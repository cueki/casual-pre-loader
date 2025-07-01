import zlib
import struct
from hashlib import md5
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, BinaryIO, List, Tuple

# see: https://developer.valvesoftware.com/wiki/VPK_(file_format)

@dataclass
class VPKDirectoryEntry:
    crc: int
    preload_bytes: int
    archive_index: int
    entry_offset: int
    entry_length: int
    preload_data: Optional[bytes] = None

    @classmethod
    def from_file(cls, file: BinaryIO) -> 'VPKDirectoryEntry':
        crc = struct.unpack('<I', file.read(4))[0]
        crc = int.from_bytes(crc.to_bytes(4, 'little'), 'big')

        entry_format = '<HHII'
        data = struct.unpack(entry_format, file.read(struct.calcsize(entry_format)))

        entry = cls(
            crc=crc,
            preload_bytes=data[0],
            archive_index=data[1],
            entry_offset=data[2],
            entry_length=data[3]
        )

        if entry.preload_bytes > 0:
            entry.preload_data = file.read(entry.preload_bytes)

        terminator = struct.unpack('<H', file.read(2))[0]
        if terminator != 0xFFFF:
            print(f"VPK WARNING: Expected 0xFFFF terminator, got 0x{terminator:04X}")

        return entry


def read_null_string(file: BinaryIO) -> str:
    result = bytearray()
    bad_result = bytearray()
    had_data = False

    while True:
        char = file.read(1)
        if not char or char == b'\x00':
            break
        had_data = True

        if 32 <= char[0] <= 126:
            result.extend(char)
        else:
            bad_result.extend(char)

    if had_data and not result:
        print(f"[VPK] All chars filtered, bad_result: {bad_result.hex()}")

    return result.decode("ascii")


class VPKFile:
    def __init__(self, vpk_path: str):
        self.vpk_path = vpk_path
        self.directory: Dict[str, Dict[str, Dict[str, VPKDirectoryEntry]]] = {}
        self._setup_paths()
        self.header_and_tree_offset = 0
        if not self.is_dir_vpk:
            self._calculate_header_and_tree_offset()

    def _setup_paths(self):
        if self.vpk_path.endswith('_dir.vpk'):
            self.is_dir_vpk = True
            self.dir_path = self.vpk_path
            self.base_path = self.vpk_path[:-8]
        else:
            path_without_ext = str(Path(self.vpk_path).with_suffix(''))
            if path_without_ext[-3:].isdigit() and path_without_ext[-4] == '_':
                path_without_ext = path_without_ext[:-4]

            possible_dir_path = f"{path_without_ext}_dir.vpk"

            if Path(possible_dir_path).exists():
                self.is_dir_vpk = True
                self.dir_path = possible_dir_path
                self.base_path = path_without_ext
            else:
                self.is_dir_vpk = False
                self.dir_path = self.vpk_path
                self.base_path = str(Path(self.vpk_path).with_suffix(''))

    def parse_directory(self) -> 'VPKFile':
        with open(self.dir_path, 'rb') as f:
            tree_offset = struct.calcsize('<7I')
            f.seek(tree_offset)

            while True:
                extension = read_null_string(f)
                if not extension:
                    break

                while True:
                    path = read_null_string(f)
                    if not path:
                        break

                    while True:
                        filename = read_null_string(f)
                        if not filename:
                            break

                        entry = VPKDirectoryEntry.from_file(f)

                        if extension not in self.directory:
                            self.directory[extension] = {}
                        if path not in self.directory[extension]:
                            self.directory[extension][path] = {}

                        self.directory[extension][path][filename] = entry
        return self

    def _calculate_header_and_tree_offset(self) -> int:
        try:
            with open(self.dir_path, 'rb') as f:
                header = f.read(28)
                if len(header) != 28:
                    raise ValueError(f"Invalid VPK header: expected 28 bytes, got {len(header)}")

                tree_size = int.from_bytes(header[8:12], 'little')
                self.header_and_tree_offset = 28 + tree_size
                return self.header_and_tree_offset
        except Exception as e:
            print(f"Error calculating header offset: {e}")
            return 0

    def get_archive_path(self, archive_index: int) -> str:
        if not self.is_dir_vpk:
            return self.vpk_path

        if archive_index == 0x7fff:
            return self.dir_path
        return f"{self.base_path}_{archive_index:03d}.vpk"

    def read_from_archive(self, archive_index: int, offset: int, size: int) -> Optional[bytes]:
        archive_path = self.get_archive_path(archive_index)
        try:
            with open(archive_path, 'rb') as f:
                adjusted_offset = offset + (self.header_and_tree_offset if not self.is_dir_vpk else 0)
                f.seek(adjusted_offset)
                return f.read(size)
        except (IOError, OSError) as e:
            print(f"Error reading from archive {archive_path}: {e}")
            return None

    def list_files(self, extension: Optional[str] = None, path: Optional[str] = None) -> List[str]:
        files = []
        extensions = [extension] if extension else self.directory.keys()

        for ext in extensions:
            if ext not in self.directory:
                continue

            paths = [path] if path else self.directory[ext].keys()
            for p in paths:
                if p not in self.directory[ext]:
                    continue

                for filename in self.directory[ext][p]:
                    full_path = f"{p}/{filename}.{ext}" if p != " " else f"{filename}.{ext}"
                    files.append(full_path)

        return files

    def find_files(self, pattern: str) -> List[str]:
        all_files = self.list_files()
        if pattern.endswith('/'):
            return [f for f in all_files if f.startswith(pattern)]
        return [f for f in all_files if Path(f).match(pattern)]

    def find_file_path(self, filename: str) -> Optional[str]:
        try:
            name, ext = filename.rsplit('.', 1)
        except ValueError:
            return None

        if ext not in self.directory:
            return None

        for path in self.directory[ext]:
            if name in self.directory[ext][path]:
                return f"{path}/{filename}" if path and path != " " else filename

        return None

    def get_file_entry(self, filepath: str) -> Optional[Tuple[str, str, VPKDirectoryEntry]]:
        try:
            path = Path(filepath)
            extension = path.suffix[1:]
            filename = path.stem
            directory = str(path.parent).replace('\\', '/')
            if directory == '.':
                directory = ' '

            if (extension in self.directory and
                    directory in self.directory[extension] and
                    filename in self.directory[extension][directory]):
                return extension, directory, self.directory[extension][directory][filename]
        except (AttributeError, KeyError) as e:
            print(f"Error getting file entry: {e}")
        return None

    def extract_file(self, filepath: str, output_path: str) -> bool:
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        extension, directory, entry = entry_info

        try:
            file_data = self.read_from_archive(entry.archive_index, entry.entry_offset, entry.entry_length)
            if not file_data:
                return False

            with open(output_path, 'wb') as f:
                if entry.preload_bytes > 0 and entry.preload_data:
                    f.write(entry.preload_data)
                f.write(file_data)

            return True
        except Exception as e:
            print(f"Error extracting file: {e}")
            return False

    def patch_file(self, filepath: str, new_data: bytes, create_backup: bool = False) -> bool:
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        _, _, entry = entry_info

        try:
            if len(new_data) != entry.entry_length:
                raise ValueError(
                    f"Modified file {filepath} does not match original "
                    f"({len(new_data)} != {entry.entry_length} bytes)"
                )

            archive_path = self.get_archive_path(entry.archive_index)

            if create_backup:
                backup_path = f"{archive_path}.backup"
                if not Path(backup_path).exists():
                    with open(archive_path, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())

            with open(archive_path, 'rb+') as f:
                f.seek(entry.entry_offset)
                f.write(new_data)

            return True
        except Exception as e:
            print(f"Error patching file: {e}")
            return False

    @classmethod
    def create(cls, source_dir: str, output_base_path: str, split_size: int = None) -> bool:
        source_path = Path(source_dir)
        base_output_path = Path(output_base_path)

        try:
            base_output_path.parent.mkdir(parents=True, exist_ok=True)
            files = [(f, f.relative_to(source_path)) for f in source_path.rglob('*') if f.is_file()]

            if not files:
                print("No files found in source directory")
                return False

            vpk_structure = cls._build_vpk_structure(files)
            dir_path = f"{base_output_path}_dir.vpk"

            if split_size is None:
                return cls._create_single_vpk(vpk_structure, dir_path)
            else:
                return cls._create_multi_vpk(vpk_structure, base_output_path, split_size)
        except Exception as e:
            print(f"Error creating VPK: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _build_vpk_structure(files):
        vpk_structure = {}
        for file_path, rel_path in files:
            extension = rel_path.suffix[1:] if rel_path.suffix else ' '
            path = str(rel_path.parent).replace('\\', '/') if str(rel_path.parent) != '.' else ' '
            filename = rel_path.stem

            if extension not in vpk_structure:
                vpk_structure[extension] = {}
            if path not in vpk_structure[extension]:
                vpk_structure[extension][path] = {}

            with open(file_path, 'rb') as f:
                content = f.read()

            vpk_structure[extension][path][filename] = {
                'content': content,
                'size': len(content),
                'path': str(file_path)
            }
        return vpk_structure

    @staticmethod
    def _write_vpk_header(f, tree_size=0, embed_chunk_length=0):
        f.write(struct.pack('<I', 0x55AA1234))
        f.write(struct.pack('<I', 2))
        tree_size_pos = f.tell()
        f.write(struct.pack('<I', tree_size))
        embed_chunk_length_pos = f.tell()
        f.write(struct.pack('<I', embed_chunk_length))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 48))
        f.write(struct.pack('<I', 0))
        return tree_size_pos, embed_chunk_length_pos

    @staticmethod
    def _write_directory_tree(f, vpk_structure, archive_entries=None):
        entry_positions = []
        archive_offset = 0

        structure = archive_entries if vpk_structure is None else vpk_structure

        for extension in sorted(structure.keys()):
            f.write(extension.encode('ascii') + b'\0')

            for path in sorted(structure[extension].keys()):
                f.write(path.encode('ascii') + b'\0')

                for filename in sorted(structure[extension][path].keys()):
                    f.write(filename.encode('ascii') + b'\0')

                    if archive_entries and vpk_structure is None:
                        # multi-file VPK case
                        entry = archive_entries[extension][path][filename]
                        f.write(struct.pack('<I', entry['crc']))
                        f.write(struct.pack('<H', 0))
                        f.write(struct.pack('<H', entry['archive_idx']))
                        f.write(struct.pack('<I', entry['offset']))
                        f.write(struct.pack('<I', entry['size']))
                    else:
                        # single-file VPK case
                        file_info = vpk_structure[extension][path][filename]
                        content = file_info['content']
                        crc = zlib.crc32(content) & 0xFFFFFFFF

                        f.write(struct.pack('<I', crc))
                        f.write(struct.pack('<H', 0))
                        f.write(struct.pack('<H', 0x7FFF))

                        entry_positions.append((f.tell(), archive_offset, len(content)))
                        f.write(struct.pack('<I', 0))
                        f.write(struct.pack('<I', len(content)))
                        archive_offset += len(content)

                    f.write(struct.pack('<H', 0xFFFF))

                f.write(b'\0')
            f.write(b'\0')
        f.write(b'\0')

        return entry_positions

    @staticmethod
    def _write_checksums(f, dir_start, dir_size):
        tree_md5 = md5()
        f.seek(dir_start)
        tree_md5.update(f.read(dir_size))

        chunk_hashes_md5 = md5()
        file_md5 = md5()
        f.seek(0)
        header_data = f.read(dir_start)
        file_md5.update(header_data)
        file_md5.update(tree_md5.digest())
        file_md5.update(chunk_hashes_md5.digest())

        f.seek(0, 2)
        f.write(tree_md5.digest())
        f.write(chunk_hashes_md5.digest())
        f.write(file_md5.digest())

    @staticmethod
    def _create_single_vpk(vpk_structure, output_path):
        try:
            with open(output_path, 'w+b') as f:
                tree_size_pos, embed_chunk_length_pos = VPKFile._write_vpk_header(f)
                dir_start = f.tell()

                entry_positions = VPKFile._write_directory_tree(f, vpk_structure)

                dir_end = f.tell()
                dir_size = dir_end - dir_start
                data_start = f.tell()

                # write data and update offsets
                current_offset = 0
                for extension in sorted(vpk_structure.keys()):
                    for path in sorted(vpk_structure[extension].keys()):
                        for filename in sorted(vpk_structure[extension][path].keys()):
                            content = vpk_structure[extension][path][filename]['content']
                            f.write(content)

                embed_chunk_length = f.tell() - data_start

                for pos, offset, length in entry_positions:
                    f.seek(pos)
                    f.write(struct.pack('<I', current_offset))
                    current_offset += length

                VPKFile._write_checksums(f, dir_start, dir_size)

                f.seek(tree_size_pos)
                f.write(struct.pack('<I', dir_size))
                f.seek(embed_chunk_length_pos)
                f.write(struct.pack('<I', embed_chunk_length))

            return True
        except Exception as e:
            print(f"Error creating single-file VPK: {e}")
            return False

    @staticmethod
    def _create_multi_vpk(vpk_structure, base_output_path, split_size):
        try:
            archives = {}
            current_archive = 0
            current_size = 0

            # distribute files across archives
            for extension in sorted(vpk_structure.keys()):
                for path in sorted(vpk_structure[extension].keys()):
                    for filename in sorted(vpk_structure[extension][path].keys()):
                        file_info = vpk_structure[extension][path][filename]
                        size = file_info['size']

                        if current_size + size > split_size and current_size > 0:
                            current_archive += 1
                            current_size = 0

                        if current_archive not in archives:
                            archives[current_archive] = []

                        archives[current_archive].append({
                            'extension': extension,
                            'path': path,
                            'filename': filename,
                            'content': file_info['content'],
                            'size': size
                        })
                        current_size += size

            # create archive files and build entries
            archive_entries = {}
            for archive_idx, files in archives.items():
                archive_path = f"{base_output_path}_{archive_idx:03d}.vpk"

                with open(archive_path, 'wb') as archive_f:
                    current_pos = 0

                    for file_entry in files:
                        extension = file_entry['extension']
                        path = file_entry['path']
                        filename = file_entry['filename']
                        content = file_entry['content']
                        size = file_entry['size']

                        crc = zlib.crc32(content) & 0xFFFFFFFF

                        if extension not in archive_entries:
                            archive_entries[extension] = {}
                        if path not in archive_entries[extension]:
                            archive_entries[extension][path] = {}

                        archive_entries[extension][path][filename] = {
                            'archive_idx': archive_idx,
                            'offset': current_pos,
                            'size': size,
                            'crc': crc
                        }

                        archive_f.write(content)
                        current_pos += size

            # create directory file
            dir_path = f"{base_output_path}_dir.vpk"
            with open(dir_path, 'w+b') as dir_f:
                tree_size_pos, _ = VPKFile._write_vpk_header(dir_f)
                dir_start = dir_f.tell()

                VPKFile._write_directory_tree(dir_f, None, archive_entries)

                dir_end = dir_f.tell()
                dir_size = dir_end - dir_start

                VPKFile._write_checksums(dir_f, dir_start, dir_size)

                dir_f.seek(tree_size_pos)
                dir_f.write(struct.pack('<I', dir_size))

            return True
        except Exception as e:
            print(f"Error creating multi-file VPK: {e}")
            return False
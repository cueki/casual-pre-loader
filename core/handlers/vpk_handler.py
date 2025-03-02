from typing import Optional, List
from core.parsers.vpk_file import VPKParser
from pathlib import Path
import os


class VPKHandler:
    def __init__(self, vpk_path: str):
        # initialize VPK handler with path to VPK file.
        # handles both directory-based VPKs (_dir.vpk) and single-file VPKs.
        self.original_path = vpk_path

        # check if it's a _dir.vpk path
        if vpk_path.endswith('_dir.vpk'):
            if os.path.exists(vpk_path):
                self.dir_path = vpk_path
                self.base_path = vpk_path[:-8]  # remove "_dir.vpk"
                self.is_dir_vpk = True
            else:
                raise ValueError(f"Could not find directory VPK: {vpk_path}")
        else:
            # for non-dir VPKs, try to find the corresponding _dir.vpk
            path_without_ext = str(Path(vpk_path).with_suffix(''))
            # remove any _NNN suffix if present
            if path_without_ext[-4:-1].isdigit() and path_without_ext[-4] == '_':
                path_without_ext = path_without_ext[:-4]

            possible_dir_path = f"{path_without_ext}_dir.vpk"

            if os.path.exists(possible_dir_path):
                self.dir_path = possible_dir_path
                self.base_path = path_without_ext
                self.is_dir_vpk = True
            # if no _dir.vpk exists, treat as single file VPK
            elif os.path.exists(vpk_path):
                self.dir_path = vpk_path
                self.base_path = str(Path(vpk_path).with_suffix(''))
                self.is_dir_vpk = False
            else:
                raise ValueError(f"Could not find VPK file: {vpk_path} or directory VPK: {possible_dir_path}")

        self.vpk_parser = VPKParser(self.dir_path)
        self.vpk_parser.parse_directory()

        self.header_offset = 0
        if not self.is_dir_vpk:
            # calculate header offset for single-file VPKs
            self.header_offset = self._calculate_header_offset()

    def get_archive_path(self, archive_index: int) -> str:
        if not self.is_dir_vpk:
            # for single-file VPKs, always use the original file
            return self.original_path

        # for directory VPKs, use the normal archive system
        if archive_index == 0x7fff:
            return self.dir_path
        return f"{self.base_path}_{archive_index:03d}.vpk"

    def list_files(self, extension: Optional[str] = None, path: Optional[str] = None) -> List[str]:
        files = []
        extensions = [extension] if extension else self.vpk_parser.directory.keys()

        for ext in extensions:
            if ext not in self.vpk_parser.directory:
                continue

            paths = [path] if path else self.vpk_parser.directory[ext].keys()
            for p in paths:
                if p not in self.vpk_parser.directory[ext]:
                    continue

                for filename in self.vpk_parser.directory[ext][p]:
                    full_path = f"{p}/{filename}.{ext}" if p != " " else f"{filename}.{ext}"
                    files.append(full_path)

        return files

    def find_files(self, pattern: str):
        all_files = self.list_files()
        # directory prefix
        if pattern.endswith('/'):
            return [f for f in all_files if f.startswith(pattern)]
        # normal file
        return [f for f in all_files if Path(f).match(pattern)]

    def find_file_path(self, filename: str):
        try:
            name, ext = filename.rsplit('.', 1)
        except ValueError:
            return None

        if ext not in self.vpk_parser.directory:
            return None

        for path in self.vpk_parser.directory[ext]:
            if name in self.vpk_parser.directory[ext][path]:
                return f"{path}/{filename}" if path else filename

        return None

    def get_file_entry(self, filepath: str):
        try:
            path = Path(filepath)
            extension = path.suffix[1:]  # removes the dot
            filename = path.stem
            # ensure forward slashes and handle nested paths correctly
            directory = str(path.parent).replace('\\', '/')
            if directory == '.':
                directory = ' '

            if (extension in self.vpk_parser.directory and
                    directory in self.vpk_parser.directory[extension] and
                    filename in self.vpk_parser.directory[extension][directory]):
                return extension, directory, self.vpk_parser.directory[extension][directory][filename]

        except (AttributeError, KeyError) as e:
            print(f"somethings wrong, I can feel it {e}")
        return None

    def _calculate_header_offset(self) -> int:
        # calculate the offset where file data begins in a single-file VPK.
        try:
            with open(self.dir_path, 'rb') as f:
                # VPK header is 28 bytes (7 uint32 values)
                header = f.read(28)
                if len(header) != 28:
                    return 0

                tree_size = int.from_bytes(header[8:12], 'little')
                total_offset = (28 + tree_size)  # tree + header offset

                return total_offset

        except Exception as e:
            print(f"Error calculating header offset: {e}")
            return 0

    def read_from_archive(self, archive_index: int, offset: int, size: int):
        archive_path = self.get_archive_path(archive_index)
        try:
            with open(archive_path, 'rb') as f:
                adjusted_offset = offset
                if not self.is_dir_vpk:
                    adjusted_offset = offset + self.header_offset

                f.seek(adjusted_offset)
                return f.read(size)
        except (IOError, OSError) as e:
            print(f"Error reading from archive {archive_path}: {e}")
            return None

    def extract_file(self, filepath: str, output_path: str) -> bool:
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        extension, directory, entry = entry_info

        try:
            file_data = self.read_from_archive(
                entry.archive_index,
                entry.entry_offset,
                entry.entry_length
            )

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
        # patch a file in the VPK with new data (ONLY WORKS WITH _DIR.VPK)
        entry_info = self.get_file_entry(filepath)
        if not entry_info:
            return False

        _, _, entry = entry_info

        try:
            # verify size
            if len(new_data) != entry.entry_length:
                raise ValueError(
                    f"Modified file is does not match original "
                    f"({len(new_data)} != {entry.entry_length} bytes)"
                )
            # get the correct VPK archive path
            archive_path = self.get_archive_path(entry.archive_index)

            # create backup if requested
            if create_backup:
                backup_path = f"{archive_path}.backup"
                if not os.path.exists(backup_path):
                    with open(archive_path, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())

            # write the modified data
            with open(archive_path, 'rb+') as f:
                f.seek(entry.entry_offset)
                f.write(new_data)

            return True

        except Exception as e:
            print(f"Error patching file: {e}")
            return False

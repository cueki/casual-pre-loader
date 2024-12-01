import os
import struct
import difflib
from dataclasses import dataclass
from typing import Dict, List, Optional, BinaryIO, Tuple, Set


@dataclass
class VPKHeader:
    signature: int
    version: int
    tree_size: int
    file_data_section_size: int
    archive_md5_section_size: int
    other_md5_section_size: int
    signature_section_size: int

    @classmethod
    def from_file(cls, file: BinaryIO) -> 'VPKHeader':
        """Read VPK header from file"""
        header_format = '<7I'  # uint32 x 7
        data = struct.unpack(header_format, file.read(struct.calcsize(header_format)))
        return cls(*data)


@dataclass
class ArchiveMD5Entry:
    archive_index: int
    start_offset: int
    count: int
    checksum: bytes

    @classmethod
    def from_file(cls, file) -> 'ArchiveMD5Entry':
        data = struct.unpack('<III16s', file.read(28))
        return cls(data[0], data[1], data[2], data[3])

    def __str__(self):
        return f"Archive {self.archive_index}: offset={self.start_offset}, size={self.count}, MD5={self.checksum.hex()}"


@dataclass
class OtherMD5Section:
    tree_checksum: bytes
    archive_md5_checksum: bytes
    whole_file_checksum: bytes

    @classmethod
    def from_file(cls, file) -> 'OtherMD5Section':
        data = struct.unpack('16s16s16s', file.read(48))
        return cls(data[0], data[1], data[2])

    def __str__(self):
        return f"""Directory Tree: {self.tree_checksum.hex()}
Archive MD5 Entries: {self.archive_md5_checksum.hex()}
Complete File: {self.whole_file_checksum.hex()}"""


class VPKChecksumReader:
    def __init__(self, vpk_path: str):
        self.vpk_path = vpk_path

    def read_checksums(self) -> tuple[List[ArchiveMD5Entry], Optional[OtherMD5Section]]:
        with open(self.vpk_path, 'rb') as f:
            # Read VPK header
            header = struct.unpack('<7I', f.read(28))
            tree_size = header[2]
            archive_md5_size = header[4]
            other_md5_size = header[5]

            # Skip to MD5 section
            f.seek(28 + tree_size)

            # Read archive MD5 entries
            archive_entries = []
            num_entries = archive_md5_size // 28
            for _ in range(num_entries):
                entry = ArchiveMD5Entry.from_file(f)
                archive_entries.append(entry)

            # Read other MD5s if present
            other_md5s = None
            if other_md5_size == 48:
                other_md5s = OtherMD5Section.from_file(f)

            return archive_entries, other_md5s



@dataclass
class VPKDirectoryEntry:
    crc: int
    preload_bytes: int
    archive_index: int
    entry_offset: int
    entry_length: int
    preload_data: Optional[bytes] = None
    directory_offset: int = 0  # New field to store offset in directory (not useful)

    @classmethod
    def from_file(cls, file: BinaryIO) -> 'VPKDirectoryEntry':
        """Read directory entry from file"""
        # Read CRC separately to handle endianness
        crc = struct.unpack('<I', file.read(4))[0]
        # Convert to big-endian for consistency with other tools
        crc = int.from_bytes(crc.to_bytes(4, 'little'), 'big')

        # Read remaining fields
        entry_format = '<HHII'  # uint16, uint16, uint32, uint32
        data = struct.unpack(entry_format, file.read(struct.calcsize(entry_format)))

        entry = cls(
            crc=crc, # not used in code
            preload_bytes=data[0], # not used in this game
            archive_index=data[1],
            entry_offset=data[2],
            entry_length=data[3]
        )

        if entry.preload_bytes > 0:
            entry.preload_data = file.read(entry.preload_bytes)
        return entry

    def __str__(self):
        return (f"CRC: 0x{self.crc:08x}\n"
                f"Archive Index: {self.archive_index}\n"
                f"Entry Offset: {self.entry_offset}\n"
                f"Entry Length: {self.entry_length}\n"
                f"Preload Bytes: {self.preload_bytes}")


class VPKParser:
    def __init__(self, dir_path: str):
        self.dir_path = dir_path
        self.base_path = dir_path[:-8]  # Remove "_dir.vpk"
        self.directory: Dict[str, Dict[str, Dict[str, VPKDirectoryEntry]]] = {}

    def read_null_string(self, file: BinaryIO) -> str:
        result = bytearray()
        while True:
            char = file.read(1)
            if char == b'\0' or not char:
                break
            # Only accept printable ASCII characters
            if 32 <= char[0] <= 126:
                result.extend(char)
        return result.decode('ascii') if result else ''

    def parse_directory(self) -> None:
        with open(self.dir_path, 'rb') as f:
            tree_offset = struct.calcsize('<7I')
            f.seek(tree_offset)

            while True:
                extension = self.read_null_string(f)
                if not extension:
                    break

                while True:
                    path = self.read_null_string(f)
                    if not path:
                        break

                    while True:
                        filename_offset = f.tell() + 2  # Offset includes the null terminator from previous string
                        filename = self.read_null_string(f)
                        if not filename:
                            break

                        entry = VPKDirectoryEntry.from_file(f)
                        entry.directory_offset = filename_offset

                        if extension not in self.directory:
                            self.directory[extension] = {}
                        if path not in self.directory[extension]:
                            self.directory[extension][path] = {}

                        self.directory[extension][path][filename] = entry

    def get_file_data(self, extension: str, path: str, filename: str) -> Optional[bytes]:
        try:
            entry = self.directory[extension][path][filename]

            # Return preload data if that's all there is
            if entry.entry_length == 0 and entry.preload_data:
                return entry.preload_data

            # Read from archive
            if entry.archive_index == 0x7fff:
                # Data follows directory
                with open(self.dir_path, 'rb') as f:
                    f.seek(entry.entry_offset)
                    return f.read(entry.entry_length)
            else:
                # Data is in numbered archive
                archive_path = f"{self.base_path}_{entry.archive_index:03d}.vpk"
                with open(archive_path, 'rb') as f:
                    f.seek(entry.entry_offset)
                    return f.read(entry.entry_length)

        except (KeyError, IOError):
            return None

    def list_files(self) -> List[str]:
        files = []
        for ext in self.directory:
            for path in self.directory[ext]:
                for filename in self.directory[ext][path]:
                    full_path = f"{path}/{filename}.{ext}" if path else f"{filename}.{ext}"
                    files.append(full_path)
        return files


class VMTComparator:
    def __init__(self, source_vpk_path: str, target_vpk_path: str):
        self.source_vpk = VPKParser(source_vpk_path)
        self.target_vpk = VPKParser(target_vpk_path)
        self.source_vpk.parse_directory()
        self.target_vpk.parse_directory()
        self.source_files = self._find_vmt_files(self.source_vpk)
        self.target_files = self._find_vmt_files(self.target_vpk)

    def _find_vmt_files(self, vpk: VPKParser) -> Dict[str, List[Tuple[str, str, str]]]:
        vmt_files = {}
        if 'vmt' in vpk.directory:
            for path in vpk.directory['vmt']:
                for filename in vpk.directory['vmt'][path]:
                    full_filename = f"{filename}.vmt"
                    if full_filename not in vmt_files:
                        vmt_files[full_filename] = []
                    vmt_files[full_filename].append(('vmt', path, filename))
        return vmt_files

    def compare_vmts(self) -> Dict[str, List[Dict[str, any]]]:
        results = {}

        for filename in self.source_files:
            if filename not in self.target_files:
                continue

            file_results = []
            for ext1, path1, fname1 in self.source_files[filename]:
                source_data = self.source_vpk.get_file_data(ext1, path1, fname1)
                source_path = f"{path1}/{fname1}.{ext1}" if path1 else f"{fname1}.{ext1}"

                for ext2, path2, fname2 in self.target_files[filename]:
                    target_data = self.target_vpk.get_file_data(ext2, path2, fname2)
                    target_path = f"{path2}/{fname2}.{ext2}" if path2 else f"{fname2}.{ext2}"

                    if source_data is None or target_data is None:
                        continue

                    try:
                        source_text = source_data.decode('utf-8').splitlines()
                        target_text = target_data.decode('utf-8').splitlines()

                        if source_text == target_text:
                            comparison = {
                                'source_path': source_path,
                                'target_path': target_path,
                                'status': 'identical',
                                'size': len(source_data)
                            }
                        else:
                            diff = list(difflib.unified_diff(
                                source_text, target_text,
                                fromfile=f"SOURCE:{source_path}",
                                tofile=f"TARGET:{target_path}",
                                lineterm=''
                            ))
                            comparison = {
                                'source_path': source_path,
                                'target_path': target_path,
                                'status': 'different',
                                'source_size': len(source_data),
                                'target_size': len(target_data),
                                'diff': '\n'.join(diff)
                            }
                        file_results.append(comparison)
                    except UnicodeDecodeError:
                        continue

            if file_results:
                results[filename] = file_results

        return results


def print_vmt_comparison(filename: str, comparisons: List[Dict[str, any]]):
    print(f"\n{'=' * 80}")
    print(f"VMT: {filename}")
    print(f"{'=' * 80}")

    for comp in comparisons:
        print(f"\nSource: {comp['source_path']}")
        print(f"Target: {comp['target_path']}")

        if comp['status'] == 'identical':
            print(f"Status: IDENTICAL (Size: {comp['size']} bytes)")
        else:
            print("Status: DIFFERENT")
            print(f"Source size: {comp['source_size']} bytes")
            print(f"Target size: {comp['target_size']} bytes")
            print("\nDifferences:")
            print(f"{'-' * 40}")
            print(comp['diff'])
            print(f"{'-' * 40}")


class VTFComparator:
    def __init__(self, source_vpk_path: str, target_vpk_path: str):
        self.source_vpk = VPKParser(source_vpk_path)
        self.target_vpk = VPKParser(target_vpk_path)
        self.source_vpk.parse_directory()
        self.target_vpk.parse_directory()
        self.source_files = self._find_vtf_files(self.source_vpk)
        self.target_files = self._find_vtf_files(self.target_vpk)

    def _find_vtf_files(self, vpk: VPKParser) -> Dict[str, List[Tuple[str, str, str]]]:
        vtf_files = {}
        if 'vtf' in vpk.directory:
            for path in vpk.directory['vtf']:
                for filename in vpk.directory['vtf'][path]:
                    full_filename = f"{filename}.vtf"
                    if full_filename not in vtf_files:
                        vtf_files[full_filename] = []
                    vtf_files[full_filename].append(('vtf', path, filename))
        return vtf_files

    def compare_vtfs(self) -> Dict[str, List[Dict[str, any]]]:
        results = {}

        for filename in self.source_files:
            if filename not in self.target_files:
                continue

            file_results = []
            for ext1, path1, fname1 in self.source_files[filename]:
                source_data = self.source_vpk.get_file_data(ext1, path1, fname1)
                source_path = f"{path1}/{fname1}.{ext1}" if path1 else f"{fname1}.{ext1}"

                for ext2, path2, fname2 in self.target_files[filename]:
                    target_data = self.target_vpk.get_file_data(ext2, path2, fname2)
                    target_path = f"{path2}/{fname2}.{ext2}" if path2 else f"{fname2}.{ext2}"

                    if source_data is None or target_data is None:
                        continue

                    comparison = {
                        'source_path': source_path,
                        'target_path': target_path,
                        'source_size': len(source_data),
                        'target_size': len(target_data),
                        'identical': source_data == target_data,
                        'size_diff': len(target_data) - len(source_data)
                    }
                    file_results.append(comparison)

            if file_results:
                results[filename] = file_results

        return results


def print_vtf_comparison(filename: str, comparisons: List[Dict[str, any]]):
    print(f"\n{'=' * 80}")
    print(f"VTF: {filename}")
    print(f"{'=' * 80}")

    for comp in comparisons:
        print(f"\nSource: {comp['source_path']}")
        print(f"Target: {comp['target_path']}")

        if comp['identical']:
            print(f"Status: IDENTICAL")
        else:
            print(f"Status: DIFFERENT")

        print(f"Source size: {comp['source_size']:,} bytes")
        print(f"Target size: {comp['target_size']:,} bytes")
        if not comp['identical']:
            diff = comp['size_diff']
            if diff > 0:
                print(f"Target is {diff:,} bytes larger")
            else:
                print(f"Target is {abs(diff):,} bytes smaller")


class VMTDirComparator:
    def __init__(self, local_dir: str, vpk_path: str):
        self.local_dir = local_dir
        self.vpk = VPKParser(vpk_path)
        self.vpk.parse_directory()
        self.local_vmts = self._scan_local_vmts()
        self.vpk_vmts = self._get_vpk_vmts()

    def _scan_local_vmts(self) -> Dict[str, str]:
        """Scan local directory for VMTs, returns {filepath: full_path}"""
        vmts = {}
        for root, _, files in os.walk(self.local_dir):
            for file in files:
                if file.endswith('.vmt'):
                    full_path = os.path.join(root, file)
                    # Convert path to VPK-style path
                    rel_path = os.path.relpath(full_path, self.local_dir)
                    rel_path = rel_path.replace('\\', '/')
                    vmts[rel_path] = full_path
        return vmts

    def _get_vpk_vmts(self) -> Set[str]:
        """Get set of VMT paths from VPK"""
        vmts = set()
        if 'vmt' in self.vpk.directory:
            for path in self.vpk.directory['vmt']:
                for filename in self.vpk.directory['vmt'][path]:
                    vpk_path = f"{path}/{filename}.vmt" if path else f"{filename}.vmt"
                    vmts.add(vpk_path)
        return vmts

    def compare_files(self) -> Dict[str, Dict]:
        """Compare VMTs between local dir and VPK"""
        results = {}
        for local_path, full_path in self.local_vmts.items():
            # Check if this VMT exists in VPK
            if local_path in self.vpk_vmts:
                # Read local file
                with open(full_path, 'rb') as f:
                    local_content = f.read()

                # Get VPK file content
                *folders, filename = local_path.split('/')
                path = '/'.join(folders)
                basename = filename[:-4]  # Remove .vmt
                vpk_content = self.vpk.get_file_data('vmt', path, basename)

                if vpk_content:
                    try:
                        local_text = local_content.decode('utf-8').splitlines()
                        vpk_text = vpk_content.decode('utf-8').splitlines()

                        if local_text == vpk_text:
                            results[local_path] = {
                                'status': 'identical',
                                'size': len(local_content)
                            }
                        else:
                            diff = list(difflib.unified_diff(
                                vpk_text, local_text,
                                fromfile=f"VPK:{local_path}",
                                tofile=f"LOCAL:{local_path}",
                                lineterm=''
                            ))
                            results[local_path] = {
                                'status': 'different',
                                'local_size': len(local_content),
                                'vpk_size': len(vpk_content),
                                'diff': '\n'.join(diff)
                            }
                    except UnicodeDecodeError:
                        results[local_path] = {
                            'status': 'binary',
                            'local_size': len(local_content),
                            'vpk_size': len(vpk_content)
                        }
                else:
                    results[local_path] = {
                        'status': 'vpk_read_error'
                    }
            else:
                results[local_path] = {
                    'status': 'local_only'
                }

        return results


def print_comparison_results(results: Dict[str, Dict]):
    """Print comparison results in a readable format"""
    for path, result in results.items():
        print(f"\n{'=' * 80}")
        print(f"VMT: {path}")
        print(f"{'=' * 80}")

        if result['status'] == 'identical':
            print(f"Status: IDENTICAL (Size: {result['size']} bytes)")

        elif result['status'] == 'different':
            print("Status: DIFFERENT")
            print(f"Local size: {result['local_size']} bytes")
            print(f"VPK size: {result['vpk_size']} bytes")
            print("\nDifferences:")
            print(f"{'-' * 40}")
            print(result['diff'])
            print(f"{'-' * 40}")

        elif result['status'] == 'binary':
            print("Status: BINARY COMPARISON")
            print(f"Local size: {result['local_size']} bytes")
            print(f"VPK size: {result['vpk_size']} bytes")

        elif result['status'] == 'local_only':
            print("Status: EXISTS ONLY IN LOCAL DIRECTORY")

        elif result['status'] == 'vpk_read_error':
            print("Status: ERROR READING FROM VPK")
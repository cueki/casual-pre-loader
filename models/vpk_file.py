import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, BinaryIO


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

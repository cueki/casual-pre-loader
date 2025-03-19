import struct
from dataclasses import dataclass
from typing import Dict, Optional, BinaryIO


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
        # read CRC separately to handle endianness
        crc = struct.unpack('<I', file.read(4))[0]
        # convert to big-endian for consistency
        crc = int.from_bytes(crc.to_bytes(4, 'little'), 'big')

        # read remaining fields
        entry_format = '<HHII'  # uint16, uint16, uint32, uint32
        data = struct.unpack(entry_format, file.read(struct.calcsize(entry_format)))

        entry = cls(
            crc=crc, # not used in code
            preload_bytes=data[0], # not used in tf2 but whatever
            archive_index=data[1],
            entry_offset=data[2],
            entry_length=data[3]
        )

        if entry.preload_bytes > 0:
            entry.preload_data = file.read(entry.preload_bytes)
        return entry


def read_null_string(file: BinaryIO) -> str:
    result = bytearray()
    while True:
        char = file.read(1)
        if not char or char == b'\x00':
            break
        # only accept printable ASCII characters
        if 32 <= char[0] <= 126:
            result.extend(char)
    return result.decode('ascii') if result else ''


class VPKParser:
    def __init__(self, dir_path: str):
        self.dir_path = dir_path
        self.base_path = dir_path[:-8]  # remove "_dir.vpk"
        self.directory: Dict[str, Dict[str, Dict[str, VPKDirectoryEntry]]] = {}

    def parse_directory(self) -> None:
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

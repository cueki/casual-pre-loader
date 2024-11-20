import struct
import os
from typing import Dict, List, Tuple, BinaryIO
from dataclasses import dataclass
import argparse

@dataclass
class VPKHeader:
    """Represents the header of a VPK file"""
    signature: int          # Should be 0x55AA1234
    version: int           # Version number of the VPK file
    tree_size: int         # Size of the directory tree
    file_data_section_size: int
    archive_md5_section_size: int
    other_md5_section_size: int
    signature_section_size: int

@dataclass
class VPKEntry:
    """Represents a file entry in the VPK"""
    path: str
    extension: str
    directory: str
    filename: str
    crc: int
    preload_bytes: int
    archive_index: int
    entry_offset: int
    entry_length: int
    preload_data: bytes = b''

class VPKDecoder:
    def __init__(self, filename: str):
        self.filename = filename
        self.header = None
        self.entries: List[VPKEntry] = []
        self.extensions: Dict[str, List[VPKEntry]] = {}

    def read_null_terminated_string(self, f: BinaryIO) -> str:
        """Read a null-terminated string from the file."""
        result = []
        while True:
            char = f.read(1)
            if char == b'\x00' or not char:
                break
            result.append(char.decode('utf-8'))
        return ''.join(result)

    def read_header(self, f: BinaryIO) -> VPKHeader:
        """Read and validate the VPK header."""
        # Read header fields
        signature, version = struct.unpack("<II", f.read(8))
        
        if signature != 0x55AA1234:
            raise ValueError(f"Invalid VPK signature: {hex(signature)}")

        if version == 1:
            tree_size, = struct.unpack("<I", f.read(4))
            return VPKHeader(
                signature=signature,
                version=version,
                tree_size=tree_size,
                file_data_section_size=0,
                archive_md5_section_size=0,
                other_md5_section_size=0,
                signature_section_size=0
            )
        elif version == 2:
            (tree_size, file_data_section_size, archive_md5_section_size,
             other_md5_section_size, signature_section_size) = struct.unpack("<IIIII", f.read(20))
            return VPKHeader(
                signature=signature,
                version=version,
                tree_size=tree_size,
                file_data_section_size=file_data_section_size,
                archive_md5_section_size=archive_md5_section_size,
                other_md5_section_size=other_md5_section_size,
                signature_section_size=signature_section_size
            )
        else:
            raise ValueError(f"Unsupported VPK version: {version}")

    def read_tree(self, f: BinaryIO) -> None:
        """Read the directory tree structure."""
        while True:
            # Read extension
            extension = self.read_null_terminated_string(f)
            if not extension:
                break

            while True:
                # Read directory
                directory = self.read_null_terminated_string(f)
                if not directory:
                    break

                while True:
                    # Read filename
                    filename = self.read_null_terminated_string(f)
                    if not filename:
                        break

                    # Read file metadata
                    crc = struct.unpack("<I", f.read(4))[0]
                    preload_bytes = struct.unpack("<H", f.read(2))[0]
                    archive_index = struct.unpack("<H", f.read(2))[0]
                    entry_offset = struct.unpack("<I", f.read(4))[0]
                    entry_length = struct.unpack("<I", f.read(4))[0]
                    terminator = struct.unpack("<H", f.read(2))[0]

                    if terminator != 0xFFFF:
                        raise ValueError(f"Invalid terminator: {hex(terminator)}")

                    # Read preload data if present
                    preload_data = b''
                    if preload_bytes > 0:
                        preload_data = f.read(preload_bytes)

                    entry = VPKEntry(
                        path=os.path.join(directory, f"{filename}.{extension}").strip(' /\\'),
                        extension=extension,
                        directory=directory,
                        filename=filename,
                        crc=crc,
                        preload_bytes=preload_bytes,
                        archive_index=archive_index,
                        entry_offset=entry_offset,
                        entry_length=entry_length,
                        preload_data=preload_data
                    )

                    self.entries.append(entry)
                    
                    # Organize by extension
                    if extension not in self.extensions:
                        self.extensions[extension] = []
                    self.extensions[extension].append(entry)

    def decode(self) -> None:
        """Decode the VPK file."""
        with open(self.filename, 'rb') as f:
            self.header = self.read_header(f)
            self.read_tree(f)

    def print_summary(self) -> None:
        """Print a summary of the VPK contents."""
        print(f"\nVPK File: {self.filename}")
        print(f"Version: {self.header.version}")
        print(f"Tree Size: {self.header.tree_size:,} bytes")
        if self.header.version == 2:
            print(f"File Data Section Size: {self.header.file_data_section_size:,} bytes")
            print(f"Archive MD5 Section Size: {self.header.archive_md5_section_size:,} bytes")
            print(f"Other MD5 Section Size: {self.header.other_md5_section_size:,} bytes")
            print(f"Signature Section Size: {self.header.signature_section_size:,} bytes")
        
        print(f"\nTotal Files: {len(self.entries):,}")
        print("\nFile Extensions:")
        for ext, files in sorted(self.extensions.items()):
            print(f"  .{ext:<10} {len(files):,} files")

    def print_file_list(self, extension_filter: str = None) -> None:
        """Print detailed file listing, optionally filtered by extension."""
        print("\nFile Listing:")
        for entry in sorted(self.entries, key=lambda x: x.path):
            if extension_filter and entry.extension != extension_filter:
                continue
            print(f"\nPath: {entry.path}")
            print(f"  CRC: {hex(entry.crc)}")
            print(f"  Archive Index: {entry.archive_index}")
            print(f"  Offset: {entry.entry_offset:,}")
            print(f"  Length: {entry.entry_length:,} bytes")
            if entry.preload_bytes:
                print(f"  Preload Data: {entry.preload_bytes:,} bytes")

def main():
    parser = argparse.ArgumentParser(description='Decode and analyze VPK files')
    parser.add_argument('filename', help='VPK file to analyze')
    parser.add_argument('-e', '--extension', help='Filter files by extension')
    parser.add_argument('-l', '--list', action='store_true', help='Show detailed file listing')
    args = parser.parse_args()

    try:
        decoder = VPKDecoder(args.filename)
        decoder.decode()
        decoder.print_summary()
        
        if args.list:
            decoder.print_file_list(args.extension)
            
    except FileNotFoundError:
        print(f"Error: File '{args.filename}' not found")
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
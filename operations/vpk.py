import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, BinaryIO, Dict
from core.constants import PCFVersion
from core.errors import PCFError
from models.pcf_file import PCFFile


@dataclass
class VPKSearchResult:
    """Result of a PCF search in VPK"""
    vpk_path: str
    offset: int
    size: int
    pcf_version: str
    context: bytes


@dataclass
class PCFPatchResult:
    """Result of patching a PCF in VPK"""
    success: bool
    original_size: int
    new_size: int
    offset: int
    backup_path: Optional[str] = None
    error_message: Optional[str] = None



@dataclass
class VPKEntry:
    """Entry in VPK directory tree"""
    path: str
    crc: int
    preload_bytes: int
    archive_index: int
    entry_offset: int
    entry_length: int


class VPKOperations:
    """Handles operations on PCFs within VPK files"""
    def __init__(self, vpk_path: str):
        self.path = vpk_path
        self.entries: Dict[str, VPKEntry] = {}

    @staticmethod
    def read_binary_chunk(file: BinaryIO, offset: int, size: int) -> bytes:
        """Read chunk of binary data from file"""
        file.seek(offset)
        return file.read(size)

    @staticmethod
    def write_binary_chunk(file: BinaryIO, offset: int, data: bytes) -> None:
        """Write chunk of binary data to file"""
        file.seek(offset)
        file.write(data)

    @staticmethod
    def detect_pcf_version(data: bytes) -> Optional[str]:
        """Detect PCF version from binary data"""
        try:
            # Find end of version string
            end = data.index(b'\x00')
            header = data[:end].decode('ascii')

            # Check against known versions
            for version in PCFVersion:
                if header.startswith(version):
                    return version
            return None
        except (ValueError, UnicodeDecodeError):
            return None

    @staticmethod
    def create_vpk_backup(vpk_path: str) -> Optional[str]:
        """Create backup of VPK file"""
        try:
            backup_path = f"{vpk_path}.backup"
            if not os.path.exists(backup_path):
                with open(vpk_path, 'rb') as src, open(backup_path, 'wb') as dst:
                    dst.write(src.read())
            return backup_path
        except OSError:
            return None

    @staticmethod
    def read_null_string(file: BinaryIO) -> str:
        """Read null-terminated string from file"""
        result = bytearray()
        while True:
            char = file.read(1)
            if char == b'\0' or not char:
                break
            result.extend(char)
        return result.decode('ascii', errors='replace')

    @classmethod
    def find_pcfs(cls, vpk_path: str, context_size: int = 100) -> List[VPKSearchResult]:
        """
        Find all PCFs in a VPK file

        Args:
            vpk_path: Path to VPK file
            context_size: Number of context bytes to store around matches

        Returns:
            List of search results
        """
        results = []

        try:
            with open(vpk_path, 'rb') as f:
                data = f.read()
                pos = 0

                while True:
                    # Search for PCF header pattern
                    pos = data.find(b'<!-- dmx encoding binary', pos)
                    if pos == -1:
                        break

                    # Get context around match
                    context_start = max(0, pos - context_size)

                    # Find potential end of PCF by looking for next header or reasonable chunk
                    next_pos = data.find(b'<!-- dmx encoding binary', pos + 100)
                    if next_pos == -1:
                        size = min(10000, len(data) - pos)  # Reasonable max size
                    else:
                        size = next_pos - pos

                    context_end = min(len(data), pos + size + context_size)
                    context = data[context_start:context_end]

                    # Detect version
                    pcf_version = cls.detect_pcf_version(data[pos:pos + 100])
                    if pcf_version:
                        results.append(VPKSearchResult(
                            vpk_path=vpk_path,
                            offset=pos,
                            size=size,
                            pcf_version=pcf_version,
                            context=context
                        ))

                    pos += 1

        except OSError as e:
            raise PCFError(f"Error reading VPK file: {e}")

        return results

    @classmethod
    def extract_pcf(cls, vpk_path: str, offset: int, size: int, output_path: str) -> bool:
        """
        Extract PCF from VPK to file

        Args:
            vpk_path: Path to VPK file
            offset: Offset of PCF in VPK
            size: Size of PCF data
            output_path: Path to save extracted PCF

        Returns:
            True if successful
        """
        try:
            with open(vpk_path, 'rb') as f:
                pcf_data = cls.read_binary_chunk(f, offset, size)

            with open(output_path, 'wb') as f:
                f.write(pcf_data)

            return True
        except OSError:
            return False

    @classmethod
    def patch_pcf(cls, vpk_path: str, offset: int, size: int, pcf: PCFFile,
                  create_backup: bool = True) -> PCFPatchResult:
        """
        Patch PCF in VPK file

        Args:
            vpk_path: Path to VPK file
            offset: Offset of PCF in VPK
            size: Size of PCF in VPK
            pcf: Modified PCF to write
            create_backup: Whether to create backup

        Returns:
            Patch result
        """
        backup_path = None
        try:
            # Create backup if requested
            if create_backup:
                backup_path = cls.create_vpk_backup(vpk_path)
                if not backup_path:
                    return PCFPatchResult(
                        success=False,
                        original_size=0,
                        new_size=0,
                        offset=offset,
                        error_message="Failed to create backup"
                    )

            # Encode modified PCF
            temp_path = f"{vpk_path}.temp"
            pcf.encode(temp_path)

            with open(temp_path, 'rb') as f:
                new_data = f.read()
                new_size = len(new_data)

            # Verify size
            if new_size > size:
                os.remove(temp_path)
                return PCFPatchResult(
                    success=False,
                    original_size=size,
                    new_size=new_size,
                    offset=offset,
                    error_message="Modified PCF is larger than original"
                )

            # Write modified PCF
            with open(vpk_path, 'rb+') as f:
                cls.write_binary_chunk(f, offset, new_data)
                # Pad with nulls if smaller
                if new_size < size:
                    f.write(b'\x00' * (size - new_size))

            os.remove(temp_path)
            return PCFPatchResult(
                success=True,
                original_size=size,
                new_size=new_size,
                offset=offset,
                backup_path=backup_path
            )

        except Exception as e:
            return PCFPatchResult(
                success=False,
                original_size=0,
                new_size=0,
                offset=offset,
                error_message=str(e)
            )

    @staticmethod
    def batch_process_vpks(vpk_pattern: str, operation: callable) -> List[Tuple[str, bool]]:
        """Process multiple VPK files with given operation"""
        results = []
        for vpk_path in Path('.').glob(vpk_pattern):
            try:
                success = operation(str(vpk_path))
                results.append((str(vpk_path), success))
            except Exception as e:
                print(e)
                results.append((str(vpk_path), False))
        return results


def format_vpk_number(num: int) -> str:
    """Format VPK file number with leading zeros"""
    return f"{num:03d}"


def get_vpk_path(base_name: str, number: int) -> str:
    """Get full VPK path from base name and number"""
    return f"{base_name}_{format_vpk_number(number)}.vpk"
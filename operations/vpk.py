import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, BinaryIO, Dict
from core.constants import PCFVersion
from core.errors import PCFError
from models.pcf_file import PCFFile


@dataclass
class VPKSearchResult:
    vpk_path: str
    offset: int
    size: int
    pcf_version: str
    context: bytes


@dataclass
class PCFPatchResult:
    success: bool
    original_size: int
    new_size: int
    offset: int
    backup_path: Optional[str] = None
    error_message: Optional[str] = None



@dataclass
class VPKEntry:
    path: str
    crc: int
    preload_bytes: int
    archive_index: int
    entry_offset: int
    entry_length: int


class VPKOperations:
    # Handles operations on stuff within VPK files
    def __init__(self, vpk_path: str):
        self.path = vpk_path
        self.entries: Dict[str, VPKEntry] = {}

    @staticmethod
    def read_binary_chunk(file: BinaryIO, offset: int, size: int) -> bytes:
        file.seek(offset)
        return file.read(size)

    @staticmethod
    def write_binary_chunk(file: BinaryIO, offset: int, data: bytes) -> None:
        file.seek(offset)
        file.write(data)

    @staticmethod
    def detect_pcf_version(data: bytes) -> Optional[str]:
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
        # Make backup... I probably should do this smarter
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
        result = bytearray()
        while True:
            char = file.read(1)
            if char == b'\0' or not char:
                break
            result.extend(char)
        return result.decode('ascii', errors='replace')

    @classmethod
    def extract_pcf(cls, vpk_path: str, offset: int, size: int, output_path: str) -> bool:
        # Extract PCF from VPK based on offset and size, careful, it will do exactly as you ask
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
        # Opposite of extract, write to location whatever bytes you want, will error if new PCF is too large
        backup_path = None
        try:
            # Create backup
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

            # Temp VPK
            temp_path = f"{vpk_path}.temp"

            # Encode modified PCF to temp
            pcf.encode(temp_path)

            # Get size of the VPK
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
        # My very own _dir.vpk ;) - unused
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
    return f"{num:03d}"


def get_vpk_path(base_name: str, number: int) -> str:
    return f"{base_name}_{format_vpk_number(number)}.vpk"
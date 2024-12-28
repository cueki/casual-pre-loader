import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, BinaryIO, Dict
from core.constants import PCFVersion
from core.errors import PCFError
from operations.vmt_wasted_space import VMTSpaceAnalyzer, VMTFile, WastedSpace
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


@dataclass
class VMTPatchResult:
    path: str
    original_size: int
    new_size: Optional[int] = None
    bytes_saved: Optional[int] = None
    status: str = 'success'
    error_message: Optional[str] = None


@dataclass
class VMTAnalysisResult:
    vpk_path: str
    total_vmt_files: int
    total_wasted_bytes: int
    analyzed_vmts: Dict[str, VMTFile]
    errors: List[str]


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

    def analyze_vmt_spaces(self) -> VMTAnalysisResult:
        vmt_analyzer = VMTSpaceAnalyzer()
        analyzed_files = {}
        errors = []
        total_wasted_bytes = 0

        if 'vmt' in self.entries:
            for entry in self.entries.values():
                if entry.path.endswith('.vmt'):
                    try:
                        # Read VMT content
                        with open(self.path, 'rb') as f:
                            f.seek(entry.entry_offset)
                            vmt_data = f.read(entry.entry_length)

                        # Analyze VMT content
                        vmt_file = vmt_analyzer.analyze_file(vmt_data, entry.path)
                        analyzed_files[entry.path] = vmt_file
                        total_wasted_bytes += sum(space.length for space in vmt_file.wasted_spaces)

                    except Exception as e:
                        errors.append(f"Error analyzing {entry.path}: {str(e)}")

        return VMTAnalysisResult(
            vpk_path=self.path,
            total_vmt_files=len(analyzed_files),
            total_wasted_bytes=total_wasted_bytes,
            analyzed_vmts=analyzed_files,
            errors=errors
        )

    def consolidate_vmt_spaces(self, create_backup: bool = False) -> List[VMTPatchResult]:
        results = []
        vmt_analyzer = VMTSpaceAnalyzer()

        # Create backup if requested
        if create_backup:
            backup_path = self.create_vpk_backup(self.path)
            if not backup_path:
                return [VMTPatchResult(
                    path='',
                    original_size=0,
                    status='error',
                    error_message='Failed to create backup'
                )]

        # First analyze all VMTs
        analysis = self.analyze_vmt_spaces()

        # Process each VMT file
        for path, vmt_file in analysis.analyzed_vmts.items():
            if not vmt_file.wasted_spaces:
                continue

            try:
                # Consolidate spaces
                new_content = vmt_analyzer.consolidate_wasted_space(vmt_file)
                if not new_content:
                    results.append(VMTPatchResult(
                        path=path,
                        original_size=vmt_file.total_size,
                        status='error',
                        error_message='Failed to consolidate spaces'
                    ))
                    continue

                # Get VPK entry
                entry = self.entries.get(path)
                if not entry:
                    results.append(VMTPatchResult(
                        path=path,
                        original_size=vmt_file.total_size,
                        status='error',
                        error_message='Entry not found in VPK'
                    ))
                    continue

                # Verify size constraints
                if len(new_content) > entry.entry_length:
                    results.append(VMTPatchResult(
                        path=path,
                        original_size=vmt_file.total_size,
                        status='error',
                        error_message='New content larger than original'
                    ))
                    continue

                # Patch the VPK
                with open(self.path, 'rb+') as f:
                    f.seek(entry.entry_offset)
                    f.write(new_content)

                results.append(VMTPatchResult(
                    path=path,
                    original_size=vmt_file.total_size,
                    new_size=len(new_content),
                    bytes_saved=vmt_file.total_size - len(new_content),
                    status='success'
                ))

            except Exception as e:
                results.append(VMTPatchResult(
                    path=path,
                    original_size=vmt_file.total_size,
                    status='error',
                    error_message=str(e)
                ))

        return results


def print_vmt_analysis(analysis: VMTAnalysisResult):
    print(f"\nVPK VMT Analysis Results for: {analysis.vpk_path}")
    print(f"Total VMT files analyzed: {analysis.total_vmt_files}")
    print(f"Total wasted bytes found: {analysis.total_wasted_bytes:,}")

    if analysis.analyzed_vmts:
        print("\nDetailed VMT Analysis:")
        for filepath, vmt_file in analysis.analyzed_vmts.items():
            wasted_bytes = sum(space.length for space in vmt_file.wasted_spaces)
            if wasted_bytes > 0:
                print(f"\nFile: {filepath}")
                print(f"Total size: {vmt_file.total_size:,} bytes")
                print(f"Wasted space: {wasted_bytes:,} bytes")
                if vmt_file.wasted_spaces:
                    print("Wasted spaces:")
                    for i, space in enumerate(vmt_file.wasted_spaces):
                        print(f"  [{i}] Line {space.line_number}: {space.original_content}")

    if analysis.errors:
        print("\nErrors encountered:")
        for error in analysis.errors:
            print(f"- {error}")


def print_vmt_patch_results(results: List[VMTPatchResult]):
    print("\nVMT Patch Results:")
    total_saved = 0
    success_count = 0
    error_count = 0

    for result in results:
        if result.status == 'success':
            print(f"\nSuccessfully patched: {result.path}")
            print(f"Bytes saved: {result.bytes_saved:,}")
            total_saved += result.bytes_saved or 0
            success_count += 1
        else:
            print(f"\nError patching: {result.path}")
            print(f"Error: {result.error_message}")
            error_count += 1

    print(f"\nSummary:")
    print(f"Total files processed: {len(results)}")
    print(f"Successful patches: {success_count}")
    print(f"Failed patches: {error_count}")
    print(f"Total bytes saved: {total_saved:,}")


def format_vpk_number(num: int) -> str:
    return f"{num:03d}"


def get_vpk_path(base_name: str, number: int) -> str:
    return f"{base_name}_{format_vpk_number(number)}.vpk"
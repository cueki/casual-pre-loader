import os
from dataclasses import dataclass
from typing import List, Optional, Dict
from operations.vmt_wasted_space import VMTSpaceAnalyzer, VMTFile


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

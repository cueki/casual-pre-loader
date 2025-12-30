import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from valve_parsers import VPKFile

from core.constants import VALID_MOD_ROOT_FOLDERS

log = logging.getLogger()


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    type_detected: str  # "hud" or "unknown" for now


def validate_mod_structure(folder_path: Path) -> ValidationResult:
    # validate that the folder has the required mod structure:
    # must contain at least one of the valid mod root folders
    # valid mod root folders must be one level down from the root
    # must not contain VPK files
    errors = []
    warnings = []
    found_valid_folders = []
    found_vpk_files = []

    try:
        # VPK check
        vpk_files = list(folder_path.glob("*.vpk"))
        if vpk_files:
            vpk_names = [vpk.name for vpk in vpk_files]
            errors.append(
                f"Folder '{folder_path.name}' contains VPK files: {', '.join(vpk_names)}\n\n"
                f"Please drag the VPK files directly instead of the folder containing them.\n"
                f"VPK files should be dragged individually for proper processing."
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                type_detected="vpk_container"
            )

        # check immediate subdirectories
        subdirs = [item for item in folder_path.iterdir() if item.is_dir()]
        subdir_names = {subdir.name.lower() for subdir in subdirs}

        # check for VPK files in subdirectories
        for subdir in subdirs:
            sub_vpks = list(subdir.glob("*.vpk"))
            if sub_vpks:
                found_vpk_files.extend([(subdir.name, vpk.name) for vpk in sub_vpks])

        if found_vpk_files:
            vpk_locations = [f"{subdir}/{vpk}" for subdir, vpk in found_vpk_files]
            errors.append(
                f"Folder '{folder_path.name}' contains VPK files in subdirectories:\n"
                f"{chr(10).join(f'• {loc}' for loc in vpk_locations)}\n\n"
                f"Please extract and drag the VPK files directly instead of the folder containing them."
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                type_detected="vpk_container"
            )

        # check if any valid mod root folders exist
        for valid_folder in VALID_MOD_ROOT_FOLDERS:
            if valid_folder.lower() in subdir_names:
                found_valid_folders.append(valid_folder)

        if not found_valid_folders:
            errors.append(
                f"Folder '{folder_path.name}' does not contain any valid mod structure folders.\n"
                f"Expected at least one of: {', '.join(VALID_MOD_ROOT_FOLDERS)}\n"
                f"Found subdirectories: {', '.join([d.name for d in subdirs]) if subdirs else 'none'}"
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                type_detected="unknown"
            )

        # determine type based on found folders (rn just HUD)
        type_detected = "unknown"
        if "resource" in found_valid_folders or any("ui" in str(subdir) for subdir in subdirs):
            # check for HUD files in resource folder
            resource_dir = folder_path / "resource"
            if resource_dir.exists():
                ui_dir = resource_dir / "ui"
                if ui_dir.exists() or (resource_dir / "../info.vdf").exists():
                    type_detected = "hud"

    except PermissionError:
        log.exception(f"Permission denied accessing folder: {folder_path}")
        errors.append(f"Permission denied accessing folder: {folder_path}")
    except Exception:
        log.exception("Error validating folder structure")
        errors.append("Error validating folder structure")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        type_detected=type_detected
    )


def validate_zip_structure(zip_file: zipfile.ZipFile) -> ValidationResult:
    # same thing as above but for zip files
    errors = []
    warnings = []
    found_mod_folders = []

    try:
        file_list = zip_file.namelist()
        vpk_files = [f for f in file_list if f.lower().endswith('.vpk')]
        if vpk_files:
            errors.append(
                f"ZIP file contains VPK files:\n"
                f"{chr(10).join(f'• {vpk}' for vpk in vpk_files[:10])}"
                f"{f'{chr(10)}• ... and {len(vpk_files) - 10} more VPK files' if len(vpk_files) > 10 else ''}\n\n"
                f"Please extract the VPK files from the ZIP and drag them directly instead.\n"
                f"VPK files should be dragged individually for proper processing."
            )
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                type_detected="vpk_container"
            )

        # ZIP structure
        potential_mod_dirs = set()
        second_level_structure = {}  # mod_dir -> set of subdirs

        for file_path in file_list:
            parts = file_path.split('/')
            if len(parts) >= 3:  # has at least mod_dir/subdir/file structure
                mod_dir = parts[0]
                sub_dir = parts[1]

                potential_mod_dirs.add(mod_dir)
                if mod_dir not in second_level_structure:
                    second_level_structure[mod_dir] = set()
                second_level_structure[mod_dir].add(sub_dir.lower())

        # check each potential mod directory for valid structure
        for mod_dir in potential_mod_dirs:
            subdirs = second_level_structure.get(mod_dir, set())
            valid_subdirs = []

            for valid_folder in VALID_MOD_ROOT_FOLDERS:
                if valid_folder.lower() in subdirs:
                    valid_subdirs.append(valid_folder)

            if valid_subdirs:
                found_mod_folders.append({
                    'name': mod_dir,
                    'valid_folders': valid_subdirs
                })

        if not found_mod_folders:
            # fallback: check if valid folders exist at root level
            top_level_dirs = set()
            for file_path in file_list:
                parts = file_path.split('/')
                if len(parts) > 1:
                    top_level_dirs.add(parts[0].lower())

            root_valid_folders = []
            for valid_folder in VALID_MOD_ROOT_FOLDERS:
                if valid_folder.lower() in top_level_dirs:
                    root_valid_folders.append(valid_folder)

            if root_valid_folders:
                found_mod_folders.append({
                    'name': 'root',
                    'valid_folders': root_valid_folders
                })
            else:
                errors.append(
                    f"ZIP file does not contain any valid mod structure.\n"
                    f"Expected structure: mod_name/materials/... etc. \n"
                    f"Found potential mod directories: {', '.join(potential_mod_dirs) if potential_mod_dirs else 'none'}\n"
                    f"Each mod directory should contain at least one of: {', '.join(VALID_MOD_ROOT_FOLDERS)}"
                )
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    type_detected="unknown"
                )

        type_detected = "unknown"
        if len(found_mod_folders) > 1:
            warnings.append(f"ZIP contains multiple mods: {', '.join([mod['name'] for mod in found_mod_folders])}")

        # HUD indicators
        for mod_info in found_mod_folders:
            if "resource" in [f.lower() for f in mod_info['valid_folders']]:
                hud_files = [f for f in file_list if f.startswith(mod_info['name'] + "/") and ('info.vdf' in f or 'resource/ui' in f)]
                if hud_files:
                    type_detected = "hud"

    except Exception as e:
        errors.append(f"Error validating ZIP structure: {str(e)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        type_detected=type_detected
    )


def validate_vpk_structure(vpk_path: Path) -> ValidationResult:
    # validate VPK structure without extracting
    errors = []
    warnings = []
    type_detected = "unknown"

    try:
        vpk_file = VPKFile(str(vpk_path))
        file_list = vpk_file.list_files()

        # analyze structure to determine type
        found_folders = set()

        for file_path in file_list:
            # get the first directory component
            parts = file_path.split('/')
            if len(parts) >= 2:
                root_folder = parts[0]
                found_folders.add(root_folder.lower())

        # check for valid mod root folders
        valid_folders = []
        for valid_folder in VALID_MOD_ROOT_FOLDERS:
            if valid_folder.lower() in found_folders:
                valid_folders.append(valid_folder)

        if not valid_folders:
            errors.append(
                f"VPK does not contain any valid mod folders.\n"
                f"Expected at least one of: {', '.join(VALID_MOD_ROOT_FOLDERS)}\n"
                f"Found folders: {', '.join(sorted(found_folders)) if found_folders else 'none'}"
            )

        # detect HUD mods
        if 'resource' in found_folders:
            has_info_vdf = any('info.vdf' in f for f in file_list)
            has_resource_ui = any('resource/ui' in f for f in file_list)
            if has_info_vdf and has_resource_ui:
                type_detected = "hud"

    except Exception as e:
        errors.append(f"Error validating VPK structure: {str(e)}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        type_detected=type_detected
    )


class StructureValidator:
     # empty set that can be used to filter problematic files in the future
    INVALID_EXTENSIONS = set()

    # valid mod root folders from constants
    MOD_INDICATORS = VALID_MOD_ROOT_FOLDERS
    HUD_INDICATORS = {'info.vdf', 'resource/ui', 'scripts/hudlayout.res'}

    def __init__(self, max_depth: int = 10):
        # this is not a magic number guys... right?
        self.max_depth = max_depth

    def validate_folder(self, folder_path: Path) -> ValidationResult:
        # validates folder against expected structure
        if not folder_path.exists() or not folder_path.is_dir():
            return ValidationResult(
                is_valid=False,
                errors=[f"Path does not exist or is not a directory: {folder_path}"],
                warnings=[],
                type_detected="unknown"
            )

        # check if this folder contains valid mod root folders
        mod_structure_result = validate_mod_structure(folder_path)
        if not mod_structure_result.is_valid:
            return mod_structure_result

        # scan for other issues (VPK files, etc.)
        scan_result = self._scan_directory(folder_path)

        return ValidationResult(
            is_valid=mod_structure_result.is_valid and scan_result.is_valid,
            errors=mod_structure_result.errors + scan_result.errors,
            warnings=mod_structure_result.warnings + scan_result.warnings,
            type_detected=mod_structure_result.type_detected if mod_structure_result.type_detected != "unknown" else scan_result.type_detected
        )

    def validate_zip(self, zip_path: Path) -> ValidationResult:
        # validate a zip file structure without extracting
        if not zip_path.exists() or not zip_path.is_file():
            return ValidationResult(
                is_valid=False,
                errors=[f"Path does not exist or is not a file: {zip_path}"],
                warnings=[],
                type_detected="unknown"
            )

        if not zip_path.suffix.lower() == '.zip':
            return ValidationResult(
                is_valid=False,
                errors=[f"File is not a zip file: {zip_path}"],
                warnings=[],
                type_detected="unknown"
            )

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                # check for valid mod structure in ZIP
                structure_result = validate_zip_structure(zip_file)
                if not structure_result.is_valid:
                    return structure_result

                # scan for other issues
                scan_result = self._scan_zip_contents(zip_file)

                return ValidationResult(
                    is_valid=structure_result.is_valid and scan_result.is_valid,
                    errors=structure_result.errors + scan_result.errors,
                    warnings=structure_result.warnings + scan_result.warnings,
                    type_detected=structure_result.type_detected if structure_result.type_detected != "unknown" else scan_result.type_detected
                )
        except zipfile.BadZipFile:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid or corrupted zip file: {zip_path}"],
                warnings=[],
                type_detected="unknown"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error reading zip file {zip_path}: {str(e)}"],
                warnings=[],
                type_detected="unknown"
            )

    @staticmethod
    def validate_vpk(vpk_path: Path) -> ValidationResult:
        if not vpk_path.exists() or not vpk_path.is_file():
            return ValidationResult(
                is_valid=False,
                errors=[f"Path does not exist or is not a file: {vpk_path}"],
                warnings=[],
                type_detected="unknown"
            )

        if not vpk_path.suffix.lower() == '.vpk':
            return ValidationResult(
                is_valid=False,
                errors=[f"File is not a VPK file: {vpk_path}"],
                warnings=[],
                type_detected="unknown"
            )

        try:
            structure_result = validate_vpk_structure(vpk_path)
            return structure_result
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error reading VPK file {vpk_path}: {str(e)}"],
                warnings=[],
                type_detected="unknown"
            )

    def _scan_directory(self, folder_path: Path, current_depth: int = 0) -> ValidationResult:
        # recursively scan directory for invalid content
        errors = []
        warnings = []
        found_files = set()
        found_dirs = set()

        if current_depth > self.max_depth:
            warnings.append(f"Maximum directory depth ({self.max_depth}) exceeded")
            return ValidationResult(
                is_valid=True,
                errors=errors,
                warnings=warnings,
                type_detected="unknown"
            )

        try:
            for item in folder_path.iterdir():
                if item.is_file():
                    # invalid file extensions
                    if item.suffix.lower() in self.INVALID_EXTENSIONS:
                        errors.append(f"Found nested VPK file: {item.relative_to(folder_path)}")

                    found_files.add(item.name.lower())

                elif item.is_dir():
                    found_dirs.add(item.name.lower())
                    # recursively check subdirectories
                    sub_result = self._scan_directory(item, current_depth + 1)
                    errors.extend(sub_result.errors)
                    warnings.extend(sub_result.warnings)

        except PermissionError:
            errors.append(f"Permission denied accessing: {folder_path}")
        except Exception as e:
            errors.append(f"Error scanning directory {folder_path}: {str(e)}")

        type_detected = self._detect_type(found_files, found_dirs)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            type_detected=type_detected
        )

    def _scan_zip_contents(self, zip_file: zipfile.ZipFile) -> ValidationResult:
        # scan zip file contents for invalid patterns
        errors = []
        warnings = []
        found_files = set()
        found_dirs = set()

        try:
            file_list = zip_file.namelist()

            for file_path in file_list:
                path_obj = Path(file_path)

                # check depth
                if len(path_obj.parts) > self.max_depth:
                    warnings.append(f"Deep directory structure found: {file_path}")

                # invalid extensions
                if path_obj.suffix.lower() in self.INVALID_EXTENSIONS:
                    errors.append(f"Found nested VPK file in zip: {file_path}")

                # track file and directory names
                found_files.add(path_obj.name.lower())
                for part in path_obj.parts[:-1]:  # all parts except filename
                    found_dirs.add(part.lower())

        except Exception as e:
            errors.append(f"Error reading zip contents: {str(e)}")

        type_detected = self._detect_type(found_files, found_dirs)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            type_detected=type_detected
        )

    def _detect_type(self, files: Set[str], dirs: Set[str]) -> str:
        # detect the type of mod based on files and directories found
        if any(indicator in files for indicator in self.HUD_INDICATORS):
            return "hud"

        if any(indicator in dirs for indicator in self.HUD_INDICATORS):
            return "hud"

        return "unknown"

import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional

from valve_parsers import VPKFile

from core.folder_setup import folder_setup
from core.operations.advanced_particle_merger import AdvancedParticleMerger
from core.structure_validator import StructureValidator
from core.util.zip import extract

log = logging.getLogger()


class ImportService:
    # mod extraction logic
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.validator = StructureValidator()

    def process_folder(
        self,
        folder_path: Path,
        override_name: str = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple[bool, str]:
        # attempt to process a folder
        folder_name = override_name if override_name else folder_path.name
        validation_result = self.validator.validate_folder(folder_path)

        try:
            # determine if it has particles
            has_particles = any((folder_path / "particles").glob("*.pcf"))

            if has_particles:
                destination = folder_setup.particles_dir / folder_name
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(folder_path, destination)

                # process with AdvancedParticleMerger
                particle_merger = AdvancedParticleMerger(
                    progress_callback=lambda p, m: progress_callback(50 + int(p / 2), m) if progress_callback else None
                )
                particle_merger.preprocess_vpk(destination)
            else:
                # it is an addon
                destination = folder_setup.addons_dir / folder_name
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(folder_path, destination)

                # create mod.json if it doesn't exist
                mod_json_path = destination / "mod.json"
                if not mod_json_path.exists():
                    default_mod_info = {
                        "addon_name": folder_name,
                        "type": validation_result.type_detected.title(),
                        "description": f"Content from folder: {folder_name}",
                        "contents": ["Custom content"]
                    }
                    with open(mod_json_path, 'w') as f:
                        json.dump(default_mod_info, f, indent=2)

            return True, f"Successfully processed folder {folder_name}"

        except Exception as e:
            log.exception(f"Error processing folder {folder_name}")
            return False, f"Error processing folder {folder_name}: {str(e)}"

    def process_zip_file(
        self,
        zip_path: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple[bool, str]:
        # attempt to process and extract a zip file
        zip_name = zip_path.stem

        try:
            # extract to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                extract(zip_path, temp_path)

                # analyze extracted structure to find mod folders
                extracted_items = list(temp_path.iterdir())

                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    # check if this folder contains valid mod structure
                    single_folder = extracted_items[0]
                    validation_result = self.validator.validate_folder(single_folder)
                    if validation_result.is_valid:
                        # process as single mod
                        success, message = self.process_folder(single_folder, progress_callback=progress_callback)
                        return success, message
                    else:
                        # zip might contain multiple mod subdirectories
                        # TODO: test this better
                        success_count = 0
                        for sub_item in single_folder.iterdir():
                            if sub_item.is_dir():
                                sub_validation = self.validator.validate_folder(sub_item)
                                if sub_validation.is_valid:
                                    success, _ = self.process_folder(sub_item, progress_callback=progress_callback)
                                    if success:
                                        success_count += 1
                        if success_count > 0:
                            return True, f"Successfully processed {success_count} mods from {zip_name}"
                        return False, f"No valid mods found in {zip_name}"

                else:
                    # check if the temp_path itself is a valid mod (has mod folders at root)
                    root_validation = self.validator.validate_folder(temp_path)
                    if root_validation.is_valid:
                        # use zip filename as the mod name
                        success, message = self.process_folder(temp_path, override_name=zip_name, progress_callback=progress_callback)
                        return success, message

                    # otherwise, process each valid mod folder
                    success_count = 0
                    for item in extracted_items:
                        if item.is_dir():
                            validation_result = self.validator.validate_folder(item)
                            if validation_result.is_valid:
                                success, _ = self.process_folder(item, progress_callback=progress_callback)
                                if success:
                                    success_count += 1
                    if success_count > 0:
                        return True, f"Successfully processed {success_count} mods from {zip_name}"
                    return False, f"No valid mods found in {zip_name}"

        except Exception as e:
            log.exception(f"Error processing ZIP file {zip_name}")
            return False, f"Error processing ZIP file {zip_name}: {str(e)}"

    def process_vpk_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple[bool, str]:
        # mod VPK extraction
        try:
            vpk_path = Path(file_path)
            vpk_name = vpk_path.stem
            if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == '_dir':
                vpk_name = vpk_name[:-4]

            # validate VPK structure to determine type
            if progress_callback:
                progress_callback(5, "Validating VPK structure...")
            validation_result = self.validator.validate_vpk(vpk_path)

            extracted_particles_dir = folder_setup.particles_dir / vpk_name
            extracted_addons_dir = folder_setup.addons_dir / vpk_name
            extracted_particles_dir.mkdir(parents=True, exist_ok=True)

            if progress_callback:
                progress_callback(10, "Analyzing VPK...")
            vpk_handler = VPKFile(str(file_path))

            # check for particles
            has_particles = bool(vpk_handler.find_files("*.pcf"))

            if progress_callback:
                progress_callback(15, "Extracting files...")
            extracted_count = vpk_handler.extract_all(str(extracted_particles_dir))
            if progress_callback:
                progress_callback(35, f"Extracted {extracted_count} files")

            # process with AdvancedParticleMerger if it has particles
            if has_particles:
                if progress_callback:
                    progress_callback(50, "Processing particles...")
                particle_merger = AdvancedParticleMerger(
                    progress_callback=lambda p, m: progress_callback(50 + int(p / 2), m) if progress_callback else None
                )
                particle_merger.preprocess_vpk(extracted_particles_dir)
            else:
                # for non-particle mods, create addon folder
                if progress_callback:
                    progress_callback(60, "Creating addon folder...")

                # if extracted_addons_dir already exists, remove it first
                if extracted_addons_dir.exists():
                    shutil.rmtree(extracted_addons_dir)

                # move the extracted files to the addons directory
                shutil.move(extracted_particles_dir, extracted_addons_dir)

                # create mod.json if it doesn't exist
                mod_json_path = extracted_addons_dir / "mod.json"
                if not mod_json_path.exists():
                    default_mod_info = {
                        "addon_name": vpk_name,
                        "type": validation_result.type_detected.title() if validation_result.type_detected != "unknown" else "Unknown",
                        "description": f"Content extracted from {vpk_path.name}",
                        "contents": ["Custom content"]
                    }
                    with open(mod_json_path, 'w') as f:
                        json.dump(default_mod_info, f, indent=2)

            return True, f"Successfully processed VPK {vpk_name}"

        except Exception as e:
            error_msg = f"Error processing VPK {Path(file_path).name}: {str(e)}"
            log.exception(error_msg)
            return False, error_msg

    def process_dropped_items(
        self,
        item_paths: list[str],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> tuple[list[str], list[tuple[str, str]]]:

        total_items = len(item_paths)
        successful_items = []
        failed_items = []

        for index, item_path in enumerate(item_paths):
            path_obj = Path(item_path)
            item_name = path_obj.name
            if progress_callback:
                progress_callback(0, f"Processing item {index + 1}/{total_items}")

            try:
                if path_obj.is_dir():
                    # folder
                    success, message = self.process_folder(path_obj, progress_callback=progress_callback)
                elif item_path.lower().endswith('.zip'):
                    # ZIP file
                    success, message = self.process_zip_file(path_obj, progress_callback=progress_callback)
                elif item_path.lower().endswith('.vpk'):
                    # VPK file
                    success, message = self.process_vpk_file(item_path, progress_callback=progress_callback)
                else:
                    failed_items.append((item_name, f"Unsupported file type: {item_name}"))
                    continue

                if success:
                    successful_items.append(item_name)
                else:
                    failed_items.append((item_name, message))

            except Exception as e:
                error_msg = f"Error processing {item_name}: {str(e)}"
                log.exception(error_msg)
                failed_items.append((item_name, error_msg))

        return successful_items, failed_items

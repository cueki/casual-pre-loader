import json
import logging
import tempfile
from pathlib import Path

from valve_parsers import VPKFile

from core.config import config
from core.operations.advanced_particle_merger import AdvancedParticleMerger
from core.structure_validator import StructureValidator
from core.util import NoopProgressCallback, ProgressCallback
from core.util.file import copy, delete, move
from core.util.zip import extract

log = logging.getLogger(__name__)


def normalize_vpk_paths(vpk_paths: list[Path]) -> list[Path]:
    '''
    Normalize and deduplicate VPK paths.
    Multi-part VPKs (mod_000.vpk, mod_001.vpk, mod_dir.vpk) all resolve to mod_dir.vpk.

    Args:
        vpk_paths: A list of paths to nromalize

    Return:
        A  list of normalized paths in the same order they were provided
    '''

    normalized = {}
    for vpk_path in vpk_paths:
        vpk_name = vpk_path.stem
        if (vpk_name[-3:].isdigit() and vpk_name[-4] == '_') or vpk_name[-4:] == "_dir":
            base_name = vpk_name[:-4]
            normalized[base_name] = vpk_path.parent / f"{base_name}_dir.vpk"
        else:
            normalized[vpk_name] = vpk_path
    return list(normalized.values())


class UnsupportedFileTypeError(Exception):
    pass


class ImportService:
    # mod extraction logic
    def __init__(self):
        self.validator = StructureValidator()

    def process_folder(
        self,
        folder_path: Path,
        folder_name: str | None = None,
        progress_callback: ProgressCallback = NoopProgressCallback
    ) -> None:
        '''
        Process a folder containing a mod

        Args:
            folder_path: Path to the folder to be processed
            folder_name: Optional new name to use for the resulting processed folder
            progress_callback: Optional callback to pass a progress metric and message to
        '''

        folder_name = folder_name or folder_path.name
        validation_result = self.validator.validate_folder(folder_path)

        try:
            has_particles = any((folder_path / 'particles').glob('*.pcf'))
            destination = (config.particles_dir if has_particles else config.addons_dir) / folder_name

            delete(destination, not_exist_ok=True)
            copy(folder_path, destination)

            if has_particles:
                particle_merger = AdvancedParticleMerger(
                    progress_callback=lambda p, m: progress_callback(50 + int(p / 2), m)
                )
                particle_merger.preprocess_vpk(destination)
            else:
                mod_json_path = destination / 'mod.json'
                if not mod_json_path.is_file():
                    default_mod_info = {
                        'addon_name': folder_name,
                        'type': validation_result.type_detected.title(),
                        'description': f'Content from folder: {folder_name}',
                        'contents': ['Custom content']
                    }
                    with mod_json_path.open('w') as fd:
                        json.dump(default_mod_info, fd, indent=4)
        except Exception:
            log.error(f'Error processing folder {folder_name}')
            raise

        log.info(f'Successfully processed folder {folder_name}')

    def process_zip_file(
        self,
        zip_path: Path,
        progress_callback: ProgressCallback = NoopProgressCallback
    ) -> None:
        '''
        Process and extract a zip file

        Args:
            zip_path: The path to the zip file to extract
            progress_callback: Optional callback to pass a progress metric and message to
        '''

        zip_name = zip_path.stem

        with tempfile.TemporaryDirectory() as temp_dir: # extract to temporary directory
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
                    self.process_folder(single_folder, progress_callback=progress_callback)
                else:
                    # zip might contain multiple mod subdirectories
                    # TODO: test this better
                    excs = []
                    for i, sub_item in enumerate(f for f in single_folder.iterdir() if f.is_dir() and self.validator.validate_folder(f).is_valid):
                        try:
                            self.process_folder(sub_item, progress_callback=progress_callback)
                        except Exception as e:  # ruff: ignore[blind-except]
                            excs.append(e)

                    if excs:
                        raise ExceptionGroup(f'No valid mods found in {zip_name}', excs)
                    log.info(f'Successfully processed {i} mods from {zip_name}')
            else:
                if self.validator.validate_folder(temp_path).is_valid: # check if the temp_path itself is a valid mod (has mod folders at root)
                    self.process_folder(temp_path, folder_name=zip_name, progress_callback=progress_callback) # use zip filename as the mod name
                else: # otherwise, process each valid mod folder
                    excs = []
                    for i, item in enumerate(f for f in extracted_items if f.is_dir() and self.validator.validate_folder(f).is_valid):
                        try:
                            self.process_folder(item, progress_callback=progress_callback)
                        except Exception as e:  # ruff: ignore[blind-except]
                            excs.append(e)

                    if excs:
                        raise ExceptionGroup(f'No valid mods found in {zip_name}', excs)
                    log.info(f'Successfully processed {i} mods from {zip_name}')

    def process_vpk_file(
        self,
        file_path: Path,
        progress_callback: ProgressCallback = NoopProgressCallback
    ) -> tuple[bool, str]:
        # mod VPK extraction
        try:
            vpk_name = file_path.stem
            if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == '_dir':
                vpk_name = vpk_name[:-4]

            # validate VPK structure to determine type
            progress_callback(5, 'Validating VPK structure...')
            validation_result = self.validator.validate_vpk(file_path)

            extracted_particles_dir = config.particles_dir / vpk_name
            extracted_addons_dir = config.addons_dir / vpk_name
            extracted_particles_dir.mkdir(parents=True, exist_ok=True)

            progress_callback(10, 'Analyzing VPK...')
            vpk_handler = VPKFile(file_path)

            # check for particles
            has_particles = bool(vpk_handler.find_files('*.pcf'))

            progress_callback(15, 'Extracting files...')
            extracted_count = vpk_handler.extract_all(str(extracted_particles_dir))
            progress_callback(35, f'Extracted {extracted_count} files')

            # process with AdvancedParticleMerger if it has particles
            if has_particles:
                progress_callback(50, 'Processing particles...')
                particle_merger = AdvancedParticleMerger(
                    progress_callback=lambda p, m: progress_callback(50 + int(p / 2), m)
                )
                particle_merger.preprocess_vpk(extracted_particles_dir)
            else:
                # for non-particle mods, create addon folder
                progress_callback(60, 'Creating addon folder...')

                # if extracted_addons_dir already exists, remove it first
                delete(extracted_addons_dir, not_exist_ok=True)

                # move the extracted files to the addons directory
                move(extracted_particles_dir, extracted_addons_dir)

                # create mod.json if it doesn't exist
                mod_json_path = extracted_addons_dir / 'mod.json'
                if not mod_json_path.is_file():
                    default_mod_info = {
                        'addon_name': vpk_name,
                        'type': validation_result.type_detected.title() if validation_result.type_detected != 'unknown' else 'Unknown',
                        'description': f'Content extracted from {file_path.name}',
                        'contents': ['Custom content']
                    }
                    with open(mod_json_path, 'w') as f:
                        json.dump(default_mod_info, f, indent=2)
        except Exception:
            log.error(f'Error processing VPK {file_path.name}')
            raise

        log.info(f'Successfully processed VPK {vpk_name}')

    def process_dropped_items(
        self,
        item_paths: list[Path],
        progress_callback: ProgressCallback = NoopProgressCallback
    ) -> None:
        '''
        Process items that have been dragged onto the main window.

        Args:
            item_paths: The items to process
            progress_callback: Optional callback to pass a progress metric and message to
        '''

        total_items = len(item_paths)

        excs = []
        for index, item_path in enumerate(item_paths):
            item_name = item_path.name
            progress_callback(0, f'Processing item {index + 1}/{total_items}')

            try:
                if item_path.is_dir():
                    self.process_folder(item_path, progress_callback=progress_callback)
                elif item_path.suffix.lower() == '.zip':
                    self.process_zip_file(item_path, progress_callback=progress_callback)
                elif item_path.suffix.lower() == '.vpk':
                    self.process_vpk_file(item_path, progress_callback=progress_callback)
                else:
                    raise UnsupportedFileTypeError(item_path)
            except Exception as e:  # ruff: ignore[blind-except]
                errormsg = ('Error processing %s', item_name)
                log.error(*errormsg)
                e.add_note(errormsg[0] % errormsg[1:])
                e.add_note(str(item_path))
                excs.append(e)

        if excs:
            raise ExceptionGroup('', excs)

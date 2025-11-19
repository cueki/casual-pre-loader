import json
import threading
import shutil
import zipfile
import tempfile
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox, QProgressDialog
from core.folder_setup import folder_setup
from core.constants import PARTICLE_SPLITS
from core.structure_validator import StructureValidator, ValidationResult
from valve_parsers import VPKFile, PCFFile
from gui.conflict_matrix import ConflictMatrix
from core.operations.advanced_particle_merger import AdvancedParticleMerger
from core.operations.pcf_merge import merge_pcf_files
from core.operations.pcf_rebuild import load_particle_system_map, get_pcf_element_names, extract_elements


def parse_vmt_texture(vmt_path):
    try:
        with open(vmt_path, 'r', encoding='utf-8') as f:
            lines = []
            for line in f:
                # skip commented lines
                if not line.strip().startswith('//'):
                    lines.append(line.lower())

            # join non-commented lines
            content = ''.join(lines)

        # this texture_paths_list should contain all the possible vtf files from a vmt that are mapped to these texture_params
        # this may need to be updated in the future to handle more possible paths
        texture_params = ['$basetexture', '$detail', '$ramptexture', '$normalmap', '$normalmap2']
        texture_paths_list = []

        # simple parsing for texture path
        for texture_param in texture_params:
            start_pos = 0

            while True:
                if texture_param in content:
                    # find the texture_params
                    pos = content.find(texture_param, start_pos)
                    if pos == -1:  # no more occurrences
                        break

                    param_end = pos + len(texture_param)
                    if param_end < len(content):
                        # check if the parameter is followed by whitespace or quote
                        if not (content[param_end].isspace() or content[param_end] in ['"', "'"]):
                            start_pos = pos + 1
                            continue

                    # find the end of the line
                    line_end = content.find('\n', pos)
                    comment_pos = content.find('//', pos)

                    # if there's a comment before the end of line, use that as the line end
                    if comment_pos != -1 and (comment_pos < line_end or line_end == -1):
                        line_end = comment_pos

                    # just in case no newline at end of file
                    if line_end == -1:
                        line_end = len(content)

                    # spec ops: the line
                    line = content[pos:line_end]

                    # check if the line ends with a quote
                    if line.rstrip().endswith('"') or line.rstrip().endswith("'"):
                        # if it does, find the matching opening quote
                        quote_char = line.rstrip()[-1]
                        value_end = line.rstrip().rfind(quote_char)
                        value_start = line.rfind(quote_char, 0, value_end - 1)
                        if value_start != -1:
                            texture_path = line[value_start + 1:value_end].strip()
                            texture_paths_list.append(Path(texture_path + '.vtf'))
                            texture_paths_list.append(Path(texture_path + '.vmt'))
                    else:
                        # look for tab or space after the parameter
                        param_end = pos + len(texture_param)
                        # skip initial whitespace after parameter name
                        while param_end < len(line) and line[param_end].isspace():
                            param_end += 1
                        # find the value - everything after whitespace until end of line
                        value_start = param_end
                        texture_path = line[value_start:].strip()
                        texture_paths_list.append(Path(texture_path + '.vtf'))
                        texture_paths_list.append(Path(texture_path + '.vmt'))

                    start_pos = line_end
                else:
                    break

        return texture_paths_list

    except Exception as e:
        print(f"Error parsing VMT file {vmt_path}: {e}")
        return None


def get_mod_particle_files():
    mod_particles = {}
    all_particles = set()

    # scan directories
    for vpk_dir in folder_setup.particles_dir.iterdir():
        if vpk_dir.is_dir():
            particle_dir = vpk_dir / "actual_particles"
            if particle_dir.exists():
                particles = [pcf.stem for pcf in particle_dir.glob("*.pcf")]
                mod_particles[vpk_dir.name] = particles
                all_particles.update(particles)

    return mod_particles, sorted(list(all_particles))


class VPKProcessWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)


class ModDropZone(QFrame):
    mod_dropped = pyqtSignal(str)
    addon_updated = pyqtSignal()

    def __init__(self, parent=None, settings_manager=None, rescan_callback=None):
        super().__init__(parent)
        self.drop_frame = None
        self.conflict_matrix = None
        self.settings_manager = settings_manager
        self.setAcceptDrops(True)
        self.setup_ui()
        self.processing = False
        self.progress_dialog = None
        self.worker = VPKProcessWorker()
        self.worker.finished.connect(self.on_process_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.show_error)
        self.worker.success.connect(self.show_success)
        self.rescan_callback = rescan_callback
        self.validator = StructureValidator()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.drop_frame = QFrame()

        drop_layout = QVBoxLayout(self.drop_frame)
        title = QLabel("Drag and drop VPKs, folders, or ZIP files here\n"
                       "(do not try and install them manually, it will break.)\n"
                       "Non-particle mods will appear in the addons section under the install tab.")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        drop_layout.addWidget(title)

        self.drop_frame.setStyleSheet("""
            QFrame {
                min-height: 50px;
            }
            QFrame[dragOver="true"] {
            }
        """)

        # conflict matrix
        self.conflict_matrix = ConflictMatrix(self.settings_manager)

        layout.addWidget(self.drop_frame)
        layout.addWidget(self.conflict_matrix)

    def apply_particle_selections(self):
        selections = self.conflict_matrix.get_selected_particles()
        required_materials = set()

        # process each mod that has selected particles
        used_mods = set(selections.values())
        for mod_name in used_mods:
            mod_dir = folder_setup.particles_dir / mod_name

            # copy selected particles
            source_particles_dir = mod_dir / "actual_particles"
            if source_particles_dir.exists():
                for particle_file, selected_mod in selections.items():
                    if selected_mod == mod_name:
                        source_file = source_particles_dir / (particle_file + ".pcf")
                        if source_file.exists():
                            # copy particle file to to_be_patched
                            shutil.copy2(source_file, folder_setup.temp_to_be_patched_dir / (particle_file + ".pcf"))
                            # get particle file mats from attrib
                            pcf = PCFFile(source_file).decode()
                            system_defs = pcf.get_elements_by_type('DmeParticleSystemDefinition')
                            for element in system_defs:
                                material_value = pcf.get_attribute_value(element, 'material')
                                if material_value and isinstance(material_value, bytes):
                                    material_path = material_value.decode('ascii')
                                    # ignore vgui/white
                                    if material_path == 'vgui/white':
                                        continue
                                    if material_path.endswith('.vmt'):
                                        required_materials.add(material_path)
                                    else:
                                        required_materials.add(material_path + ".vmt")

        for mod_name in used_mods:
            mod_dir = folder_setup.particles_dir / mod_name
            # process each required material
            for material_path in required_materials:
                full_material_path = mod_dir / 'materials' / material_path.replace('\\', '/')
                if full_material_path.exists():
                    material_destination = folder_setup.temp_to_be_vpk_dir / Path(full_material_path).relative_to(mod_dir)
                    material_destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(full_material_path), material_destination)
                    texture_paths = parse_vmt_texture(full_material_path)
                    if texture_paths:
                        for texture_path in texture_paths:
                            full_texture_path = mod_dir / 'materials' / str(texture_path).replace('\\', '/')
                            if full_texture_path.exists():
                                texture_destination = folder_setup.temp_to_be_vpk_dir / Path(full_texture_path).relative_to(
                                    mod_dir)
                                texture_destination.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(Path(full_texture_path), texture_destination)

        # merge split files back into original files
        for original_file, split_defs in PARTICLE_SPLITS.items():
            split_files_in_temp = []

            # check which split files exist in to_be_patched
            for split_name in split_defs.keys():
                split_path = folder_setup.temp_to_be_patched_dir / split_name
                if split_path.exists():
                    split_files_in_temp.append(split_path)

            # if we have splits for this original file, merge them
            if split_files_in_temp:
                pcf_parts = [PCFFile(split_file).decode() for split_file in split_files_in_temp]

                if len(pcf_parts) > 1:
                    merged = pcf_parts[0]
                    for pcf in pcf_parts[1:]:
                        merged = merge_pcf_files(merged, pcf)
                else:
                    merged = pcf_parts[0]

                output_path = folder_setup.temp_to_be_patched_dir / original_file
                merged.encode(output_path)

                for split_file in split_files_in_temp:
                    split_file.unlink()

        # fill in missing vanilla elements for reconstructed split files
        particle_map = load_particle_system_map(folder_setup.data_dir / 'particle_system_map.json')

        for original_file in PARTICLE_SPLITS.keys():
            merged_file = folder_setup.temp_to_be_patched_dir / original_file

            if merged_file.exists():
                merged_pcf = PCFFile(merged_file).decode()
                elements_we_have = get_pcf_element_names(merged_pcf)

                elements_we_still_need = set()
                for element in particle_map[f'particles/{original_file}']:
                    if element not in elements_we_have:
                        elements_we_still_need.add(element)

                if elements_we_still_need:
                    vanilla_file = folder_setup.temp_to_be_referenced_dir / original_file
                    if vanilla_file.exists():
                        vanilla_pcf = PCFFile(vanilla_file).decode()
                        vanilla_elements = extract_elements(vanilla_pcf, elements_we_still_need)
                        complete_pcf = merge_pcf_files(merged_pcf, vanilla_elements)
                        complete_pcf.encode(merged_file)

        return len(selections) > 0

    def validate_and_show_warnings(self, validation_result: ValidationResult, item_name: str) -> bool:
        # show validation warnings/errors and return whether to proceed
        if not validation_result.is_valid:
            error_msg = f"Cannot process '{item_name}':\n\n"
            error_msg += "\n".join(f"• {error}" for error in validation_result.errors)

            if validation_result.warnings:
                error_msg += f"\n\nWarnings:\n"
                error_msg += "\n".join(f"• {warning}" for warning in validation_result.warnings)

            QMessageBox.critical(self, "Invalid Structure", error_msg)
            return False

        # show warnings but allow processing
        if validation_result.warnings:
            warning_msg = f"Warnings found for '{item_name}':\n\n"
            warning_msg += "\n".join(f"• {warning}" for warning in validation_result.warnings)
            warning_msg += "\n\nDo you want to continue anyway?"

            reply = QMessageBox.question(self, "Validation Warnings", warning_msg,
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return reply == QMessageBox.StandardButton.Yes

        return True

    def process_folder(self, folder_path: Path, override_name: str = None) -> bool:
        # process a folder by copying it to the appropriate location
        folder_name = override_name if override_name else folder_path.name

        # re-validate to get the type information for processing
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
                    progress_callback=lambda p, m: self.worker.progress.emit(50 + int(p / 2), m)
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

            return True

        except Exception as e:
            self.worker.error.emit(f"Error processing folder {folder_name}: {str(e)}")
            return False

    def process_zip_file(self, zip_path: Path) -> bool:
        zip_name = zip_path.stem

        try:
            # extract to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(temp_path)

                # analyze extracted structure to find mod folders
                extracted_items = list(temp_path.iterdir())

                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    # check if this folder contains valid mod structure
                    single_folder = extracted_items[0]
                    validation_result = self.validator.validate_folder(single_folder)
                    if validation_result.is_valid:
                        # process as single mod
                        return self.process_folder(single_folder)
                    else:
                        # zip might contain multiple mod subdirectories
                        # TODO: test this better
                        success_count = 0
                        for sub_item in single_folder.iterdir():
                            if sub_item.is_dir():
                                sub_validation = self.validator.validate_folder(sub_item)
                                if sub_validation.is_valid:
                                    if self.process_folder(sub_item):
                                        success_count += 1
                        return success_count > 0

                else:
                    # check if the temp_path itself is a valid mod (has mod folders at root)
                    root_validation = self.validator.validate_folder(temp_path)
                    if root_validation.is_valid:
                        # use zip filename as the mod name
                        return self.process_folder(temp_path, override_name=zip_name)

                    # otherwise, process each valid mod folder
                    success_count = 0
                    for item in extracted_items:
                        if item.is_dir():
                            validation_result = self.validator.validate_folder(item)
                            if validation_result.is_valid:
                                if self.process_folder(item):
                                    success_count += 1
                    return success_count > 0

        except zipfile.BadZipFile:
            self.worker.error.emit(f"Invalid ZIP file: {zip_name}")
            return False
        except Exception as e:
            self.worker.error.emit(f"Error processing ZIP file {zip_name}: {str(e)}")
            return False

    def update_matrix(self):
        # get mod information and all unique particle files
        mod_particles, all_particles = get_mod_particle_files()

        if not mod_particles:
            # clear the matrix if there are no mods
            self.conflict_matrix.setRowCount(0)
            self.conflict_matrix.setColumnCount(0)
            return

        mods = list(mod_particles.keys())
        self.conflict_matrix.update_matrix(mods, all_particles)
        # checkbox enable/disable logic is now handled inside update_matrix() / _setup_matrix_cells()

    def update_progress(self, value, message):
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        QMessageBox.information(self, "Success", message)

    def on_process_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
        self.update_matrix()
        self.rescan_callback()
        self.processing = False

    def process_dropped_items(self, dropped_paths):
        # process a list of dropped items (VPKs, folders, or ZIP files)
        total_items = len(dropped_paths)
        successful_items = []

        for index, item_path in enumerate(dropped_paths):
            path_obj = Path(item_path)
            item_name = path_obj.name
            self.worker.progress.emit(0, f"Processing item {index + 1}/{total_items}")

            try:
                if path_obj.is_dir():
                    # folder
                    if self.process_folder(path_obj):
                        successful_items.append(item_name)
                elif item_path.lower().endswith('.zip'):
                    # ZIP file
                    if self.process_zip_file(path_obj):
                        successful_items.append(item_name)
                elif item_path.lower().endswith('.vpk'):
                    # VPK file
                    if self.process_single_vpk(item_path):
                        successful_items.append(item_name)
                else:
                    self.worker.error.emit(f"Unsupported file type: {item_name}")

            except Exception as e:
                self.worker.error.emit(f"Error processing {item_name}: {str(e)}")

        if successful_items:
            self.addon_updated.emit()
            if len(successful_items) == 1:
                self.worker.success.emit(f"Successfully processed {successful_items[0]}")
            else:
                items_text = ",\n".join(successful_items)
                self.worker.success.emit(f"Successfully processed {len(successful_items)} items:\n{items_text}")

        self.worker.finished.emit()

    def process_single_vpk(self, file_path) -> bool:
        # process a single VPK file
        try:
            vpk_name = Path(file_path).stem
            if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == '_dir':
                vpk_name = vpk_name[:-4]

            extracted_particles_dir = folder_setup.particles_dir / vpk_name
            extracted_addons_dir = folder_setup.addons_dir / vpk_name
            extracted_particles_dir.mkdir(parents=True, exist_ok=True)

            self.worker.progress.emit(10, "Analyzing VPK...")
            vpk_handler = VPKFile(str(file_path))

            # check for particles
            has_particles = bool(vpk_handler.find_files("*.pcf"))

            self.worker.progress.emit(15, "Extracting files...")
            extracted_count = vpk_handler.extract_all(str(extracted_particles_dir))
            self.worker.progress.emit(35, f"Extracted {extracted_count} files")

            # process with AdvancedParticleMerger if it has particles
            if has_particles:
                self.worker.progress.emit(50, "Processing particles...")
                particle_merger = AdvancedParticleMerger(
                    progress_callback=lambda p, m: self.worker.progress.emit(50 + int(p / 2), m)
                )
                particle_merger.preprocess_vpk(extracted_particles_dir)
            else:
                # for non-particle mods, create addon folder
                self.worker.progress.emit(60, "Creating addon folder...")

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
                        "type": "Unknown",
                        "description": f"Content extracted from {Path(file_path).name}",
                        "contents": ["Custom content"]
                    }
                    with open(mod_json_path, 'w') as f:
                        json.dump(default_mod_info, f, indent=2)

            return True

        except Exception as e:
            self.worker.error.emit(f"Error processing VPK {Path(file_path).name}: {str(e)}")
            return False


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                path_obj = Path(file_path)

                # accept VPK files, directories, and ZIP files
                if (file_path.lower().endswith('.vpk') or
                    path_obj.is_dir() or
                    file_path.lower().endswith('.zip')):
                    event.accept()
                    self.setProperty('dragOver', True)
                    self.style().polish(self)
                    return

    def dragLeaveEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

    def dropEvent(self, event):
        if self.processing:
            QMessageBox.warning(self, "Processing in Progress",
                                "Please wait for the current operation to complete.")
            return

        self.setProperty('dragOver', False)
        self.style().polish(self)
        folder_setup.create_required_folders()

        # collect all dropped items
        dropped_items = []
        normalized_vpks = {}

        for url in event.mimeData().urls():
            item_path = url.toLocalFile()
            path_obj = Path(item_path)

            # handle different file types
            if path_obj.is_dir():
                # validate folder structure
                validation_result = self.validator.validate_folder(path_obj)
                if not self.validate_and_show_warnings(validation_result, path_obj.name):
                    continue
                dropped_items.append(item_path)
            elif item_path.lower().endswith('.zip'):
                # ZIP file
                if path_obj.name.count('.') > 1:
                    QMessageBox.warning(self, "Invalid Filename",
                                        f"File '{path_obj.name}' contains multiple periods.\n\n"
                                        f"Please rename the file and try again.")
                    continue
                # validate ZIP structure
                validation_result = self.validator.validate_zip(path_obj)
                if not self.validate_and_show_warnings(validation_result, path_obj.stem):
                    continue
                dropped_items.append(item_path)
            elif item_path.lower().endswith('.vpk'):
                # VPK file
                if path_obj.name.count('.') > 1:
                    QMessageBox.warning(self, "Invalid Filename",
                                        f"File '{path_obj.name}' contains multiple periods.\n\n"
                                        f"Please rename the file and try again.")
                    continue

                vpk_name = path_obj.stem
                if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == "_dir":
                    base_name = vpk_name[:-4]
                    normalized_vpks[base_name] = str(path_obj.parent / f"{base_name}_dir.vpk")
                else:
                    normalized_vpks[vpk_name] = item_path
            else:
                QMessageBox.warning(self, "Unsupported File Type",
                                    f"File type not supported: {path_obj.name}\n\n"
                                    f"Supported types: VPK files, folders, ZIP files")
                continue

        # add normalized VPK files to dropped items
        dropped_items.extend(normalized_vpks.values())

        if not dropped_items:
            return

        has_vpk = any(item.lower().endswith('.vpk') for item in dropped_items)
        has_zip = any(item.lower().endswith('.zip') for item in dropped_items)
        has_folder = any(Path(item).is_dir() for item in dropped_items)

        if has_vpk and has_zip and has_folder:
            dialog_title = "Processing Mixed Items"
            dialog_text = "Processing files..."
        elif has_vpk and (has_zip or has_folder):
            dialog_title = "Processing Items"
            dialog_text = "Processing items..."
        elif has_vpk:
            dialog_title = "Processing VPKs"
            dialog_text = "Processing VPK files..."
        elif has_zip:
            dialog_title = "Processing ZIP Files"
            dialog_text = "Processing ZIP files..."
        else:
            dialog_title = "Processing Folders"
            dialog_text = "Processing folders..."

        # start processing in a thread
        self.processing = True
        self.progress_dialog = QProgressDialog(dialog_text, "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle(dialog_title)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setFixedSize(275, 75)
        self.progress_dialog.show()

        process_thread = threading.Thread(
            target=self.process_dropped_items,
            args=(dropped_items,),
            daemon=True
        )
        process_thread.start()

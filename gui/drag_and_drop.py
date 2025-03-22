import os
import threading
import zipfile
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox, QProgressDialog
from core.folder_setup import folder_setup
from core.parsers.vpk_file import VPKFile
from core.parsers.pcf_file import PCFFile
from gui.conflict_matrix import ConflictMatrix
from operations.advanced_particle_merger import AdvancedParticleMerger


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
        texture_params = ['$basetexture', '$detail', '$ramptexture']
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

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.drop_frame = QFrame()

        drop_layout = QVBoxLayout(self.drop_frame)
        title = QLabel("Drag and drop VPKs here (do not try and install them manually, it will break.)\n"
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
                            # copy particle file
                            shutil.copy2(source_file, folder_setup.temp_mods_dir / (particle_file + ".pcf"))
                            # get particle file mats from attrib
                            pcf = PCFFile(source_file).decode()
                            for element in pcf.elements:
                                type_name = pcf.string_dictionary[element.type_name_index]
                                if type_name == b'DmeParticleSystemDefinition':
                                    if b'material' in element.attributes:
                                        attr_type, value = element.attributes[b'material']
                                        if isinstance(value, bytes):
                                            material_path = value.decode('ascii')
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
                    material_destination = folder_setup.temp_mods_dir / Path(full_material_path).relative_to(mod_dir)
                    material_destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(full_material_path), material_destination)
                    texture_paths = parse_vmt_texture(full_material_path)
                    if texture_paths:
                        for texture_path in texture_paths:
                            full_texture_path = mod_dir / 'materials' / str(texture_path).replace('\\', '/')
                            if full_texture_path.exists():
                                texture_destination = folder_setup.temp_mods_dir / Path(full_texture_path).relative_to(
                                    mod_dir)
                                texture_destination.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(Path(full_texture_path), texture_destination)

        return len(selections) > 0

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

        # enable/disable checkboxes based on which mods have which particles
        for row, mod_name in enumerate(mods):
            mod_particles_set = set(mod_particles[mod_name])
            for col, particle in enumerate(all_particles):
                cell_widget = self.conflict_matrix.cellWidget(row, col + 1)  # add +1 for Select All column
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    checkbox.setEnabled(particle in mod_particles_set)

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

    def process_vpk_files(self, file_paths):
        total_files = len(file_paths)
        successful_files = []

        for index, file_path in enumerate(file_paths):
            file_name = Path(file_path).name
            self.worker.progress.emit(0, f"Processing file {index + 1}/{total_files}: {file_name}")

            try:
                vpk_name = Path(file_path).stem
                if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == '_dir':
                    vpk_name = vpk_name[:-4]

                extracted_particles_dir = folder_setup.particles_dir / vpk_name
                extracted_addons_dir = folder_setup.addons_dir / vpk_name
                extracted_particles_dir.mkdir(parents=True, exist_ok=True)

                self.worker.progress.emit(10, f"Analyzing VPK: {vpk_name}")
                vpk_handler = VPKFile(str(file_path))
                vpk_handler.parse_directory()
                file_list = vpk_handler.list_files()

                # check for particles
                has_particles = any('.pcf' in f for f in file_list)

                # extract all files
                total_files_in_vpk = len(file_list)
                for i, file_path_in_vpk in enumerate(file_list):
                    progress = 10 + int((i / total_files_in_vpk) * 40)
                    self.worker.progress.emit(progress, f"Extracting file {i + 1}/{total_files_in_vpk}")

                    relative_path = Path(file_path_in_vpk)
                    output_path = extracted_particles_dir / relative_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    vpk_handler.extract_file(file_path_in_vpk, str(output_path))

                # process with AdvancedParticleMerger if it has particles
                if has_particles:
                    self.worker.progress.emit(50, f"Processing particles for {vpk_name}")
                    particle_merger = AdvancedParticleMerger(
                        progress_callback=lambda p, m: self.worker.progress.emit(50 + int(p / 2), m)
                    )
                    particle_merger.preprocess_vpk(extracted_particles_dir)
                else:
                    # for non-particle mods, zip and move to addons
                    self.worker.progress.emit(60, f"Creating addon for {vpk_name}")
                    zip_path = extracted_addons_dir.with_suffix('.zip')

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zip_f:
                        # walk through all files in the extracted directory
                        all_files = []
                        for root, _, files in os.walk(extracted_particles_dir):
                            for file in files:
                                file_path_in_dir = Path(root) / file
                                # make sure the file has an extension (for vpk module)
                                if file_path_in_dir.suffix:
                                    all_files.append(
                                        (file_path_in_dir, file_path_in_dir.relative_to(extracted_particles_dir)))

                        for i, (file_path_entry, arc_path) in enumerate(all_files):
                            progress = 60 + int((i / len(all_files)) * 40)
                            self.worker.progress.emit(progress, f"Adding to zip: {arc_path}")
                            zip_f.write(file_path_entry, arc_path)

                    shutil.rmtree(extracted_particles_dir)

                # hacky refresh
                main_window = self.window()
                main_window.load_addons()

                successful_files.append(vpk_name)

            except Exception as e:
                self.worker.error.emit(f"Error processing {file_name}: {str(e)}")

        if successful_files:
            if len(successful_files) == 1:
                self.worker.success.emit(f"Successfully processed {successful_files[0]}")
            else:
                file_list_text = ",\n".join(successful_files)
                self.worker.success.emit(f"Successfully processed {len(successful_files)} files:\n{file_list_text}")

        self.worker.finished.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.vpk'):
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

        # Use a dictionary to store normalized paths and their original files
        normalized_files = {}

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()

            # disallow any files that have more than 1 '.' in its name
            if Path(file_path).name.count('.') > 1:
                QMessageBox.warning(self, "Invalid Filename",
                                    f"File '{Path(file_path).name}' contains multiple periods.\n\n"
                                    f"Please rename the file and try again.")
                continue

            path = Path(file_path)
            vpk_name = path.stem

            if vpk_name[-3:].isdigit() and vpk_name[-4] == '_' or vpk_name[-4:] == "_dir":
                base_name = vpk_name[:-4]
                normalized_files[base_name] = str(path.parent / f"{base_name}_dir.vpk")
            else:
                normalized_files[vpk_name] = file_path

        valid_files = normalized_files.values()

        if not valid_files:
            return

        # start processing in a thread
        self.processing = True
        self.progress_dialog = QProgressDialog("Processing VPK files...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Processing VPKs")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.setFixedSize(600, 75)
        self.progress_dialog.show()

        process_thread = threading.Thread(
            target=self.process_vpk_files,
            args=(valid_files,),
            daemon=True
        )
        process_thread.start()

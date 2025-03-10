import os
import zipfile
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox
from core.folder_setup import folder_setup
from core.handlers.vpk_handler import VPKHandler
from core.parsers.pcf_file import PCFFile
from gui.conflict_matrix import ConflictMatrix
from operations.advanced_particle_merger import AdvancedParticleMerger


def parse_vmt_texture(vmt_path):
    texture_path = None
    texture_param = '$basetexture'

    try:
        with open(vmt_path, 'r', encoding='utf-8') as f:
            # read file line by line to properly handle comments
            lines = []
            for line in f:
                # skip commented lines
                if not line.strip().startswith('//'):
                    lines.append(line.lower())

            # join non-commented lines
            content = ''.join(lines)

        # simple parsing for texture path
        if texture_param in content:
            # find the $basetexture
            pos = content.find(texture_param)
            if pos != -1:
                # find the end of the line
                line_end = content.find('\n', pos)

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
                else:
                    # look for tab or space after the parameter
                    param_end = pos + len(texture_param)
                    # skip initial whitespace after parameter name
                    while param_end < len(line) and line[param_end].isspace():
                        param_end += 1

                    # find the value - everything after whitespace until end of line
                    value_start = param_end
                    texture_path = line[value_start:].strip()

        if texture_path:
            return Path(texture_path + '.vtf')

    except Exception as e:
        print(f"Error parsing VMT file {vmt_path}: {e}")
        return None


def get_mod_particle_files():
    mod_particles = {}
    all_particles = set()

    # scan directories
    for vpk_dir in folder_setup.user_mods_dir.iterdir():
        if vpk_dir.is_dir():
            particle_dir = vpk_dir / "actual_particles"
            if particle_dir.exists():
                particles = [pcf.stem for pcf in particle_dir.glob("*.pcf")]
                mod_particles[vpk_dir.name] = particles
                all_particles.update(particles)

    return mod_particles, sorted(list(all_particles))


class ModDropZone(QFrame):
    mod_dropped = pyqtSignal(str)

    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.drop_frame = None
        self.conflict_matrix = None
        self.settings_manager = settings_manager
        self.setAcceptDrops(True)
        self.setup_ui()

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

        # only copy what we care about
        required_materials = set()

        # process each mod that has selected particles
        used_mods = set(selections.values())
        for mod_name in used_mods:
            mod_dir = folder_setup.user_mods_dir / mod_name

            # copy selected particles
            source_particles_dir = mod_dir / "actual_particles"
            if source_particles_dir.exists():
                for particle_file, selected_mod in selections.items():
                    if selected_mod == mod_name:
                        source_file = source_particles_dir / (particle_file + ".pcf")
                        if source_file.exists():
                            # copy particle file
                            shutil.copy2(source_file, folder_setup.mods_particle_dir / (particle_file + ".pcf"))
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
            mod_dir = folder_setup.user_mods_dir / mod_name
            # process each required material
            for material_path in required_materials:
                full_material_path = mod_dir / 'materials' / material_path
                if full_material_path.exists():
                    material_destination = folder_setup.mods_everything_else_dir / Path(full_material_path).relative_to(mod_dir)
                    material_destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(Path(full_material_path), material_destination)
                    texture_path = parse_vmt_texture(full_material_path)
                    if texture_path:
                        full_texture_path = Path(mod_dir / 'materials' / texture_path)
                        if full_texture_path.exists():
                            texture_destination = folder_setup.mods_everything_else_dir / Path(full_texture_path).relative_to(mod_dir)
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
                cell_widget = self.conflict_matrix.cellWidget(row, col + 1)  # Add +1 for Select All column
                if cell_widget:
                    checkbox = cell_widget.layout().itemAt(0).widget()
                    checkbox.setEnabled(particle in mod_particles_set)

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
        self.setProperty('dragOver', False)
        self.style().polish(self)
        folder_setup.create_required_folders()

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()

            # disallow any files that have more than 1 '.' in its name (stinky)
            if Path(file_path).name.count('.') > 1:
                QMessageBox.warning(self, "Invalid Filename",
                                   f"File '{Path(file_path).name}' contains multiple periods in its name.\n\n"
                                   f"Please rename the file to contain only one period (for the extension) and try again.")
                continue

            try:
                vpk_name = Path(file_path).stem
                extracted_user_mods_dir = folder_setup.user_mods_dir / vpk_name
                extracted_addons_dir = folder_setup.addons_dir / vpk_name
                extracted_user_mods_dir.mkdir(parents=True, exist_ok=True)

                # extract VPK contents
                vpk_handler = VPKHandler(file_path)
                file_list = vpk_handler.list_files()

                # check for particles folder
                has_particles = any('particles/' in f for f in file_list)

                # extract all files
                for file_path in file_list:
                    relative_path = Path(file_path)
                    output_path = extracted_user_mods_dir / relative_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    vpk_handler.extract_file(file_path, str(output_path))

                # process with AdvancedParticleMerger if it has particles
                if has_particles:
                    particle_merger = AdvancedParticleMerger()
                    particle_merger.preprocess_vpk(extracted_user_mods_dir)
                else:
                    # for non-particle mods, zip and move to addons
                    zip_path = extracted_addons_dir.with_suffix('.zip')

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_f:
                        # walk through all files in the extracted directory
                        for root, _, files in os.walk(extracted_user_mods_dir):
                            for file in files:
                                file_path = Path(root) / file
                                # make sure the file has an extension (the vpk module cant handle them later on)
                                if file_path.suffix:
                                    # calculate relative path for the archive
                                    arc_path = file_path.relative_to(extracted_user_mods_dir)
                                    # add file to the archive
                                    zip_f.write(file_path, arc_path)

                    # clean up the extracted directory after zipping
                    shutil.rmtree(extracted_user_mods_dir)
                    # hacky refresh
                    main_window = self.window()
                    main_window.load_addons()

                self.update_matrix()
                self.mod_dropped.emit(str(file_path))

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process VPK: {str(e)}")

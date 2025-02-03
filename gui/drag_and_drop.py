import os
import zipfile
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox
from core.folder_setup import folder_setup
from gui.conflict_matrix import ConflictMatrix
from handlers.vpk_handler import VPKHandler
import shutil
from tools.advanced_particle_merger import AdvancedParticleMerger


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drop_frame = None
        self.conflict_matrix = None
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
        self.conflict_matrix = ConflictMatrix()

        layout.addWidget(self.drop_frame)
        layout.addWidget(self.conflict_matrix)

    def apply_particle_selections(self):
        selections = self.conflict_matrix.get_selected_particles()

        folder_setup.cleanup_temp_folders()
        folder_setup.create_required_folders()

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
                            shutil.copy2(source_file, folder_setup.mods_particle_dir / (particle_file + ".pcf"))

            # Copy all other non-particle content
            for item in mod_dir.iterdir():
                if item.name not in ['particles', 'actual_particles']:
                    destination = folder_setup.mods_everything_else_dir / item.relative_to(mod_dir)
                    if item.is_file():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, destination)
                    elif item.is_dir():
                        shutil.copytree(item, destination, dirs_exist_ok=True)

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

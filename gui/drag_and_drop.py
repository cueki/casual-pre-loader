from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox, QTableWidget, QHeaderView, QTableWidgetItem, \
    QCheckBox, QWidget, QHBoxLayout
from core.folder_setup import folder_setup
from handlers.vpk_handler import VPKHandler
import shutil
from tools.advanced_particle_merger import AdvancedParticleMerger


class ConflictMatrix(QTableWidget):
    def __init__(self):
       super().__init__()
       self.setStyleSheet("QTableWidget { border: 1px solid #ccc; }")
       self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
       self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
       self.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

    def update_matrix(self, mods, pcf_files):
        self.setColumnCount(len(pcf_files))
        self.setRowCount(len(mods))
        self.setHorizontalHeaderLabels(pcf_files)

        for row, mod in enumerate(mods):
            name_item = QTableWidgetItem(mod)
            self.setVerticalHeaderItem(row, name_item)

            for col, _ in enumerate(pcf_files):
                cell_widget = QCheckBox()
                self.setCellWidget(row, col, cell_widget)


class ModDropZone(QFrame):
    mod_dropped = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)

        # original drop zone
        self.drop_frame = QFrame()
        self.drop_frame.setAcceptDrops(True)
        self.drop_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.drop_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 2px dashed #aaa;
                border-radius: 5px;
                min-height: 100px;
            }
            QFrame[dragOver="true"] {
                background-color: #e1e1e1;
                border-color: #666;
            }
        """)

        drop_layout = QVBoxLayout(self.drop_frame)
        title = QLabel("Drag and drop VPK mods here")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        drop_layout.addWidget(title)

        # conflict matrix
        self.conflict_matrix = ConflictMatrix()

        layout.addWidget(self.drop_frame)
        layout.addWidget(self.conflict_matrix)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.vpk'):
                    event.accept()
                    self.setProperty('dragOver', True)
                    self.style().polish(self)
                    return
        event.ignore()

    def update_matrix(self):
        mods = []
        pcf_files = set()

        # scan directories
        for vpk_dir in folder_setup.user_mods_dir.iterdir():
            if vpk_dir.is_dir():
                particle_dir = vpk_dir / "actual_particles"
                if particle_dir.exists():
                    mods.append(vpk_dir.name)
                    for pcf in particle_dir.glob("*.pcf"):
                        pcf_files.add(pcf.name)

        pcf_files = sorted(list(pcf_files))

        # set up matrix
        self.conflict_matrix.setColumnCount(len(pcf_files))
        self.conflict_matrix.setRowCount(len(mods))

        # set headers without .pcf extension
        header_labels = [pcf.replace('.pcf', '') for pcf in pcf_files]
        self.conflict_matrix.setHorizontalHeaderLabels(header_labels)
        self.conflict_matrix.setVerticalHeaderLabels(mods)

        # add centered checkboxes
        for row in range(len(mods)):
            for col in range(len(pcf_files)):
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)

                checkbox = QCheckBox()
                layout.addWidget(checkbox)
                self.conflict_matrix.setCellWidget(row, col, cell_widget)

    def dragLeaveEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            try:
                vpk_name = Path(file_path).stem
                extracted_dir = folder_setup.user_mods_dir / vpk_name
                extracted_dir.mkdir(parents=True, exist_ok=True)

                # extract VPK contents
                vpk_handler = VPKHandler(file_path)
                file_list = vpk_handler.list_files()

                # check for particles folder
                has_particles = any('particles/' in f for f in file_list)

                # extract all files
                for file_path in file_list:
                    relative_path = Path(file_path)
                    output_path = extracted_dir / relative_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    vpk_handler.extract_file(file_path, str(output_path))

                # process with AdvancedParticleMerger if it has particles
                if has_particles:
                    particle_merger = AdvancedParticleMerger()
                    particle_merger.preprocess_vpk(extracted_dir)
                else:
                    # for non-particle mods, copy to everything_else
                    everything_else = folder_setup.mods_everything_else_dir
                    everything_else.mkdir(parents=True, exist_ok=True)
                    for item in extracted_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, everything_else / item.name)
                        else:
                            shutil.copytree(item, everything_else / item.name, dirs_exist_ok=True)
                self.update_matrix()
                self.mod_dropped.emit(str(file_path))

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process VPK: {str(e)}")
                # Clean up on error
                if 'extracted_dir' in locals() and extracted_dir.exists():
                    shutil.rmtree(extracted_dir)

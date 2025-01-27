from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QMessageBox
from core.folder_setup import folder_setup
from handlers.vpk_handler import VPKHandler
from zipfile import ZipFile
import shutil

def check_if_particle_mod(vpk_path: str) -> bool:
    handler = VPKHandler(vpk_path)
    files = handler.find_files("particles/*")
    return len(files) == 0


def check_if_sound_mod(vpk_path: str) -> bool:
    handler = VPKHandler(vpk_path)
    files = handler.find_files("sound/*")
    return len(files) == 0


class DragDropZone(QFrame):
    addon_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setStyleSheet("""
            DragDropZone {
                background-color: #f0f0f0;
                border: 2px dashed #aaa;
                border-radius: 5px;
                min-height: 100px;
            }
            DragDropZone[dragOver="true"] {
                background-color: #e1e1e1;
                border-color: #666;
            }
        """)

        layout = QVBoxLayout(self)
        label = QLabel("Drag and drop any non-particle mod here")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile().lower()
                if file_path.endswith('.vpk'):
                    event.accept()
                    self.setProperty('dragOver', True)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.vpk'):
                if not check_if_particle_mod(file_path):
                    QMessageBox.critical(self, "Error",
                                       "VPK file contains particle files and cannot be used as an addon.")
                    continue
                if not check_if_sound_mod(file_path):
                    QMessageBox.warning(self, "Warning",
                                       "The sound files found in this VPK will not work yet."
                                       "\nComing in future release, stay tuned!")
                try:
                    # create addon directory with VPK name
                    vpk_name = Path(file_path).stem
                    extracted_addon_dir = folder_setup.addons_dir / vpk_name
                    extracted_addon_dir.mkdir(parents=True, exist_ok=True)

                    # extract VPK contents to the addon directory
                    vpk_handler = VPKHandler(file_path)
                    file_list = vpk_handler.list_files()

                    for file_path in file_list:
                        relative_path = Path(file_path)
                        output_path = extracted_addon_dir / relative_path
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        vpk_handler.extract_file(file_path, str(output_path))

                    # create a zip file from the extracted contents
                    zip_path = Path('addons') / f"{vpk_name}.zip"
                    with ZipFile(str(zip_path), 'w') as zip_f:
                        for file_path in file_list:
                            relative_path = Path(file_path)
                            zip_f.write((extracted_addon_dir / relative_path), str(relative_path))

                    # clean up the temporary directory
                    shutil.rmtree(extracted_addon_dir)
                    self.addon_dropped.emit(str(zip_path))

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to process VPK: {str(e)}")

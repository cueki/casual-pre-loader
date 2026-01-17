import logging
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QMessageBox, QProgressDialog, QVBoxLayout

from core.folder_setup import folder_setup
from core.services.importer import ImportService, normalize_vpk_paths
from core.structure_validator import StructureValidator, ValidationResult
from core.util.pcf_path_walk import apply_particle_selections, get_mod_particles
from gui.conflict_matrix import ConflictMatrix

log = logging.getLogger()


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
        self.service = ImportService(settings_manager)

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
        return apply_particle_selections(selections)

    def validate_and_show_warnings(self, validation_result: ValidationResult, item_name: str) -> bool:
        # show validation warnings/errors and return whether to proceed
        if not validation_result.is_valid:
            error_msg = f"Cannot process '{item_name}':\n\n"
            error_msg += "\n".join(f"• {error}" for error in validation_result.errors)

            if validation_result.warnings:
                error_msg += "\n\nWarnings:\n"
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

    def update_matrix(self):
        # get mod information and all unique particle files
        mod_particles, all_particles = get_mod_particles()

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
        # just a wrapper for the services
        successful_items, failed_items = self.service.process_dropped_items(
            dropped_paths,
            progress_callback=self.worker.progress.emit
        )

        # emit errors for failed items
        for item_name, error_msg in failed_items:
            self.worker.error.emit(error_msg)

        # emit success message and update addon list
        if successful_items:
            self.addon_updated.emit()
            if len(successful_items) == 1:
                self.worker.success.emit(f"Successfully processed {successful_items[0]}")
            else:
                items_text = ",\n".join(successful_items)
                self.worker.success.emit(f"Successfully processed {len(successful_items)} items:\n{items_text}")

        self.worker.finished.emit()

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

        # collect all dropped items
        dropped_items = []
        vpk_paths = []

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
                vpk_paths.append(item_path)
            else:
                QMessageBox.warning(self, "Unsupported File Type",
                                    f"File type not supported: {path_obj.name}\n\n"
                                    f"Supported types: VPK files, folders, ZIP files")
                continue

        # normalize and deduplicate VPK paths
        dropped_items.extend(normalize_vpk_paths(vpk_paths))

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

import threading
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox
from operations.file_processors import check_game_type
from gui.interface import Interface


class InstallationManager(QObject):
    progress_update = pyqtSignal(int, str)
    operation_finished = pyqtSignal()
    operation_error = pyqtSignal(str)
    operation_success = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.interface = Interface()
        self.tf_path = ""
        self.processing = False

        # interface connection
        self.interface.progress_signal.connect(self.progress_update)
        self.interface.error_signal.connect(self.operation_error)
        self.interface.success_signal.connect(self.operation_success)
        self.interface.operation_finished.connect(self.operation_finished)

    def set_tf_path(self, path):
        self.tf_path = path

    def validate_tf_path(self):
        if not self.tf_path:
            return False, "Please select tf/ directory!"

        if not (self.tf_path.endswith("/tf") or self.tf_path.endswith("/tf/")):
            return False, "Please select tf/ directory!"

        if not Path(self.tf_path).exists():
            return False, "Selected TF2 directory does not exist!"

        return True, ""

    def install(self, selected_addons, mod_drop_zone=None, valve_rc_found=False):
        valid, message = self.validate_tf_path()
        if not valid:
            self.operation_error.emit(message)
            self.operation_finished.emit()
            return

        self.processing = True
        thread = threading.Thread(
            target=self.interface.install,
            args=(self.tf_path, selected_addons, mod_drop_zone, valve_rc_found)
        )
        thread.daemon = True
        thread.start()

    def restore(self):
        if not self.tf_path:
            self.operation_error.emit("Please select tf/ directory!")
            return False

        result = QMessageBox.question(
            None,
            "Confirm Uninstall",
            "This will revert all changes that have been made to TF2 by this app.\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result != QMessageBox.StandardButton.Yes:
            return False

        self.processing = True
        thread = threading.Thread(
            target=self.interface.restore_backup,
            args=(self.tf_path,)
        )
        thread.daemon = True
        thread.start()
        return True

    def is_modified(self):
        if not self.tf_path:
            return False

        gameinfo_path = Path(self.tf_path) / 'gameinfo.txt'
        return check_game_type(gameinfo_path) if gameinfo_path.exists() else False

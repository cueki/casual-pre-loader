import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from core.operations.file_processors import check_game_type
from gui.interface import Interface
from gui.settings_manager import validate_goldrush_directory, validate_tf_directory


class InstallationManager(QObject):
    progress_update = pyqtSignal(int, str)
    operation_finished = pyqtSignal()
    operation_error = pyqtSignal(str)
    operation_success = pyqtSignal(str)

    def __init__(self, settings_manager=None):
        super().__init__()
        self.interface = Interface(settings_manager)
        self.tf_path = ""
        self.processing = False
        self.settings_manager = settings_manager

        # interface connection
        self.interface.progress_signal.connect(self.progress_update)
        self.interface.error_signal.connect(self.operation_error)
        self.interface.success_signal.connect(self.operation_success)
        self.interface.operation_finished.connect(self.operation_finished)

    def set_tf_path(self, path):
        self.tf_path = path

    def install(self, selected_addons, mod_drop_zone=None, target_path=None):
        # use provided target_path or fall back to tf_path
        install_path = target_path if target_path else self.tf_path

        # use appropriate validation based on target
        if Path(install_path).name == "tf_goldrush":
            is_valid = validate_goldrush_directory(install_path)
        else:
            is_valid = validate_tf_directory(install_path)

        if not is_valid:
            self.operation_error.emit("Invalid target directory!")
            self.operation_finished.emit()
            return

        self.processing = True
        thread = threading.Thread(
            target=self.interface.install,
            args=(install_path, selected_addons, mod_drop_zone),
            daemon=True
        )
        thread.start()

    def restore(self, target_path=None):
        # use provided target_path or fall back to tf_path
        restore_path = target_path if target_path else self.tf_path

        if not restore_path:
            self.operation_error.emit("Please select a target directory!")
            return False

        # determine target name for message
        target_name = "Gold Rush" if Path(restore_path).name == "tf_goldrush" else "TF2"

        result = QMessageBox.question(
            None,
            "Confirm Uninstall",
            f"This will revert all changes that have been made to {target_name} by this app.\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result != QMessageBox.StandardButton.Yes:
            return False

        self.processing = True
        thread = threading.Thread(
            target=self.interface.restore_backup,
            args=(restore_path,),
            daemon=True
        )
        thread.start()
        return True

    def cancel_operation(self):
        if self.processing:
            self.interface.cancel_requested = True

    def is_modified(self, target_path=None):
        # use provided target_path or fall back to tf_path
        check_path = target_path if target_path else self.tf_path

        if not check_path:
            return False

        gameinfo_path = Path(check_path) / 'gameinfo.txt'
        return check_game_type(gameinfo_path) if gameinfo_path.exists() else False

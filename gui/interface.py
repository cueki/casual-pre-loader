import logging
import threading
from pathlib import Path
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from core.services.install import InstallService
from core.util.sourcemod import validate_goldrush_directory, validate_tf_directory

log = logging.getLogger()


class Interface(QObject):
    progress_update = pyqtSignal(int, str)
    operation_error = pyqtSignal(str)
    operation_success = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self, settings_manager=None):
        super().__init__()
        self.settings_manager = settings_manager
        self._service = InstallService()
        self.tf_path = ""
        self.processing = False

    @property
    def cancel_requested(self):
        return self._service.cancel_requested

    @cancel_requested.setter
    def cancel_requested(self, value):
        if value:
            self._service.request_cancel()
        else:
            self._service.cancel_requested = False

    def set_tf_path(self, path):
        self.tf_path = path

    def _on_progress(self, progress: int, message: str):
        self.progress_update.emit(progress, message)

    def _run_install(self, install_path, selected_addons, mod_drop_zone):
        try:
            disable_paint_colors = False
            show_console = True
            if self.settings_manager:
                disable_paint_colors = self.settings_manager.get_disable_paint_colors()
                show_console = self.settings_manager.get_show_console_on_startup()

            apply_particles = None
            if mod_drop_zone:
                apply_particles = mod_drop_zone.apply_particle_selections

            self._service.install(
                tf_path=install_path,
                selected_addons=selected_addons,
                on_progress=self._on_progress,
                apply_particle_selections=apply_particles,
                disable_paint_colors=disable_paint_colors,
                show_console_on_startup=show_console,
            )
            self.operation_success.emit("Mods installed successfully!")
            self._on_progress(0, "Installation complete")

        except Exception as e:
            was_cancelled = "cancelled by user" in str(e).lower()
            if was_cancelled:
                self._on_progress(0, "Cancelling installation, restoring files...")
            else:
                self._on_progress(0, "Installation failed, attempting cleanup...")

            try:
                self._service.uninstall(tf_path=install_path)
                if not was_cancelled:
                    self.operation_error.emit(f"Installation failed: {str(e)}\n\nFiles have been restored to default state.")
            except Exception as cleanup_error:
                self.operation_error.emit(
                    f"Installation failed and cleanup also failed.\n\n"
                    f"Original error: {str(e)}\n"
                    f"Cleanup error: {str(cleanup_error)}\n\n"
                    f"Please verify your game files through Steam:\n"
                    f"Library > Right-click Team Fortress 2 > Properties > Installed Files > Verify integrity of game files"
                )
        finally:
            self.processing = False
            self.operation_finished.emit()

    def install(self, selected_addons: List[str], mod_drop_zone=None, target_path=None):
        install_path = target_path if target_path else self.tf_path

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
            target=self._run_install,
            args=(install_path, selected_addons, mod_drop_zone),
            daemon=True
        )
        thread.start()

    def _run_uninstall(self, restore_path):
        try:
            self._service.uninstall(
                tf_path=restore_path,
                on_progress=self._on_progress,
            )
            self.operation_success.emit("Mods uninstalled successfully!")
        except Exception as e:
            self.operation_error.emit(f"An error occurred while uninstalling: {str(e)}")
        finally:
            self.processing = False
            self.operation_finished.emit()

    def uninstall(self, target_path=None):
        restore_path = target_path if target_path else self.tf_path

        if not restore_path:
            self.operation_error.emit("Please select a target directory!")
            return False

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
            target=self._run_uninstall,
            args=(restore_path,),
            daemon=True
        )
        thread.start()
        return True

    def cancel_operation(self):
        if self.processing:
            self.cancel_requested = True

    def is_modified(self, target_path=None):
        check_path = target_path if target_path else self.tf_path
        return self._service.is_modified(check_path)

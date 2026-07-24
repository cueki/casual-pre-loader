import logging
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from core.constants import Sourcemods
from core.services.install import InstallService
from core.util.sourcemod import validate_game_directory

log = logging.getLogger()


class InstallController(QObject):
    progress_update = pyqtSignal(int, str)
    operation_error = pyqtSignal(str)
    operation_success = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings
        self.service = InstallService()
        self.tf_path: Path | None = None
        self.processing = False

    @property
    def cancel_requested(self):
        return self.service.cancel_requested

    @cancel_requested.setter
    def cancel_requested(self, value):
        if value:
            self.service.request_cancel()
        else:
            self.service.cancel_requested = False

    def set_tf_path(self, path: Path) -> None:
        self.tf_path = path

    def _on_progress(self, progress: int, message: str):
        self.progress_update.emit(progress, message)

    def _run_install(self, install_path: Path, selected_addons, mod_drop_zone, sourcemod: Sourcemods = Sourcemods.DEFAULT):
        try:
            disable_paint_colors = False
            show_console = True
            fix_mdl_paths = True
            skip_quickprecache = False
            if self.settings:
                disable_paint_colors = self.settings.disable_paint_colors
                show_console = self.settings.show_console_on_startup
                fix_mdl_paths = self.settings.fix_mdl_paths
                skip_quickprecache = self.settings.skip_quickprecache

            apply_particles = None
            if mod_drop_zone:
                apply_particles = mod_drop_zone.apply_particle_selections

            self.service.install(
                tf_path=install_path,
                selected_addons=selected_addons,
                on_progress=self._on_progress,
                apply_particle_selections=apply_particles,
                disable_paint_colors=disable_paint_colors,
                show_console_on_startup=show_console,
                fix_mdl_paths=fix_mdl_paths,
                skip_quickprecache=skip_quickprecache,
                sourcemod=sourcemod,
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
                self.service.uninstall(tf_path=install_path, sourcemod=sourcemod)
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

    def install(self, selected_addons: list[str], mod_drop_zone=None, target_path: Path | None = None, sourcemod: Sourcemods = Sourcemods.DEFAULT):
        install_path = target_path if target_path else self.tf_path

        if not validate_game_directory(install_path):
            self.operation_error.emit("Invalid target directory!")
            self.operation_finished.emit()
            return

        self.processing = True
        thread = threading.Thread(
            target=self._run_install,
            args=(install_path, selected_addons, mod_drop_zone, sourcemod),
            daemon=True
        )
        thread.start()

    def _run_uninstall(self, restore_path: Path, sourcemod: Sourcemods = Sourcemods.DEFAULT):
        try:
            self.service.uninstall(
                tf_path=restore_path,
                on_progress=self._on_progress,
                sourcemod=sourcemod,
            )
            self.operation_success.emit("Mods uninstalled successfully!")
        except Exception as e:
            self.operation_error.emit(f"An error occurred while uninstalling: {str(e)}")
        finally:
            self.processing = False
            self.operation_finished.emit()

    def uninstall(self, target_path: Path | None = None, sourcemod: Sourcemods = Sourcemods.DEFAULT):
        """Start uninstall operation. Caller should confirm with user first."""
        restore_path = target_path if target_path else self.tf_path

        if not restore_path:
            self.operation_error.emit("Please select a target directory!")
            return False

        self.processing = True
        thread = threading.Thread(
            target=self._run_uninstall,
            args=(restore_path, sourcemod),
            daemon=True
        )
        thread.start()
        return True

    def cancel_operation(self):
        if self.processing:
            self.cancel_requested = True

    def is_modified(self, target_path: Path | None = None):
        check_path = target_path if target_path else self.tf_path
        return self.service.is_modified(check_path)

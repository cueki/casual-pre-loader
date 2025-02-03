import shutil
import zipfile
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
import vpk
import random
from core.constants import CUSTOM_VPK_NAMES
from core.folder_setup import folder_setup
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor
from tools.backup_manager import BackupManager
from operations.game_type import replace_game_type


class ParticleOperations(QObject):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def update_progress(self, progress: int, message: str):
        self.progress_signal.emit(progress, message)

    def install(self, tf_path: str, selected_addons: List[str]):
        try:
            folder_setup.create_required_folders()
            backup_manager = BackupManager(tf_path)

            if not backup_manager.create_initial_backup():
                self.error_signal.emit("Failed to create/verify backup")
                return

            if not backup_manager.prepare_working_copy():
                self.error_signal.emit("Failed to create working copy")
                return

            working_vpk_path = backup_manager.get_working_vpk_path()
            vpk_handler = VPKHandler(str(working_vpk_path))
            file_handler = FileHandler(vpk_handler)

            for addon_name in selected_addons:
                addon_path = Path("addons") / f"{addon_name}.zip"
                if addon_path.exists():
                    with zipfile.ZipFile(addon_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            zip_ref.extract(file, folder_setup.mods_everything_else_dir)

            self.update_progress(25, "Patching in...")
            particle_files = folder_setup.mods_particle_dir.iterdir()
            for pcf_file in particle_files:
                base_name = pcf_file.name
                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(pcf_file)),
                    create_backup=False
                )

            # deploy mods
            self.update_progress(75, "Deploying mods...")
            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to deploy to game directory")
                return

            # handle custom folder
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)
            replace_game_type(Path(tf_path) / 'gameinfo.txt', uninstall=False)

            for custom_vpk in CUSTOM_VPK_NAMES:
                vpk_path = custom_dir / custom_vpk
                cache_path = custom_dir / (custom_vpk + ".sound.cache")
                if vpk_path.exists():
                    vpk_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()

            # create new VPK for custom content
            custom_content_dir = folder_setup.mods_everything_else_dir
            if custom_content_dir.exists() and any(custom_content_dir.iterdir()):
                new_pak = vpk.new(str(custom_content_dir))
                new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

            self.update_progress(100, "Installation complete")
            self.success_signal.emit("Mods installed successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred: {str(e)}")
            folder_setup.cleanup_temp_folders()
        finally:
            folder_setup.cleanup_temp_folders()
            self.operation_finished.emit()

    def restore_backup(self, tf_path: str):
        try:
            folder_setup.cleanup_temp_folders()
            folder_setup.create_required_folders()
            backup_manager = BackupManager(tf_path)

            if not backup_manager.prepare_working_copy():
                self.error_signal.emit("Failed to prepare working copy")
                return

            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to restore backup")
                return

            replace_game_type(Path(tf_path) / 'gameinfo.txt', uninstall=True)
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)

            for custom_vpk in CUSTOM_VPK_NAMES:
                vpk_path = custom_dir / custom_vpk
                cache_path = custom_dir / (custom_vpk + ".sound.cache")
                if vpk_path.exists():
                    vpk_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()

            self.success_signal.emit("Backup restored successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred while restoring backup: {str(e)}")
            folder_setup.cleanup_temp_folders()
        finally:
            folder_setup.cleanup_temp_folders()
            self.operation_finished.emit()
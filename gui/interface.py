import shutil
import zipfile
from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
import vpk
import random
from core.constants import CUSTOM_VPK_NAMES, DX8_LIST
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler
from core.handlers.pcf_handler import check_parents, update_materials
from core.handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, game_type, get_from_vpk
from operations.pcf_rebuild import load_particle_system_map, extract_elements
from core.parsers.pcf_file import PCFFile
from backup.backup_manager import BackupManager, get_working_vpk_path, prepare_working_copy


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
            backup_manager = BackupManager(tf_path)
            working_vpk_path = get_working_vpk_path()
            vpk_handler = VPKHandler(str(working_vpk_path))
            file_handler = FileHandler(vpk_handler)
            folder_setup.initialize_pcf()

            for addon_name in selected_addons:
                addon_path = Path("addons") / f"{addon_name}.zip"
                if addon_path.exists():
                    with zipfile.ZipFile(addon_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            zip_ref.extract(file, folder_setup.mods_everything_else_dir)

            # these 5 particle files contain duplicate elements that are found elsewhere, this is an oversight by valve.
            # what im doing is simply fixing this oversight using context from the elements themselves
            # they now should only appear once in the game, and in the correct file :)
            # previous code dictates that if any custom particle effect is chosen, it is already fixed, this is to fix if they are not chosen
            duplicate_effects = [
                "halloween.pcf",
                "scary_ghost.pcf",
                "dirty_explode.pcf",
                "bigboom.pcf",
                "item_fx.pcf"
            ]

            for duplicate_effect in duplicate_effects:
                target_path = folder_setup.mods_particle_dir / duplicate_effect
                if not target_path.exists():
                    # copy from game_files if not in
                    source_path = folder_setup.game_files_dir / duplicate_effect
                    if source_path.exists():
                        extract_elements(PCFFile(source_path).decode(),
                                         load_particle_system_map('particle_system_map.json')
                                         [f'particles/{target_path.name}']).encode(target_path)

            if (folder_setup.mods_particle_dir / "blood_trail.pcf").exists():
                # hacky fix for blood_trail being so small
                shutil.move((folder_setup.mods_particle_dir / "blood_trail.pcf"), (folder_setup.mods_particle_dir / "npc_fx.pcf"))

            self.update_progress(25, "Patching in...")
            particle_files = folder_setup.mods_particle_dir.iterdir()
            for pcf_file in particle_files:
                base_name = pcf_file.name
                if (base_name != folder_setup.base_default_pcf.input_file.name and
                        check_parents(PCFFile(pcf_file).decode(), folder_setup.base_default_parents)):
                    continue
                if base_name == folder_setup.base_default_pcf.input_file.name:
                    update_materials(folder_setup.base_default_pcf, PCFFile(pcf_file).decode()).encode(pcf_file)
                if pcf_file.stem in DX8_LIST:
                    # dx80 first
                    dx_80_ver = Path(pcf_file.stem + "_dx80.pcf")
                    shutil.copy2(pcf_file, folder_setup.mods_particle_dir / dx_80_ver)
                    file_handler.process_file(
                        dx_80_ver.name,
                        pcf_mod_processor(str(folder_setup.mods_particle_dir / dx_80_ver)),
                        create_backup=False
                    )
                # now the rest
                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(pcf_file)),
                    create_backup=False
                )

            # handle custom folder
            self.update_progress(75, "Deploying mods...")
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)
            game_type(Path(tf_path) / 'gameinfo.txt', uninstall=False)

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

            # deploy particles
            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to deploy to game directory")
                return

            for file in custom_dir.glob("*.vpk"):
                get_from_vpk(Path(file))

            self.update_progress(100, "Installation complete")
            self.success_signal.emit("Mods installed successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred: {str(e)}")
        finally:
            prepare_working_copy()
            self.operation_finished.emit()

    def restore_backup(self, tf_path: str):
        try:
            prepare_working_copy()
            backup_manager = BackupManager(tf_path)

            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to restore backup")
                return

            game_type(Path(tf_path) / 'gameinfo.txt', uninstall=True)
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
        finally:
            folder_setup.cleanup_temp_folders()
            prepare_working_copy()
            self.operation_finished.emit()
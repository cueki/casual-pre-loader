import shutil
import zipfile
from pathlib import Path
from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
from core.constants import CUSTOM_VPK_NAMES, DX8_LIST, CUSTOM_VPK_NAME, CUSTOM_VPK_SPLIT_PATTERN
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler, copy_config_files
from core.handlers.pcf_handler import check_parents, update_materials
from core.parsers.vpk_file import VPKFile
from core.parsers.pcf_file import PCFFile
from operations.pcf_rebuild import load_particle_system_map, extract_elements
from operations.file_processors import pcf_mod_processor, game_type, get_from_custom_dir
from backup.backup_manager import BackupManager, get_working_vpk_path, prepare_working_copy
from quickprecache.precache_list import make_precache_list
from quickprecache.quick_precache import QuickPrecache


class Interface(QObject):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def update_progress(self, progress: int, message: str):
        self.progress_signal.emit(progress, message)

    def install(self, tf_path: str, selected_addons: List[str], prop_filter: bool=False, mod_drop_zone=None):
        try:
            backup_manager = BackupManager(tf_path)
            working_vpk_path = get_working_vpk_path()
            vpk_file = VPKFile(str(working_vpk_path))
            vpk_file.parse_directory()
            file_handler = FileHandler(str(working_vpk_path))
            folder_setup.initialize_pcf()

            for addon_path in selected_addons:
                addon_zip = Path("addons") / f"{addon_path}.zip"
                if addon_zip.exists():
                    with zipfile.ZipFile(addon_zip, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if Path(file).name != 'mod.json':
                                zip_ref.extract(file, folder_setup.mods_everything_else_dir)

            if mod_drop_zone:
                mod_drop_zone.apply_particle_selections()

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

            # create new VPK for custom content & config
            custom_content_dir = folder_setup.mods_everything_else_dir
            copy_config_files(custom_content_dir, prop_filter)

            for split_file in custom_dir.glob(f"{CUSTOM_VPK_SPLIT_PATTERN}*.vpk"):
                split_file.unlink()
                # Also remove any cache files
                cache_file = custom_dir / (split_file.name + ".sound.cache")
                if cache_file.exists():
                    cache_file.unlink()

            if custom_content_dir.exists() and any(custom_content_dir.iterdir()):
                # 2GB split size
                split_size = 2 ** 31
                vpk_base_path = custom_dir / CUSTOM_VPK_NAME.replace('.vpk', '')

                if not VPKFile.create(str(custom_content_dir), str(vpk_base_path), split_size):
                    self.error_signal.emit("Failed to create custom VPK")
                    return

            # deploy particles
            if not backup_manager.deploy_to_game():
                self.error_signal.emit("Failed to deploy to game directory")
                return

            # flush quick precache every install
            QuickPrecache(str(Path(tf_path).parents[0]), debug=False, prop_filter=prop_filter).run(flush=True)
            quick_precache_path = custom_dir / "_QuickPrecache.vpk"
            if quick_precache_path.exists():
                quick_precache_path.unlink()

            # legacy name
            old_quick_precache_path = custom_dir / "QuickPrecache.vpk"
            if old_quick_precache_path.exists():
                old_quick_precache_path.unlink()

            # run quick precache if needed (either by having props or by using the fast load)
            precache_prop_set = make_precache_list(str(Path(tf_path).parents[0]), prop_filter)
            if precache_prop_set:
                precache = QuickPrecache(str(Path(tf_path).parents[0]), debug=False, prop_filter=prop_filter)
                precache.run(auto=True)
                shutil.copy2("quickprecache/_QuickPrecache.vpk", custom_dir)

            get_from_custom_dir(custom_dir)

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

            # flush quick precache
            QuickPrecache(str(Path(tf_path).parents[0]), debug=False, prop_filter=False).run(flush=True)
            quick_precache_path = custom_dir / "_QuickPrecache.vpk"
            if quick_precache_path.exists():
                quick_precache_path.unlink()

            quick_precache_cache = custom_dir / "_quickprecache.vpk.sound.cache"
            if quick_precache_cache.exists():
                quick_precache_cache.unlink()

            # legacy name
            old_quick_precache_path = custom_dir / "QuickPrecache.vpk"
            if old_quick_precache_path.exists():
                old_quick_precache_path.unlink()

            for custom_vpk in CUSTOM_VPK_NAMES:
                vpk_path = custom_dir / custom_vpk
                cache_path = custom_dir / (custom_vpk + ".sound.cache")
                if vpk_path.exists():
                    vpk_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()

            for split_file in custom_dir.glob(f"{CUSTOM_VPK_SPLIT_PATTERN}*.vpk"):
                split_file.unlink()
                cache_file = custom_dir / (split_file.name + ".sound.cache")
                if cache_file.exists():
                    cache_file.unlink()

            self.success_signal.emit("Backup restored successfully!")

        except Exception as e:
            self.error_signal.emit(f"An error occurred while restoring backup: {str(e)}")
        finally:
            folder_setup.cleanup_temp_folders()
            prepare_working_copy()
            self.operation_finished.emit()
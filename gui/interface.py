import shutil
from pathlib import Path
from typing import List
from PyQt6.QtCore import QObject, pyqtSignal
from core.constants import CUSTOM_VPK_NAMES, DX8_LIST, CUSTOM_VPK_NAME, CUSTOM_VPK_SPLIT_PATTERN
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler, copy_config_files
from core.handlers.pcf_handler import check_parents, update_materials, restore_particle_files
from core.handlers.skybox_handler import handle_skybox_mods, restore_skybox_files
from core.parsers.vpk_file import VPKFile
from core.parsers.pcf_file import PCFFile
from operations.pcf_rebuild import load_particle_system_map, extract_elements
from operations.file_processors import pcf_mod_processor, game_type, get_from_custom_dir
from operations.vgui_preload import patch_mainmenuoverride
from backup.backup_manager import prepare_working_copy
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

    def install(self, tf_path: str, selected_addons: List[str], mod_drop_zone=None, valve_rc_found=False):
        try:
            working_vpk_path = Path(tf_path) / "tf2_misc_dir.vpk"
            vpk_file = VPKFile(str(working_vpk_path))
            vpk_file.parse_directory()
            file_handler = FileHandler(str(working_vpk_path))
            folder_setup.initialize_pcf()
            self.update_progress(0, "Installing addons...")

            total_files = 0
            files_to_copy = []

            for addon_path in selected_addons:
                addon_dir = folder_setup.addons_dir / addon_path
                if addon_dir.exists() and addon_dir.is_dir():
                    for src_path in addon_dir.glob('**/*'):
                        if src_path.is_file() and src_path.name != 'mod.json':
                            total_files += 1
                            files_to_copy.append((src_path, addon_dir))

            # progress bar
            progress_range = 40
            completed_files = 0
            self.update_progress(10, f"Installing addons... (0/{total_files} files)")

            for src_path, addon_dir in files_to_copy:
                # relative path from addon directory
                rel_path = src_path.relative_to(addon_dir)
                dest_path = folder_setup.temp_mods_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)

                # progress bar update
                completed_files += 1
                current_progress = 10 + int((completed_files / total_files) * progress_range)
                self.update_progress(current_progress, f"Installing addons... ({completed_files}/{total_files} files)")

            # remove any skybox mods if present then patch new ones in if selected
            restore_skybox_files(tf_path)
            handle_skybox_mods(folder_setup.temp_mods_dir, tf_path)

            # clear the in-game particle files
            restore_particle_files(tf_path)

            if mod_drop_zone:
                mod_drop_zone.apply_particle_selections()

            # these 4 particle files contain duplicate elements that are found elsewhere, this is an oversight by valve.
            # what im doing is simply fixing this oversight using context from the elements themselves
            # they now should only appear once in the game, and in the correct file :)
            # previous code dictates that if any custom particle effect is chosen, it is already fixed, this is to fix if they are not chosen
            duplicate_effects = [
                "item_fx.pcf",
                "halloween.pcf",
                "bigboom.pcf",
                "dirty_explode.pcf",
            ]
            for duplicate_effect in duplicate_effects:
                target_path = folder_setup.temp_mods_dir / duplicate_effect
                if not target_path.exists():
                    # copy from game_files if not in
                    source_path = folder_setup.temp_game_files_dir / duplicate_effect
                    if source_path.exists():
                        extract_elements(PCFFile(source_path).decode(),
                                         load_particle_system_map('particle_system_map.json')
                                         [f'particles/{target_path.name}']).encode(target_path)

            if (folder_setup.temp_mods_dir / "blood_trail.pcf").exists():
                # hacky fix for blood_trail being so small
                shutil.move((folder_setup.temp_mods_dir / "blood_trail.pcf"),
                            (folder_setup.temp_mods_dir / "npc_fx.pcf"))

            # more progress bar math yippee
            particle_files = list(folder_setup.temp_mods_dir.glob("*.pcf"))
            dx8_files = sum(1 for pcf_file in particle_files if pcf_file.stem in DX8_LIST)
            total_files = len(particle_files) + dx8_files
            start_progress = 50
            progress_range = 30
            completed_files = 0
            self.update_progress(start_progress, f"Processing particle files... (0/{total_files})")

            particle_files = folder_setup.temp_mods_dir.glob("*.pcf")
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
                    shutil.copy2(pcf_file, folder_setup.temp_mods_dir / dx_80_ver)
                    file_handler.process_file(
                        dx_80_ver.name,
                        pcf_mod_processor(str(folder_setup.temp_mods_dir / dx_80_ver)),
                        create_backup=False
                    )
                    # get them out of temp mods/ since they are patched directly into game vpk
                    (folder_setup.temp_mods_dir / dx_80_ver).unlink()
                    # update progress bar
                    completed_files += 1
                    current_progress = start_progress + int((completed_files / total_files) * progress_range)
                    self.update_progress(current_progress, f"Processing particle files... ({completed_files}/{total_files})")
                # now the rest
                file_handler.process_file(
                    base_name,
                    pcf_mod_processor(str(pcf_file)),
                    create_backup=False
                )
                # get them out of temp mods/ since they are patched directly into game vpk
                pcf_file.unlink()
                # update progress bar
                completed_files += 1
                current_progress = start_progress + int((completed_files / total_files) * progress_range)
                self.update_progress(current_progress,f"Processing particle files... ({completed_files}/{total_files})")

            # handle custom folder
            self.update_progress(80, "Making custom VPK")
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
            custom_content_dir = folder_setup.temp_mods_dir
            copy_config_files(custom_content_dir, valve_rc_found)
            patch_mainmenuoverride(tf_path)

            for split_file in custom_dir.glob(f"{CUSTOM_VPK_SPLIT_PATTERN}*.vpk"):
                split_file.unlink()
                # also remove any cache files
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

            # flush quick precache every install
            QuickPrecache(str(Path(tf_path).parents[0]), debug=False).run(flush=True)
            quick_precache_path = custom_dir / "_QuickPrecache.vpk"
            if quick_precache_path.exists():
                quick_precache_path.unlink()

            # legacy name
            old_quick_precache_path = custom_dir / "QuickPrecache.vpk"
            if old_quick_precache_path.exists():
                old_quick_precache_path.unlink()

            # run quick precache if needed (by having props)
            precache_prop_set = make_precache_list(str(Path(tf_path).parents[0]))
            if precache_prop_set:
                precache = QuickPrecache(str(Path(tf_path).parents[0]), debug=False)
                precache.run(auto=True)
                shutil.copy2(folder_setup.install_dir / 'quickprecache/_QuickPrecache.vpk', custom_dir)
                self.update_progress(90, f"QuickPrecaching some models...")

            get_from_custom_dir(custom_dir)

            self.update_progress(100, "Installation complete")
            self.success_signal.emit("Mods installed successfully!")
            # reset progress bar
            self.update_progress(0, "Installation complete")

        except Exception as e:
            self.error_signal.emit(f"An error occurred: {str(e)}")
        finally:
            prepare_working_copy()
            self.operation_finished.emit()

    def restore_backup(self, tf_path: str):
        try:
            prepare_working_copy()
            game_type(Path(tf_path) / 'gameinfo.txt', uninstall=True)
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)

            # skybox unpatch
            restore_skybox_files(tf_path)

            # restore particles
            restore_particle_files(tf_path)

            # flush quick precache
            QuickPrecache(str(Path(tf_path).parents[0]), debug=False).run(flush=True)
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

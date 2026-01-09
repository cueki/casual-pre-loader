import json
import logging
import shutil
from pathlib import Path
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal
from valve_parsers import PCFFile, VPKFile

from core.backup_manager import prepare_working_copy
from core.constants import (
    BACKUP_MAINMENU_FOLDER,
    CUSTOM_VPK_NAME,
    CUSTOM_VPK_NAMES,
    CUSTOM_VPK_SPLIT_PATTERN,
    DX8_LIST,
)
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler, copy_config_files, generate_config
from core.handlers.paint_handler import disable_paints, enable_paints
from core.handlers.pcf_handler import (
    check_parents,
    restore_particle_files,
    update_materials,
)
from core.handlers.skybox_handler import handle_skybox_mods, restore_skybox_files
from core.handlers.sound_handler import SoundHandler
from core.operations.file_processors import (
    game_type,
    get_from_custom_dir,
    initialize_pcf,
)
from core.operations.for_the_love_of_god_add_vmts_to_your_mods import (
    generate_missing_vmt_files,
)
from core.operations.pcf_compress import remove_duplicate_elements
from core.operations.pcf_rebuild import extract_elements, load_particle_system_map
from core.operations.vgui_preload import patch_mainmenuoverride
from core.quickprecache.precache_list import make_precache_list
from core.quickprecache.quick_precache import QuickPrecache
from core.util.vpk import get_vpk_name

log = logging.getLogger()


class Interface(QObject):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)
    operation_finished = pyqtSignal()

    def __init__(self, settings_manager=None):
        super().__init__()
        self.sound_handler = SoundHandler()
        self.cancel_requested = False
        self.settings_manager = settings_manager

    def update_progress(self, progress: int, message: str):
        self.progress_signal.emit(progress, message)

    @staticmethod
    def cleanup_huds(custom_dir: Path) -> None:
        # clean up old HUDs that we installed (they have mod.json with preloader_installed flag)
        items_to_delete = []
        for item in custom_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                mod_json = item / 'mod.json'
                if mod_json.exists():
                    try:
                        with open(mod_json, 'r') as f:
                            mod_info = json.load(f)
                            if mod_info.get('type', '').lower() == 'hud' and mod_info.get('preloader_installed', False):
                                items_to_delete.append(item)
                    except json.JSONDecodeError:
                        log.warning(f"Invalid JSON in {mod_json}", exc_info=True)

        # delete after closing all file handles
        for item in items_to_delete:
            shutil.rmtree(item)

    def install(self, tf_path: str, selected_addons: List[str], mod_drop_zone=None):
        self.cancel_requested = False
        try:
            working_vpk_path = Path(tf_path) / get_vpk_name(tf_path)
            file_handler = FileHandler(str(working_vpk_path))
            base_default_pcf, base_default_parents  = initialize_pcf(folder_setup.temp_to_be_referenced_dir)
            self.update_progress(0, "Installing addons...")

            total_files = 0
            files_to_copy = []
            hud_addons = {}

            for addon_path in selected_addons:
                addon_dir = folder_setup.addons_dir / addon_path
                if addon_dir.exists() and addon_dir.is_dir():
                    mod_json_path = addon_dir / 'mod.json'
                    if mod_json_path.exists():
                        try:
                            with open(mod_json_path, 'r') as f:
                                mod_info = json.load(f)
                                if mod_info.get('type', '').lower() == 'hud':
                                    addon_path = addon_path.lower()

                                    if hud_addons.get(addon_path) is None:
                                        hud_addons[addon_path] = addon_dir
                                        continue  # skip hud files for now
                                    else:
                                        raise Exception(f"There are 2 mods that have directory names which resolve to the same case-insensitive name:\n'{hud_addons[addon_path].name}'\n'{addon_dir.name}'")
                        except json.JSONDecodeError:
                            log.warning(f"Invalid JSON in {mod_json_path}", exc_info=True)

                    for src_path in addon_dir.glob('**/*'):
                        if src_path.is_file() and src_path.name != 'mod.json' and src_path.name != 'sound.cache':
                            # skip sound script files from addons (we'll use our versions)
                            rel_path = src_path.relative_to(addon_dir)
                            if (rel_path.parts[0] == 'scripts' and
                                len(rel_path.parts) >= 2 and
                                'sound' in src_path.name.lower() and
                                src_path.suffix == '.txt'):
                                continue
                            total_files += 1
                            files_to_copy.append((src_path, addon_dir))

            if self.cancel_requested:
                raise Exception("Installation cancelled by user")

            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)

            tf_path_obj = Path(tf_path)
            is_tf2 = tf_path_obj.name == "tf"

            # HUDs are TF2-specific
            if is_tf2:
                self.cleanup_huds(custom_dir)

                for addon_name, addon_dir in hud_addons.items():
                    hud_dest = custom_dir / addon_name
                    if hud_dest.exists():
                        log.info(f'{hud_dest} already exists, skipping as to not overwrite possible user-modified files')
                        continue
                    shutil.copytree(addon_dir, hud_dest)

                    # mark the HUD as installed by preloader
                    hud_mod_json = hud_dest / 'mod.json'
                    if hud_mod_json.exists():
                        try:
                            with open(hud_mod_json, 'r') as f:
                                mod_info = json.load(f)
                            mod_info['preloader_installed'] = True
                            with open(hud_mod_json, 'w') as f:
                                json.dump(mod_info, f, indent=2)
                        except json.JSONDecodeError:
                            log.warning(f"Invalid JSON in {hud_mod_json}, skipping preloader_installed flag", exc_info=True)

            if self.cancel_requested:
                raise Exception("Installation cancelled by user")
            if is_tf2:
                restore_skybox_files(tf_path)
                restore_particle_files(tf_path)
                enable_paints(tf_path)

            if self.cancel_requested:
                raise Exception("Installation cancelled by user")

            if mod_drop_zone:
                mod_drop_zone.apply_particle_selections()

            if files_to_copy:  # process addon files if we have them
                progress_range = 25
                completed_files = 0
                self.update_progress(10, f"Installing addons... (0/{total_files} files)")

                for src_path, addon_dir in files_to_copy:
                    if self.cancel_requested:
                        raise Exception("Installation cancelled by user")

                    rel_path = src_path.relative_to(addon_dir)
                    # route files to appropriate temp directory
                    # PCF files go to to_be_patched, everything else goes to to_be_vpk
                    if src_path.suffix.lower() == '.pcf':
                        dest_path = folder_setup.temp_to_be_patched_dir / rel_path
                    else:
                        dest_path = folder_setup.temp_to_be_vpk_dir / rel_path

                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)

                    completed_files += 1
                    current_progress = 10 + int((completed_files / total_files) * progress_range)
                    self.update_progress(current_progress, f"Installing addons... ({completed_files}/{total_files} files)")

                # process sound mods and copy needed script files from backup
                if is_tf2:
                    self.update_progress(35, "Processing sound mods...")
                    backup_scripts_dir = folder_setup.backup_dir / 'scripts'

                    # collect VPK paths (vo and misc) for sound processing
                    vpk_paths = []
                    misc_vpk = tf_path_obj / "tf2_sound_misc_dir.vpk"
                    if misc_vpk.exists():
                        vpk_paths.append(misc_vpk)
                    vo_vpks = list(tf_path_obj.glob("tf2_sound_vo_*_dir.vpk"))
                    vpk_paths.extend(vo_vpks)

                    sound_result = self.sound_handler.process_temp_sound_mods(
                        folder_setup.temp_to_be_vpk_dir,
                        backup_scripts_dir,
                        vpk_paths
                    )
                    if sound_result:
                        self.update_progress(50, sound_result['message'])

                if self.cancel_requested:
                    raise Exception("Installation cancelled by user")

                # patch skybox mods into VPK
                if is_tf2:
                    handle_skybox_mods(folder_setup.temp_to_be_vpk_dir, tf_path)

                # handle paint removal if enabled
                if is_tf2 and self.settings_manager and self.settings_manager.get_disable_paint_colors():
                    self.update_progress(52, "Disabling paint colors...")
                    disable_paints(tf_path)

            if is_tf2:
                # TF2: process and patch particles into main VPK (sv_pure enabled)
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
                    target_path = folder_setup.temp_to_be_patched_dir / duplicate_effect
                    if not target_path.exists():
                        # copy from game_files if not in
                        source_path = folder_setup.temp_to_be_referenced_dir / duplicate_effect
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        if source_path.exists():
                            extract_elements(PCFFile(source_path).decode(),
                                             load_particle_system_map(folder_setup.data_dir / 'particle_system_map.json')
                                             [f'particles/{target_path.name}']).encode(target_path)

                if (folder_setup.temp_to_be_patched_dir / "blood_trail.pcf").exists():
                    # hacky fix for blood_trail being so small
                    shutil.move((folder_setup.temp_to_be_patched_dir / "blood_trail.pcf"),
                                (folder_setup.temp_to_be_patched_dir / "npc_fx.pcf"))

                # more progress bar math yippee
                particle_files = list(folder_setup.temp_to_be_patched_dir.glob("*.pcf"))
                dx8_files = sum(1 for pcf_file in particle_files if pcf_file.stem in DX8_LIST)
                total_files = len(particle_files) + dx8_files
                start_progress = 50
                progress_range = 30
                completed_files = 0
                self.update_progress(start_progress, f"Processing particle files... (0/{total_files})")

                for pcf_file in particle_files:
                    if self.cancel_requested:
                        raise Exception("Installation cancelled by user")

                    base_name = pcf_file.name

                    mod_pcf = PCFFile(pcf_file).decode()
                    if base_name != base_default_pcf.input_file.name and check_parents(mod_pcf, base_default_parents):
                        continue

                    if base_name == base_default_pcf.input_file.name:
                        mod_pcf = update_materials(base_default_pcf, mod_pcf)

                    # process the mod PCF
                    processed_pcf = remove_duplicate_elements(mod_pcf)

                    if pcf_file.stem in DX8_LIST:  # dx80 first
                        dx_80_name = pcf_file.stem + "_dx80.pcf"
                        file_handler.process_file(dx_80_name, processed_pcf)

                        # update progress bar
                        completed_files += 1
                        current_progress = start_progress + int((completed_files / total_files) * progress_range)
                        self.update_progress(current_progress, f"Processing particle files... ({completed_files}/{total_files})")

                    file_handler.process_file(base_name, processed_pcf)
                    pcf_file.unlink()  # delete temp file

                    # update progress bar
                    completed_files += 1
                    current_progress = start_progress + int((completed_files / total_files) * progress_range)
                    self.update_progress(current_progress, f"Processing particle files... ({completed_files}/{total_files})")
            else:
                # other sourcemods will just copy particles to custom VPK directory
                particle_files = list(folder_setup.temp_to_be_patched_dir.glob("*.pcf"))
                if particle_files:
                    particles_dir = folder_setup.temp_to_be_vpk_dir / 'particles'
                    particles_dir.mkdir(parents=True, exist_ok=True)

                    total_files = len(particle_files)
                    start_progress = 50
                    progress_range = 30
                    self.update_progress(start_progress, f"Copying particle files... (0/{total_files})")

                    for i, pcf_file in enumerate(particle_files):
                        if self.cancel_requested:
                            raise Exception("Installation cancelled by user")

                        shutil.move(pcf_file, particles_dir / pcf_file.name)

                        current_progress = start_progress + int(((i + 1) / total_files) * progress_range)
                        self.update_progress(current_progress, f"Copying particle files... ({i + 1}/{total_files})")

            if self.cancel_requested:
                raise Exception("Installation cancelled by user")

            # handle custom folder
            self.update_progress(80, "Making custom VPK")

            # mark as installed
            game_type(Path(tf_path) / 'gameinfo.txt', uninstall=False)

            if is_tf2:
                # cleanup old backup mainmenu folder
                backup_mainmenu_folder = custom_dir / BACKUP_MAINMENU_FOLDER
                if backup_mainmenu_folder.exists():
                    shutil.rmtree(backup_mainmenu_folder)

            for custom_vpk in CUSTOM_VPK_NAMES:
                vpk_path = custom_dir / custom_vpk
                cache_path = custom_dir / (custom_vpk + ".sound.cache")
                if vpk_path.exists():
                    vpk_path.unlink()
                if cache_path.exists():
                    cache_path.unlink()

            # create new VPK for custom content & config
            custom_content_dir = folder_setup.temp_to_be_vpk_dir
            copy_config_files(custom_content_dir)

            if is_tf2:
                # hud preload
                patch_mainmenuoverride(tf_path)
                # make vmts
                generate_missing_vmt_files(custom_content_dir, tf_path)

            for split_file in custom_dir.glob(f"{CUSTOM_VPK_SPLIT_PATTERN}*.vpk"):
                split_file.unlink()
                # also remove preloader cache files
                cache_file = custom_dir / (split_file.name + ".sound.cache")
                if cache_file.exists():
                    cache_file.unlink()

            if custom_content_dir.exists() and any(custom_content_dir.iterdir()):
                # 2GB split size
                split_size = 2 ** 31
                vpk_base_path = custom_dir / CUSTOM_VPK_NAME.replace('.vpk', '')

                custom_content_dir.mkdir(parents=True, exist_ok=True) # INFO: technically not necessary, but VPKFile does not check if `source_dir` exists
                if not VPKFile.create(str(custom_content_dir), str(vpk_base_path), split_size):
                    raise Exception("Failed to create custom VPK")

            if self.cancel_requested:
                raise Exception("Installation cancelled by user")

            if is_tf2:
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
                self.update_progress(85, "Scanning for models to precache...")
                precache_prop_set = make_precache_list(str(Path(tf_path).parents[0]))
                if precache_prop_set:
                    precache = QuickPrecache(
                        str(Path(tf_path).parents[0]),
                        debug=False,
                        progress_callback=self.update_progress
                    )
                    precache.run(auto=True)
                    shutil.copy2(folder_setup.install_dir / 'core/quickprecache/_QuickPrecache.vpk', custom_dir)

                if self.cancel_requested:
                    raise Exception("Installation cancelled by user")

                # patch config.cfg based on what's actually in custom/
                self.update_progress(95, "Configuring...")

                # check for mastercomfig
                has_mastercomfig = False
                for item in custom_dir.iterdir():
                    if item.is_file() and item.suffix == '.vpk' and item.name.startswith('mastercomfig'):
                        has_mastercomfig = True
                        break

                # check for quickprecache
                needs_quickprecache = (custom_dir / "_QuickPrecache.vpk").exists()

                # get console setting from settings_manager
                show_console = True  # default
                if self.settings_manager:
                    show_console = self.settings_manager.get_show_console_on_startup()

                # generate appropriate config content
                config_content = generate_config(has_mastercomfig, needs_quickprecache, show_console)

                # patch generated config
                custom_vpk_path = custom_dir / CUSTOM_VPK_NAME.replace('.vpk', '_dir.vpk')
                if custom_vpk_path.exists():
                    vpk_handler = FileHandler(str(custom_vpk_path))
                    vpk_handler.process_file('cfg/w/config.cfg', config_content.encode('utf-8'))

            self.update_progress(97, "Finalizing...")
            get_from_custom_dir(custom_dir)

            self.update_progress(100, "Installation complete")
            self.success_signal.emit("Mods installed successfully!")
            self.update_progress(0, "Installation complete")
        except Exception as e:
            was_cancelled = "cancelled by user" in str(e).lower()
            if not was_cancelled:
                self.error_signal.emit(f"Installation failed: {str(e)}")
            # attempt clean up by restoring backup
            try:
                if was_cancelled:
                    self.update_progress(0, "Cancelling installation, restoring files...")
                else:
                    self.update_progress(0, "Installation failed, attempting cleanup...")
                self.restore_backup(tf_path)

                if was_cancelled:
                    # don't show error dialog for cancellations
                    pass
                else:
                    self.error_signal.emit("Installation failed. Files have been restored to default state.")
            except Exception as cleanup_error:
                # catastrophic failure
                self.error_signal.emit(
                    f"CATASTROPHIC FAILURE: Installation failed and cleanup also failed.\n"
                    f"Original error: {str(e)}\n"
                    f"Cleanup error: {str(cleanup_error)}\n\n"
                    f"Please verify your game files through Steam:\n"
                    f"Library > Right-click Team Fortress 2 > Properties > Installed Files > Verify integrity of game files"
                )
        finally:
            prepare_working_copy()
            self.operation_finished.emit()

    def restore_backup(self, tf_path: str):
        try:
            prepare_working_copy()
            custom_dir = Path(tf_path) / 'custom'
            custom_dir.mkdir(exist_ok=True)

            tf_path_obj = Path(tf_path)
            is_tf2 = tf_path_obj.name == "tf"

            # restore gameinfo.txt (for all targets)
            game_type(Path(tf_path) / 'gameinfo.txt', uninstall=True)

            if is_tf2:
                # remove preloader-installed HUDs (TF2-specific)
                self.cleanup_huds(custom_dir)
                # TF2-specific: restore VPK patches, quickprecache, mainmenu
                restore_skybox_files(tf_path)
                restore_particle_files(tf_path)
                enable_paints(tf_path)

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

                # cleanup backup mainmenu folder
                backup_mainmenu_folder = custom_dir / BACKUP_MAINMENU_FOLDER
                if backup_mainmenu_folder.exists():
                    shutil.rmtree(backup_mainmenu_folder)

            # remove custom VPKs we created (for all targets)
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
            prepare_working_copy()
            self.operation_finished.emit()

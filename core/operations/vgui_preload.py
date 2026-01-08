import logging
import shutil
from pathlib import Path

from valve_parsers import VPKFile

from core.constants import BACKUP_MAINMENU_FOLDER
from core.folder_setup import folder_setup

log = logging.getLogger()


def patch_mainmenuoverride(tf_path: str):
    custom_dir = Path(tf_path) / 'custom'
    if not custom_dir.exists():
        return

    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue

        if (item.is_file() and
              item.suffix.lower() == ".vpk" and
              "casual_preloader" not in item.name.lower()):
            _process_vpk(item)

    # check if any directory has mainmenuoverride.res
    found_mainmenuoverride = False
    for item in custom_dir.iterdir():
        if "_casual_preloader" in item.name.lower():
            continue

        if item.is_dir():
            mainmenuoverride_file = item / "resource" / "ui" / "mainmenuoverride.res"
            if mainmenuoverride_file.exists():
                _add_vguipreload_string(mainmenuoverride_file)
                found_mainmenuoverride = True

    if not found_mainmenuoverride:
        # create backup folder in custom/ with mainmenuoverride.res
        backup_folder = custom_dir / BACKUP_MAINMENU_FOLDER
        backup_folder_custom = backup_folder / "resource" / "ui"
        backup_folder_custom.mkdir(parents=True, exist_ok=True)

        # copy mainmenuoverride.res to backup folder
        shutil.copy2(folder_setup.install_dir / 'backup/resource/ui/mainmenuoverride.res', backup_folder_custom/ 'mainmenuoverride.res')

        # info.vdf so tf2 accepts res file
        shutil.copy2(folder_setup.install_dir / 'backup/info.vdf', backup_folder / 'info.vdf')
        _add_vguipreload_string(backup_folder_custom/ "mainmenuoverride.res")


def _add_vguipreload_string(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if "vguipreload.res" not in content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('#base "vguipreload.res"\n' + content)
            return True
    except Exception:
        log.exception(f'Failed to modify {file_path}')


def _process_vpk(vpk_path):
    try:
        vpk_file = VPKFile(vpk_path)
        target_files = vpk_file.find_files("resource/ui/mainmenuoverride.res")

        # skip if no mainmenuoverride.res
        if not target_files:
            return

        custom_dir = vpk_path.parent
        vpk_name = vpk_path.stem
        extract_dir = custom_dir / vpk_name
        extract_dir.mkdir(parents=True, exist_ok=True)

        vpk_file.extract_all(str(extract_dir))

        extracted_mainmenuoverride_file = extract_dir / "resource" / "ui" / "mainmenuoverride.res"
        _add_vguipreload_string(extracted_mainmenuoverride_file)

        # delete the original VPK file
        vpk_path.unlink()

    except Exception:
        log.exception(f"Error extracting VPK {vpk_path}")

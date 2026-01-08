import json
import logging
from pathlib import Path
from typing import Optional

from core.folder_setup import folder_setup
from core.util.file import copy, delete

log = logging.getLogger()


def import_mods_folder(src_path: Path) -> tuple[bool, str]:
    """
    Import a mods folder from a previous installation.

    Args:
        src_path: Path to the source mods folder

    Returns:
        Tuple of (success, error_message)
    """

    try:
        mods_dst = folder_setup.mods_dir

        if not src_path.exists() or not src_path.is_dir():
            return False, f"Source mods folder does not exist: {src_path}"

        delete(mods_dst, not_exist_ok=True)
        copy(src_path, mods_dst)
        return True, ""

    except Exception as e:
        log.exception("Failed to import mods folder")
        return False, str(e)


def save_initial_settings(tf_directory: Path, import_settings_path: Optional[Path] = None) -> tuple[bool, str]:
    """
    Create or update app_settings.json with initial setup values.

    Args:
        tf_directory: The tf/ directory path to save
        import_settings_path: Optional path to existing settings file to import

    Returns:
        Tuple of (success, error_message)
    """

    try:
        settings_data = {}
        if import_settings_path:
            try:
                with open(import_settings_path, 'r') as f:
                    settings_data = json.load(f)
            except Exception as e:
                log.warning(f"Failed to import settings file: {e}")
                # continue with empty settings

        settings_data["tf_directory"] = str(tf_directory)

        folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)
        with open(folder_setup.app_settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)

        return True, ""

    except Exception as e:
        log.exception("Failed to save settings")
        return False, str(e)


def find_mods_folder_for_settings(settings_path: Path) -> Optional[Path]:
    """
    Look for a mods folder adjacent to a settings file.

    Args:
        settings_path: Path to app_settings.json

    Returns:
        Path to mods folder if found, None otherwise
    """

    mods_path = settings_path.parent / "mods"

    if mods_path.exists() and mods_path.is_dir():
        return mods_path

    return None

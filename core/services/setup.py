import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple

from core.folder_setup import folder_setup

log = logging.getLogger()


def import_mods_folder(src_path: str) -> Tuple[bool, str]:
    """
    Import a mods folder from a previous installation.

    Args:
        src_path: Path to the source mods folder

    Returns:
        Tuple of (success, error_message)
    """
    try:
        mods_src = Path(src_path)
        mods_dst = folder_setup.mods_dir

        if not mods_src.exists() or not mods_src.is_dir():
            return False, f"Source mods folder does not exist: {src_path}"

        if mods_dst.exists():
            shutil.rmtree(mods_dst)

        shutil.copytree(mods_src, mods_dst)
        return True, ""

    except Exception as e:
        log.exception("Failed to import mods folder")
        return False, str(e)


def save_initial_settings(tf_directory: str, import_settings_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Create or update app_settings.json with initial setup values.

    Args:
        tf_directory: The tf/ directory path to save
        import_settings_path: Optional path to existing settings file to import

    Returns:
        Tuple of (success, error_message)
    """
    try:
        folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)
        settings_file = folder_setup.settings_dir / "app_settings.json"

        settings_data = {}
        if import_settings_path:
            try:
                settings_src = Path(import_settings_path)
                with open(settings_src, 'r') as f:
                    settings_data = json.load(f)
            except Exception as e:
                log.warning(f"Failed to import settings file: {e}")
                # continue with empty settings

        settings_data["tf_directory"] = tf_directory

        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)

        return True, ""

    except Exception as e:
        log.exception("Failed to save settings")
        return False, str(e)


def find_mods_folder_for_settings(settings_path: str) -> Optional[str]:
    """
    Look for a mods folder adjacent to a settings file.

    Args:
        settings_path: Path to app_settings.json

    Returns:
        Path to mods folder if found, None otherwise
    """
    settings_file = Path(settings_path)
    mods_path = settings_file.parent / "mods"

    if mods_path.exists() and mods_path.is_dir():
        return str(mods_path)

    return None

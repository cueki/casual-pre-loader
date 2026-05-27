import json
import logging
from pathlib import Path

from core.folder_setup import folder_setup
from core.util.file import copy, delete

log = logging.getLogger()


def is_valid_userdata_folder(userdata_path: Path) -> bool:
    """Return True if path looks like a userdata/ folder (has data/ and config/ subfolders)."""
    if not userdata_path.is_dir():
        return False
    return (userdata_path / 'data').is_dir() and (userdata_path / 'config').is_dir()


def import_userdata(userdata_path: Path) -> tuple[bool, list[str]]:
    """
    Import a userdata folder from a previous installation.

    Copies mods/, modsinfo.json, app_settings.json, and addon_metadata.json
    into the locations defined by folder_setup.

    Args:
        userdata_path: Path to the source userdata folder (containing data/ and config/)

    Returns:
        Tuple of (success, list of warning messages for files that were missing or failed)
    """

    if not is_valid_userdata_folder(userdata_path):
        return False, [
            f"Source is not a valid userdata folder (missing data/ or config/): {userdata_path}"
        ]

    src_data = userdata_path / 'data'
    src_config = userdata_path / 'config'

    items: list[tuple[Path, Path]] = [
        (src_data / 'mods', folder_setup.mods_dir),
        (src_data / 'modsinfo.json', folder_setup.modsinfo_file),
        (src_config / 'app_settings.json', folder_setup.app_settings_file),
        (src_config / 'addon_metadata.json', folder_setup.addon_metadata_file),
    ]

    warnings: list[str] = []
    for src, dst in items:
        if src.resolve() == dst.resolve():
            continue
        if not src.exists():
            warnings.append(f"Not present in source: {src.name}")
            continue
        try:
            delete(dst, not_exist_ok=True)
            copy(src, dst)
        except Exception as e:
            log.exception(f"Failed to import {src}")
            warnings.append(f"Failed to import {src.name}: {e}")

    return True, warnings


def save_initial_settings(tf_directory: Path) -> tuple[bool, str]:
    """
    Create or update app_settings.json with initial setup values.

    If app_settings.json already exists (e.g. from a previous userdata import),
    its other keys are preserved and only tf_directory is overwritten.

    Args:
        tf_directory: The tf/ directory path to save

    Returns:
        Tuple of (success, error_message)
    """

    try:
        settings_data = {}
        if folder_setup.app_settings_file.exists():
            try:
                with open(folder_setup.app_settings_file, 'r') as f:
                    settings_data = json.load(f)
            except Exception as e:
                log.warning(f"Failed to read existing settings file: {e}")
                # continue with empty settings

        settings_data["tf_directory"] = str(tf_directory)

        folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)
        with open(folder_setup.app_settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)

        return True, ""

    except Exception as e:
        log.exception("Failed to save settings")
        return False, str(e)

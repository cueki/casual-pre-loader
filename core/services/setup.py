import json
import logging
from pathlib import Path

from core.config import config
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
    into the locations defined by FolderConfig.

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
        (src_data / config.mods_dir.name, config.mods_dir),
        (src_data / config.modsinfo_file.name, config.modsinfo_file),
        (src_config / config.app_settings_file.name, config.app_settings_file),
        (src_config / config.addon_metadata_file.name, config.addon_metadata_file),
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

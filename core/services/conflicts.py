from pathlib import Path


# Legacy files from old Modern Casual Preloader that conflict with this method
LEGACY_MCP_ITEMS = {
    "folders": ["_modern casual preloader"],
    "files": [
        "_mcp hellfire hale fix.vpk",
        "_mcp mvm victory screen fix.vpk",
        "_mcp saxton hale fix.vpk"
    ]
}


def detect_addon_overwrites(
    load_order: list[str],
    addon_contents: dict[str, list[str]],
    addon_name_mapping: dict[str, dict] | None = None
) -> dict[str, dict[str, list[str]]]:
    """
    Detect which addons will overwrite files from other addons based on load order.

    Args:
        load_order: List of addon display names in display order (top = highest priority)
        addon_contents: Dict mapping folder names to list of files
        addon_name_mapping: Optional dict mapping display names to addon info with 'file_path'

    Returns:
        Dict mapping addon name to {overwritten_addon: [conflicting_files]}
    """

    if addon_name_mapping is None:
        addon_name_mapping = {}

    all_overwrites = {}

    for pos, addon_name in enumerate(load_order):
        # resolve display name to folder name
        folder_name = addon_name
        if addon_name in addon_name_mapping:
            folder_name = addon_name_mapping[addon_name].get('file_path', addon_name)

        if folder_name not in addon_contents:
            continue

        addon_files = set(addon_contents[folder_name])
        overwrites = {}

        # check against lower priority addons (later in list = lower priority)
        for other_pos, other_name in enumerate(load_order):
            if other_pos > pos:
                other_folder_name = other_name
                if other_name in addon_name_mapping:
                    other_folder_name = addon_name_mapping[other_name].get('file_path', other_name)

                if other_folder_name in addon_contents:
                    other_files = set(addon_contents[other_folder_name])
                    common_files = addon_files.intersection(other_files)
                    if common_files:
                        overwrites[other_name] = list(common_files)

        if overwrites:
            all_overwrites[addon_name] = overwrites

    return all_overwrites


def scan_for_legacy_conflicts(custom_dir: Path) -> list[str]:
    """
    Scan the custom directory for legacy MCP files that may conflict.

    Args:
        custom_dir: Path to the tf/custom directory

    Returns:
        List of found conflicting items (formatted strings)
    """

    if not custom_dir.exists():
        return []

    found_conflicts = []

    for folder_name in LEGACY_MCP_ITEMS["folders"]:
        folder_path = custom_dir / folder_name
        if folder_path.exists() and folder_path.is_dir():
            found_conflicts.append(f"Folder: {folder_name}")

    for file_name in LEGACY_MCP_ITEMS["files"]:
        file_path = custom_dir / file_name
        if file_path.exists() and file_path.is_file():
            found_conflicts.append(f"File: {file_name}")

    return found_conflicts

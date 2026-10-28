from pathlib import Path


def get_vpk_name(game_path: Path | str) -> str:
    """Find the main tf2_misc_dir.vpk file."""
    return "tf2_misc_dir.vpk"


def normalize_vpk_paths(vpk_paths: list[Path]) -> list[Path]:
    """
    Normalize and deduplicate VPK paths.
    Multi-part VPKs (mod_000.vpk, mod_001.vpk, mod_dir.vpk) all resolve to mod_dir.vpk.
    """

    normalized = {}
    for vpk_path in vpk_paths:
        vpk_name = vpk_path.stem
        if len(vpk_name) >= 4 and vpk_name[-4] == '_' and (vpk_name[-3:].isdigit() or vpk_name[-3:] == 'dir'):
            base_name = vpk_name[:-4]
            normalized[base_name] = vpk_path.parent / f"{base_name}_dir.vpk"
        else:
            normalized[vpk_name] = vpk_path
    return list(normalized.values())

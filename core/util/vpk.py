from pathlib import Path


def get_vpk_name(game_path: Path | str) -> str:
    """Find the main tf2_misc_dir.vpk file."""
    return "tf2_misc_dir.vpk"

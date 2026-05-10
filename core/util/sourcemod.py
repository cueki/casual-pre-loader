import sys
from pathlib import Path
from typing import Any, Optional

from core.constants import SOURCEMODS


def normalize_sourcemod(sourcemod: int | str) -> tuple[Optional[int], str]:
    """
    Normalizes sourcemods using known aliases.

    Args:
        sourcemod: The steam id of a sourcemod, its name or an alias thereof.

    Returns:
        A tuple containing the sourcemod's id if known and name.
    """

    if isinstance(sourcemod, int):
        if sourcemod in SOURCEMODS:
            if isinstance(SOURCEMODS[sourcemod], str):
                return sourcemod, SOURCEMODS[sourcemod]
            else:
                return sourcemod, SOURCEMODS[sourcemod][0]
        else:
            raise ValueError(f'Unknown sourcemod with steam id {sourcemod}')

    _sourcemod = sourcemod.lower()
    for id, name in SOURCEMODS.items():
        if isinstance(name, str):
            if _sourcemod == name.lower():
                return id, name
        else:
            for _name in name:
                if _sourcemod == _name.lower():
                    return id, name[0]

    return None, sourcemod


def auto_detect_sourcemod(game_target: str = "Team Fortress 2") -> str | None:
    """Auto-detect a Source mod installation by looking for a subdirectory with gameinfo.txt.

    Args:
        game_target: The Steam game folder name. Defaults to "Team Fortress 2".

    Returns:
        The path to the mod directory, or None if not found.
    """
    if sys.platform == 'win32':
        steam_paths = [
            Path("C:/Program Files (x86)/Steam/steamapps/common"),
            Path("D:/Program Files (x86)/Steam/steamapps/common"),
        ]
    else:
        steam_paths = [
            Path("~/.steam/steam/steamapps/common").expanduser(),
            Path("~/.local/share/Steam/steamapps/common").expanduser(),
        ]

    game_target_lower = game_target.lower()

    for steam_path in steam_paths:
        if not steam_path.exists():
            continue

        for game_folder in steam_path.iterdir():
            if not game_folder.is_dir() or game_folder.name.lower() != game_target_lower:
                continue

            for subdir in game_folder.iterdir():
                if subdir.is_dir() and (subdir / "gameinfo.txt").exists():
                    return str(subdir)

    return None


def validate_game_directory(directory: str | None, validation_label: Optional[Any] = None) -> bool:
    """Validate a Source mod directory by checking for gameinfo.txt."""
    if not directory:
        if validation_label:
            validation_label.setText("")
        return False

    path = Path(directory)

    if not path.exists():
        if validation_label:
            validation_label.setText("Directory does not exist!")
            validation_label.setStyleSheet("color: red;")
        return False

    if not (path / "gameinfo.txt").exists():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid Source mod directory")
            validation_label.setStyleSheet("color: red;")
        return False

    if validation_label:
        validation_label.setText("Valid Source mod directory detected!")
        validation_label.setStyleSheet("color: green;")

    return True

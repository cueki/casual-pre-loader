import logging
import string
import sys
from pathlib import Path
from typing import Any
from core.constants import Sourcemods
log = logging.getLogger()


class InvalidSourcemod(KeyError):
    pass

class InvalidSourcemodInstallationPath(FileNotFoundError):
    pass


def clean_name(name: str) -> str:
    non_alphanum = str.maketrans('', '', string.whitespace + string.punctuation)
    return name.translate(non_alphanum)


def get_sourcemod(sourcemod: int | str | None = None) -> Sourcemods:
    """
    Normalizes sourcemods using known aliases.

    Args:
        sourcemod: The steam id of a sourcemod, its name or an alias thereof, or None (gets the default).

    Returns:
        The sourcemod
    """

    if sourcemod is None:
        return Sourcemods.DEFAULT

    if isinstance(sourcemod, int):
        for _sourcemod in Sourcemods:
            if sourcemod == _sourcemod.appid:
                return  _sourcemod
        else:
            raise InvalidSourcemod(f'Unknown sourcemod with steam id {sourcemod}')

    sourcemod_upper_clean = clean_name(sourcemod.upper()) # enum names are upper case

    try:
        return Sourcemods[sourcemod_upper_clean]
    except KeyError:
        pass

    # give priority to exact matches
    for _sourcemod in Sourcemods:
        if _sourcemod.full_name == sourcemod:
            return _sourcemod

    for _sourcemod in Sourcemods:
        if clean_name(_sourcemod.full_name.upper()) == sourcemod_upper_clean:
            return _sourcemod

    raise InvalidSourcemod(f'Unknown sourcemod with name/alias or abbreviation thereof `{sourcemod}`')

def auto_detect_sourcemod(sourcemod: Sourcemods = Sourcemods.DEFAULT) -> Path:
    """Auto-detect a Source mod installation by looking for a subdirectory with gameinfo.txt.

    Args:
        sourcemod: A sourcemod object

    Returns:
        The path to the mod directory.
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

    name_lower = sourcemod.full_name.lower()
    name_lower_clean = clean_name(name_lower)
    for steam_path in steam_paths:
        if not steam_path.is_dir():
            continue

        for game_folder in steam_path.iterdir():
            if not game_folder.is_dir():
                    continue

            _name_lower = game_folder.name.lower()
            if not (_name_lower == name_lower or clean_name(_name_lower) == name_lower_clean):
                continue

            for subdir in game_folder.iterdir():
                if subdir.is_dir() and (subdir / 'gameinfo.txt').is_file():
                    return subdir

    raise InvalidSourcemodInstallationPath(f'Cannot find installation path for sourcemod `{sourcemod.name}`')


# TODO: narrow types
def validate_game_directory(path: Path | None, validation_label: Any | None = None) -> bool:
    """Validate a Source mod directory by checking for gameinfo.txt."""
    if path is None:
        if validation_label:
            validation_label.setText('')
        return False

    if not path.is_dir():
        if validation_label:
            validation_label.setText('Directory does not exist!')
            validation_label.setStyleSheet('color: red;')
        return False

    if not (path / 'gameinfo.txt').is_file():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid Source mod directory")
            validation_label.setStyleSheet('color: red;')
        return False

    if validation_label:
        validation_label.setText('Valid Source mod directory detected!')
        validation_label.setStyleSheet('color: green;')

    return True

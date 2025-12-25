import stat
from itertools import starmap
from operator import methodcaller
from pathlib import Path

from core.folder_setup import folder_setup
from core.util.file import delete, move

# Files and folders to delete
DELETE_PORTABLE: list[Path] = [
    #
    # old updater
    #
    folder_setup.install_dir / "core" / "updater_old.exe",
    folder_setup.install_dir / "RUNME.tmp.bat",
    #
    # old files/folders
    #
    folder_setup.install_dir / "particle_system_map.json",
    folder_setup.install_dir / "mod_urls.json",
    folder_setup.install_dir / "operations",
    folder_setup.install_dir / "quickprecache",
]
DELETE: list[tuple[Path, Path]] = []

# Files and folders to relocate
MOVE_PORTABLE: list[tuple[Path, Path]] = []
MOVE: list[tuple[Path, Path]] = []

# Files and folders to change the mode of
MODE: dict[int, list[Path]] = {
    # set executable bit
    stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR: [
        folder_setup.install_dir / "main.py",
    ]
}


def migrate():
    if folder_setup.portable:
        map(delete, DELETE_PORTABLE)
        starmap(move, MOVE_PORTABLE)

    map(delete, DELETE)
    starmap(move, MOVE)
    starmap(
        lambda mode, files: map(methodcaller("chmod", mode=mode), files), MODE.items()
    )

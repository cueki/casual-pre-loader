import stat
from functools import partial
from itertools import starmap
from pathlib import Path

from core.folder_setup import folder_setup
from core.util.file import delete, move

# Files and folders to delete
DELETE_PORTABLE: list[Path] = [
    #
    # old updater
    #
    folder_setup.install_dir / 'core' / 'updater_old.exe',
    folder_setup.install_dir / 'RUNME.tmp.bat',
    #
    # old files/folders
    #
    folder_setup.install_dir / 'particle_system_map.json',
    folder_setup.install_dir / 'mod_urls.json',
    folder_setup.install_dir / 'operations',
    folder_setup.install_dir / 'quickprecache',
]
DELETE: list[tuple[Path, Path]] = []

# Files and folders to relocate
MOVE_PORTABLE: list[tuple[Path, Path]] = []
MOVE: list[tuple[Path, Path]] = []

# Files and folders to set the mode of
MODE: dict[int, list[Path]] = {}
MODE_PORTABLE: dict[int, list[Path]] = {
    # set executable bit
    stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR: [
        folder_setup.install_dir / 'main.py',
        folder_setup.install_dir / 'scripts' / 'build.py',
        folder_setup.install_dir / 'scripts' / 'analyze_particle_hierarchy.py',
        folder_setup.install_dir / 'scripts' / 'particle_file_merger.py',
        folder_setup.install_dir / 'scripts' / 'run.sh',
    ]
}


def migrate():
    def modeset(mode: int, files: list[Path]) -> None:
        map(lambda file: file.exists() and file.chmod(mode), files)

    _delete = partial(delete, not_exist_ok=True)
    _move = partial(move, not_exist_ok=True)

    if folder_setup.portable:
        map(_delete, DELETE_PORTABLE)
        starmap(_move, MOVE_PORTABLE)
        starmap(modeset, MODE_PORTABLE.items())

    map(_delete, DELETE)
    starmap(_move, MOVE)
    starmap(modeset, MODE.items())

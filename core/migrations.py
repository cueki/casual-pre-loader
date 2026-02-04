import stat
from functools import partial
from itertools import starmap
from pathlib import Path
from typing import Iterable

from more_itertools import consume

from core.folder_setup import folder_setup
from core.util.file import delete, modeset, modeset_add, move

"""
This module has a single function, `migrate()`, that ensures that old files are cleaned up or moved into new locations.
This is so that if we change things, users will have a (hopefully) seamless expereince.

For instance, let's say we write to a directory, `/dir/subdir`, but we decide that it'd be better to call it `/dir/subdir2`.
We'd add an entry in this file to move `/dir/subdir` to `dir/subdir2`, commit that, and generate a new minor (or major) release.

Generating a new release would technically not be strictly necessary,
but assuming that users make use of the auto-updater, they won't end up with broken program/data/config files.
The auto-updater repeatedly updates to the next non-downloaded minor/major release and calls `migrate()`,
meaning that we can remove all old migrations from `migrate()` every time we generate a new release.

Granted, users using a rolling-release package manager, e.g. pacman, or users using `git` directly could still end up with broken files,
since there is no way to tell pacman to update to only the next version instead of the latest,
nor could we tell pacman to run the program in between those updates.
Technically, programs like `downgrade` exist, or users could manually grab old packages, but this is irrelevant to AUR packages anyway.
ALl this aside, such users should usually be expected to have some knowledge about the programs they run and the packages they install,
so I'd say this is a tolerable shortcoming.

To try and mitigate this potential problem, it is recommended to not remove things from this file too often, once a month at the most should be fine.

`migrate()` only needs to be called once per program execution, so even though they are effectively constants, put all migration data into its body so it can get GC'ed when it goes OOS.
"""

def migrate():
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
        folder_setup.install_dir / 'temp',
    ]
    DELETE: list[tuple[Path, Path]] = [
        folder_setup.project_dir / 'temp',
    ]

    # Files and folders to relocate
    MOVE_PORTABLE: list[tuple[Path, Path]] = [
        #
        # userdata
        #
        (folder_setup.install_dir / 'mods', folder_setup.mods_dir),
        (folder_setup.install_dir / 'app_settings.json', folder_setup.app_settings_file),
        (folder_setup.install_dir / 'addon_metadata.json', folder_setup.addon_metadata_file),
        (folder_setup.install_dir / 'casual-pre-loader.log', folder_setup.log_file),
        (folder_setup.install_dir / 'modsinfo.json', folder_setup.modsinfo_file),
    ]
    MOVE: list[tuple[Path, Path]] = []

    # Files and folders to set the mode of
    MODESET: dict[int, list[Path]] = {}
    MODESET_PORTABLE: dict[int, list[Path]] = {}
    MODESET_ADD: dict[int, list[Path]] = {}
    MODESET_ADD_PORTABLE: dict[int, list[Path]] = {
        # set executable bit
        stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR: [
            folder_setup.install_dir / 'main.py',
            folder_setup.install_dir / 'scripts' / 'build.py',
            folder_setup.install_dir / 'scripts' / 'analyze_particle_hierarchy.py',
            folder_setup.install_dir / 'scripts' / 'particle_file_merger.py',
            folder_setup.install_dir / 'scripts' / 'run.sh',
        ]
    }

    def _delete(files: Iterable[Path]):
        consume(map(partial(delete, not_exist_ok=True), files))

    def _move(pairs: Iterable[tuple[Path, Path]]):
        consume(starmap(partial(move, not_exist_ok=True), pairs))

    def _modeset(groups: Iterable[tuple[int, Path]]):
        for mode, files in groups:
            consume(map(partial(modeset, mode=mode, not_exist_ok=True), files))

    def _modeset_add(groups: Iterable[tuple[int, Path]]):
        for mode, files in groups:
            consume(map(partial(modeset_add, mode=mode, not_exist_ok=True), files))

    if folder_setup.portable:
        DELETE += DELETE_PORTABLE
        MOVE += MOVE_PORTABLE

        for k,v in MODESET_PORTABLE.items():
            MODESET[k] = MODESET.get(k, []) + v

        for k,v in MODESET_ADD_PORTABLE.items():
            MODESET_ADD[k] = MODESET_ADD.get(k, []) + v

    _delete(DELETE)
    _move(MOVE)
    _modeset(MODESET.items())
    _modeset_add(MODESET_ADD.items())

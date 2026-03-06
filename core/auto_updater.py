import logging
import os
import re
import sys
from collections import defaultdict
from operator import attrgetter
from typing import Optional

from packaging import version

from core.constants import BUILD_DIRS, BUILD_FILES, REMOTE_REPO
from core.folder_setup import folder_setup
from core.util.file import copy, delete
from core.util.net import download_file
from core.util.repo import Update
from core.util.repo.github_api import get_releases_with_asset
from core.util.zip import extract
from core.version import VERSION

log = logging.getLogger()

"""
This module handles all the logic related to auto-updating.
One can assume that any functions in this file will only run if the application is installed portably.
"""

# TODO: what is needad for auto updates to be fully auto?
# - be able to tell if we were ran with a wrapper script [scripts/run.sh] (simplest method would be to use an envvar)
# - programatically get min python version (pyproject.toml)
# - programatically get dependency information (pyproject.toml)
# - be able to determine if there are pending updates before running the main app (extract them to a tmpdir, check that on startup, apply them one by one, execing each time to relaod the runscript/interpreter)


def check_for_updates() -> tuple[Update]:
    """
    Check the source repository for new releases.

    Returns:
        A tuple of updates sorted by ascending chronological order.
    """

    try: # get the latest version of each minor release that we are behind of
        updates = defaultdict(dict)
        current = version.parse(VERSION)
        platform_name = 'linux' if sys.platform == 'linux' else 'win'

        # sort by descending chronological order, so we only store the latest patch release for every minor release
        for update in sorted(get_releases_with_asset(REMOTE_REPO, re.compile(fr'^casual-pre-?loader(-{platform_name})?.*\.zip')), key=attrgetter('version'), reverse=True):
            if update.version > current:
                updates[update.version.major].setdefault(update.version.minor, update)

        return tuple(update for major_updates in updates.values() for update in major_updates.values())[::-1] # reverse the tuple so it's sorted by ascending chronological order

    except Exception:
        log.exception('Error checking for updates')
        return tuple()


def perform_updates(updates: Optional[tuple[Update]] = None) -> None:
    """
    Download and apply all available updates.

    Args:
        updates: An optional tuple of updates. If this is not supplied, the output of `check_for_updates()` is used.
    """

    updates = updates or check_for_updates()

    # TODO: update this once we can update multiple at a time
    for update in updates:
        archive_path = folder_setup.temp_dir / 'update' / f'{update.release.tag_name}.zip'

        try:
            log.info(f'Downloading application update ({update.release.tag_name})')
            download_file(update.asset.browser_download_url, archive_path, 30)
        except Exception:
            log.exception(f'Error downloading update {update.release.tag_name}')
            break

        match sys.platform:
            case 'win32':
                renamed_runme = folder_setup.install_dir.parent / 'RUNME.tmp.bat'

                try:
                    extract(archive_path, folder_setup.install_dir.parent / '.tmp_update', 0, False, None)
                    copy(folder_setup.install_dir.parent / 'RUNME.bat', renamed_runme) # INFO: we need to rename RUNME to avoid file lock issues
                except Exception:
                    log.exception(f'Error extracting update {update.release.tag_name}')

                    delete(folder_setup.install_dir.parent / '.tmp_update')
                    delete(renamed_runme)

                    break
                finally:
                    delete(archive_path)

                os.chdir('..')
                os.execvpe('cmd.exe', ['cmd.exe', '/c', '.\\' + renamed_runme.name] + sys.argv[1:], os.environ) # NOTE: quits the interpreter and executes renamed RUNME

            case 'linux':
                include = tuple((*BUILD_FILES, *BUILD_DIRS))
                def _filter(root) -> bool:
                    def __filter(path) -> bool:
                        path = path.relative_to(root)
                        return any(map(lambda x: path.startswith(x), include))

                    return __filter

                try:
                    extract(archive_path, folder_setup.install_dir, 1, False, _filter)
                except Exception:
                    log.exception(f'Error extracting update {update.release.tag_name}')

                    break
                finally:
                    delete(archive_path)

                os.execve(sys.executable, [sys.executable] + sys.argv, os.environ) # NOTE: calls `exec()` and restarts the program

            case _:
                raise NotImplementedError

import logging
import os
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
from core.util.repo.github import get_releases_with_asset
from core.util.zip import extract
from core.version import VERSION

log = logging.getLogger()

# TODO: what is needad for auto updates to be fully auto?
# - be able to tell if we were ran with a wrapper script [scripts/run.sh] (argparse)
# - programatically get min python version (pyproject.toml)
# - programatically get dependency information (pyproject.toml)
# - be able to determine if there are pending updates before running the main app (extract them to a tmpdir, check that on startup, apply them one by one, execing each time to relaod the interpreter)


def check_for_updates() -> tuple[Update]:
    try: # get the latest version of each minor release that we are behind of
        _updates = sorted(get_releases_with_asset(REMOTE_REPO, 'casual-preloader.zip'), key=attrgetter('version'), reverse=True)

        updates = defaultdict(dict)
        current = version.parse(VERSION)
        for update in _updates:
            if update.version.major > current.major or (update.version.major == current.major and update.version.minor > current.minor):
                updates[update.version.major].setdefault(update.version.minor, update)

        return tuple(update for major, _major in updates.items() for minor, update in _major.items())

    except Exception:
        log.exception('Error checking for updates')
        return tuple()


def perform_updates(updates: Optional[tuple[Update]] = None) -> None:
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
                renamed_runme = folder_setup.install__dir / 'RUNME.tmp.bat'

                try:
                    extract(archive_path, folder_setup.install_dir / '.tmp_update', 0, False, None)
                    copy(folder_setup.install_dir / 'RUNME.bat', renamed_runme) # INFO: we need to rename RUNME to avoid file lock issues
                except Exception:
                    log.exception(f'Error extracting update {update.release.tag_name}')

                    delete(folder_setup.install_dir / '.tmp_update')
                    delete(renamed_runme)

                    break
                finally:
                    delete(archive_path)

                os.execve(renamed_runme, [renamed_runme] + sys.argv, os.environ) # NOTE: quits the interpreter and executes renamed RUNME

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

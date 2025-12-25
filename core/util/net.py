import json
import logging
import shutil
import socket
import urllib.request
from pathlib import Path
from typing import Optional

from packaging import version

from core.constants import REMOTE_REPO
from core.folder_setup import folder_setup
from core.util.repo import Update
from core.util.repo.github import get_releases_with_asset

log = logging.getLogger()


def check_mods() -> Optional[Update]:
    modsinfo = None
    try:
        with folder_setup.modsinfo_file.open('r') as fd:
            modsinfo = json.load(fd)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        log.exception(f'Could not parse {folder_setup.modsinfo_file}')

    # NOTE: How files are packaged
    # The preloader itself in:
    # - `casual-preloader.zip`
    # We also maintain a collection of mods (some of which were originally authored by 3rd parties but modified and distributed with permission). They're highly-recommended.
    # - `mods.zip`

    # INFO:
    # At certain points, the collection of mods was bundled with the preloader itself in the following files:
    # - `cukei_particle_preload.zip`
    # - `casual-particle-preloader.zip`
    # - `casual-preloader.zip`
    # The preloader was at one point released in two separate distribuitions, one with and one without the mods:
    # - `casual-preloader-full.zip`
    # - `casual-preloader-light.zip`
    # - There was also a time where the mods were kept in a zip file checked into the VCS...yeah, ~80 MB...

    for update in get_releases_with_asset(REMOTE_REPO, 'mods.zip'):
        if modsinfo:
            if update.asset.digest == modsinfo["digest"]:
                log.info(f'We already have the latest release of mods ({update.version})')
                return

            if not update.version > version.parse(modsinfo["tag"]):
                log.info(f"We already have the latest release of mods ({update.version}), but the remote file differs")
        else:
            log.info(f'A new release of mods is available ({update.version})')

        return update


def download_file(url: str, path: Path, timeout: Optional[int] = None, reporthook=None) -> None:
    old_timeout = socket.getdefaulttimeout()

    try:
        socket.setdefaulttimeout(timeout)

        tmp_path = folder_setup.temp_download_dir / f"{path.name}"

        folder_setup.temp_download_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, tmp_path, reporthook)

        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_path, path)

    finally:
        socket.setdefaulttimeout(old_timeout)

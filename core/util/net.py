import json
import logging
import shutil
import socket
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from github import Github
from github.GitReleaseAsset import GitReleaseAsset
from packaging import version

from core.constants import REMOTE_REPO
from core.folder_setup import folder_setup

log = logging.getLogger()


def check_mods() -> Optional[Tuple[GitReleaseAsset, str]]:
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

    log.info('Retrieving releases')
    releases = Github().get_repo(REMOTE_REPO).get_releases()
    log.info('Done retrieving releases')

    for release in releases:
        if not (release.draft or release.prerelease):
            for asset in release.assets:
                if asset.name == 'mods.zip':
                    try:
                        with folder_setup.modsinfo_file.open('r') as fd:
                            modsinfo = json.load(fd)

                        if asset.digest == modsinfo['digest']:
                            log.info(f'We already have the latest release of mods ({modsinfo["tag"]})')
                            return

                        if version.parse(release.tag.lstrip('v')) > version.parse(modsinfo['tag'].lstrip('v')):
                            log.info(f'A new release of mods {release.tag_name}, we have {modsinfo["tag"]}')

                        else:
                            log.info(f'We already have the latest release ({release.tag}), but the remote file differs')

                    except (json.JSONDecodeError, FileNotFoundError):
                        log.info('No release of mods has ever been downloaded')

                    return asset, release.tag_name


def download_file(url: str, path: Path, timeout: Optional[int] = None, reporthook=None) -> None:
    old_timeout = socket.getdefaulttimeout()

    try:
        socket.setdefaulttimeout(timeout)

        tmp_path = folder_setup.temp_dir / f'{path.name}.part'

        folder_setup.temp_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, tmp_path, reporthook)

        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp_path, path)

    finally:
        socket.setdefaulttimeout(old_timeout)

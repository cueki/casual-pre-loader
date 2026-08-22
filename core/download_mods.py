import json
import logging
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from packaging.version import Version

from core.config import config
from core.constants import REMOTE_REPO
from core.util.net import download_file, download_reporthook
from core.util.repo import Update
from core.util.repo.github_api import get_releases_with_asset
from core.util.zip import extract


def save_modsinfo(modsinfo: Mapping[str, Any]) -> None:
    config.modsinfo_file.parent.mkdir(parents=True, exist_ok=True)
    with config.modsinfo_file.open('w') as fd:
        json.dump(modsinfo, fd)


def check_mods() -> Update | None:
    """
    Check if a new modpack update is available for download.

    Returns:
        The most recent non-downloaded update if any.
    """

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
    # - There was also a time where the mods were kept in a zip file checked into the VCS...yeah, ~80 MB...per revision...

    modsinfo: dict[str, Any] = {}
    try:
        with config.modsinfo_file.open('r') as fd:
            modsinfo = json.load(fd)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        logging.exception(f'Could not parse {config.modsinfo_file}') # ignore this error and act as if the file didn't exist at all

    current_time = datetime.now(timezone.utc)

    if modsinfo and modsinfo.get('last_checked') is not None:
        last_checked = datetime.fromtimestamp(modsinfo['last_checked'], timezone.utc)
        interval = timedelta(minutes=5)
        if last_checked  > current_time - interval:
            logging.info(f'less than {interval} since we last checked for a new release of mods ({last_checked.astimezone()}), skipping...')
            return

    update = next(iter(get_releases_with_asset(REMOTE_REPO, 'mods.zip')))
    try:
        if modsinfo:
            if update.version > Version(modsinfo['tag']):
                logging.info(f'A new release of mods is available ({update.version})')
            elif update.version == Version(modsinfo['tag']) and update.asset.digest != modsinfo['digest']:
                logging.info(f'We already have the latest release of mods ({update.version}), but the remote file differs')
            else:
                logging.info(f'We already have the latest release of mods ({modsinfo['tag']})') # NOTE: also runs if local version is newer than remote
                return

        return update
    finally:
        modsinfo['last_checked'] = int(current_time.timestamp())
        save_modsinfo(modsinfo)


def download_mods(
    update: Update,
    set_value:    Callable[[int], None] | None  = None,
    set_label:    Callable[[str], None] | None  = None,
    process:      Callable[[None], None] | None = None,
    was_canceled: Callable[[None], bool] | None = None
) -> None:
    """
    Download a modpack update.

    The `set_value`, `process`, and `was_canceled` arguments are passed to `core.util.net.download_reporthook()`.

    Args:
        update: The update to download.
        set_value: Callback to update progress value.
        set_label: Callback to update text label.
        process: Callback to process progress and label updates.
        was_canceled: Callback to check if the operation was canceled.
    """

    # INFO:
    # the archive containing the mods has the same structure as `config.mods_dir`.
    # Its contents are wrapped in a `mods/` directory.

    archive_path = config.temp_dir / update.asset.name
    download_file(update.asset.browser_download_url, archive_path, 10, download_reporthook(set_value, process, was_canceled))

    set_label("Extracting mods")
    set_value(99)
    if process:
        process()

    try:
        extract(archive_path, config.mods_dir, 1, False)

        save_modsinfo(
            {
                'tag': update.release.tag_name,
                'digest': update.asset.digest,
                'last_checked': int(datetime.now(timezone.utc).timestamp()),
            }
        )
    finally:
        archive_path.unlink()

    set_value(100)

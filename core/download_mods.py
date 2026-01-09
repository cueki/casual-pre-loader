import json
import logging
from collections.abc import Callable
from typing import Optional

from packaging import version

from core.constants import REMOTE_REPO
from core.folder_setup import folder_setup
from core.util.net import download_file, download_reporthook
from core.util.repo import Update
from core.util.repo.github import get_releases_with_asset
from core.util.zip import extract

log = logging.getLogger()


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

    modsinfo = None
    try:
        with (folder_setup.project_dir / 'modsinfo.json').open('r') as fd:
            modsinfo = json.load(fd)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        log.exception(f'Could not parse {folder_setup.modsinfo_file}') # INFO: ignore this error and act as if the file didn't exist at all

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


def download_mods(
    update: Update,
    set_value: Optional[Callable[[int], None]] = None,
    set_label: Optional[Callable[[str], None]] = None,
    process: Optional[Callable[[None], None]] = None,
    was_canceled: Optional[Callable[[None], bool]] = None
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
    # the archive containing the mods has the same structure as `folder_setup.mods_dir`.
    # Its contents are wrapped in a `mods/` directory.

    archive_path = folder_setup.temp_dir / update.asset.name
    download_file(update.asset.browser_download_url, archive_path, 10, download_reporthook(set_value, process, was_canceled))

    set_label("Extracting mods")
    set_value(99)
    if process:
        process()

    try:
        extract(archive_path, folder_setup.mods_dir, 1, False)

        with (folder_setup.project_dir / 'modsinfo.json').open('w') as fd:
            json.dump({'tag': update.release.tag_name, 'digest': update.asset.digest}, fd)
    finally:
        archive_path.unlink()

    set_value(100)

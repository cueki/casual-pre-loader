import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from typing import Any, Self

from packaging.version import Version

from core.config import config
from core.constants import REMOTE_REPO
from core.util.net import download_file, download_reporthook
from core.util.repo import Update
from core.util.repo.github_api import get_releases_with_asset
from core.util.zip import extract

log = logging.getLogger(__name__)


@dataclass
class Modsinfo:
    tag: str | None = None
    digest: str | None = None
    last_checked: datetime | None = None

    @classmethod
    def from_dict(cls, modsinfo: Mapping[str, Any]) -> Self:
        modsinfo = dict(modsinfo)

        modsinfo.setdefault('tag', None)
        modsinfo.setdefault('digest', None)

        # deserialize Datetime objects
        modsinfo['last_checked'] = datetime.fromtimestamp(modsinfo['last_checked'], timezone.utc) if 'last_checked' in modsinfo else None

        return cls(**{ # silently ignore unknown fields
            f.name: modsinfo[f.name]
            for f in fields(cls)
            if f.name in modsinfo
        })

    @classmethod
    def load(cls) -> Self:
        try:
            with config.modsinfo_file.open('r') as fd:
                return cls.from_dict(json.load(fd))
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            log.exception(f'Could not parse {config.modsinfo_file}') # ignore this error and act as if the file didn't exist at all

        return cls()

    def save(self) -> None:
        modsinfo = asdict(self)

        if modsinfo['last_checked'] is not None:
            modsinfo['last_checked'] = int(modsinfo['last_checked'].timestamp())

        config.modsinfo_file.parent.mkdir(parents=True, exist_ok=True)
        with config.modsinfo_file.open('w') as fd:
            json.dump(modsinfo, fd)

    @property # will re-computer on subsequent calls, but I'd rather not use core.util.dep.Dep here. Modsinfo objects are short-lived anyways, so this isn't too bad
    def version(self) -> Version | None:
        return Version(self.tag) if self.tag is not None else None


def check_mods(force: bool = False) -> Update | None:
    """
    Check if a new modpack update is available for download.

    Args:
        force: Return the most recent update even if it is already installed.

    Returns:
        The most recent non-downloaded update if any, or the most recent update when `force` is set.
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

    modsinfo: Modsinfo = Modsinfo.load()
    current_time = datetime.now(timezone.utc)

    if modsinfo.last_checked is not None:
        if force:
            log.debug('forcefully skipping client-side ratelimit when checking for new mod releases')
        else:
            interval = timedelta(minutes=5)
            if modsinfo.last_checked > current_time:
                log.warning(f'last recorded check for a new release of mods is in the future, ({modsinfo.last_checked.astimezone()}), has the system\'s clock been rolled back?')
            elif modsinfo.last_checked + interval  > current_time:
                log.info(f'less than {interval} since the last recorded check for a new release of mods ({modsinfo.last_checked.astimezone()}), skipping...')
                return

    try:
        try:
            # may throw an error if the github API's ratelimit is exceed, should be handled by this function's caller
            # TODO: this does the job, but this exception should probably be handled at a lower level
            update = next(iter(get_releases_with_asset(REMOTE_REPO, 'mods.zip')))
        except StopIteration:
            log.warning('No mod releases seem to be available!')
            return

        if modsinfo.version is not None:
            if update.version > modsinfo.version:
                log.info(f'A new release of mods is available ({update.version})')
            elif update.version == modsinfo.version and update.asset.digest != modsinfo.digest:
                log.info(f'We already have the latest release of mods ({update.version}), but the remote file differs')
            elif force:
                # NOTE: this will download an older modpack release if the newest remote version is somehow older than the local version
                # (remote getting deleted or users manually editing file)
                log.info(f'Re-downloading the latest release of mods ({update.version}) by request')
            else:
                log.info(f'We already have the latest release of mods ({modsinfo.tag})') # NOTE: also runs if local version is newer than remote
                return

        return update
    finally:
        modsinfo.last_checked = current_time
        modsinfo.save()


def download_mods(
    update: Update,
    set_value:    Callable[[int], None] | None  = None,
    set_label:    Callable[[str], None] | None  = None,
    process:      Callable[[], None] | None     = None,
    was_canceled: Callable[[], bool] | None     = None
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

    if set_label:
        set_label("Extracting mods")
    if set_value:
        set_value(99)
    if process:
        process()

    try:
        extract(archive_path, config.mods_dir, 1, False)

        Modsinfo(
            tag=update.release.tag_name,
            digest=update.asset.digest,
            last_checked=datetime.now(timezone.utc),
        ).save()
    finally:
        archive_path.unlink()

    if set_value:
        set_value(100)

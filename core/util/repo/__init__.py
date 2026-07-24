from dataclasses import dataclass
from typing import Protocol

from packaging.version import Version


class Asset(Protocol):
    """An abstract class representing a release's asset."""

    name: str
    browser_download_url: str
    digest: str | None


class Release(Protocol):
    """An abstract class representing a repository's release"""

    tag_name: str
    assets: list[Asset]


@dataclass(frozen=True)
class Update:
    """A class that holds all required information to perform a self update"""

    asset: Asset
    release: Release
    version: Version

from typing import Iterable, NamedTuple, Protocol

from packaging import version


class Asset(Protocol):
    """An abstract class representing a release's asset."""
    name: str
    browser_download_url: str
    digest: str


class Release(Protocol):
    """An abstract class representing a repository's release"""
    tag_name: str
    assets: Iterable[Asset]


Update = NamedTuple('Update', release=Release, asset=Asset, version=version.Version)

from typing import Iterable, NamedTuple, Protocol

from packaging import version


# Specify the interfaces that the objects that `check_mods()` returns have
class Asset(Protocol):
    name: str
    browser_download_url: str
    digest: str


class Release(Protocol):
    tag_name: str
    assets: Iterable[Asset]


Update = NamedTuple('Update', release=Release, asset=Asset, version=version.Version)

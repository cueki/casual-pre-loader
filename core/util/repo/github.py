import logging
from operator import attrgetter
from typing import Generator, Optional

from github import Github
from github.GitRelease import GitRelease
from github.PaginatedList import PaginatedList
from github.Repository import Repository
from packaging import version

from core.util import all_predicates
from core.util.repo import Update

log = logging.getLogger()
client = Github()


is_draft = attrgetter("draft")
is_prerelease = attrgetter("prerelease")

is_not_draft = lambda x: not is_draft(x)
is_not_prerelease = lambda x: not is_prerelease(x)


def get_repo(repo: str) -> Repository:
    log.info(f"Retrieving repository ({repo})")
    return client.get_repo(repo)


# draft and prerelease may be a boolean or none.
# if true, it will add an inclusive filter
# if false, it will add an exclusive filter
# none has no effect
# NOTE:
# Information about published releases are available to everyone.
# Only users with push access will receive listings for draft releases.
# https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28
def get_releases(
    repo: str,
    prerelease: Optional[bool | None] = False,
    draft: Optional[bool | None] = False,
) -> PaginatedList[GitRelease]:
    _repo = get_repo(repo)

    _filter = []

    if prerelease:
        _filter.append(is_prerelease)
    elif prerelease is not None:
        _filter.append(is_not_prerelease)

    if draft:
        _filter.append(is_draft)
    elif draft is not None:
        _filter.append(is_not_draft)

    _filter = all_predicates(*_filter)

    log.info(f"Retrieving releases from {repo}")
    return filter(_filter, _repo.get_releases())


def get_releases_with_asset(
    repo: str,
    asset: str,
    prerelease: Optional[bool | None] = False,
    draft: Optional[bool | None] = False,
) -> Generator[Update, None, None]:
    for release in get_releases(repo, prerelease, draft):
        for _asset in release.assets:
            if _asset.name == asset:
                yield Update(release, _asset, version.parse(release.tag_name))
                break

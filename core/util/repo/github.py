import logging
from operator import attrgetter
from typing import Generator, Iterable, Optional

from github import Github
from github.GitRelease import GitRelease
from github.Repository import Repository
from packaging import version

from core.util import all_predicates
from core.util.repo import Update

log = logging.getLogger()
client = Github()


def get_repo(repo: str) -> Repository:
    """
    Retrieve information about a github repository.

    Args:
        repo: A github repository in the format of `"owner/repo"`.

    Returns:
        An object representing the repository.
    """

    log.debug(f"Retrieving repository ({repo})")
    return client.get_repo(repo)


def get_releases(
    repo: str,
    prerelease: Optional[bool | None] = False,
    draft: Optional[bool | None] = False,
) -> Iterable[GitRelease]:
    """
    Retrieve release information from a github repository.

    The `prerelease` and `draft` arguments take either a `bool` or `None`.
    `True` activates an inclusive filter, `False` activates an exclusive filter. `None` deactivates the filter.

    Information about published releases are available to everyone.
    Only users with push access will receive listings for draft releases.
    https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28

    Args:
        repo: A github repository in the format of `"owner/repo"`.
        prerelease: Whether to filter releases based on if they are prereleases.
        draft: Whether to filter releases based on if they are drafts.

    Returns:
        An Iterable of `github.GitRelease.GitRelease` objects.
    """

    repo = get_repo(repo)

    _filter = []

    is_draft = attrgetter("draft")
    is_prerelease = attrgetter("prerelease")

    if prerelease:
        _filter.append(is_prerelease)
    elif prerelease is not None:
        _filter.append(lambda x: not is_prerelease(x))

    if draft:
        _filter.append(is_draft)
    elif draft is not None:
        _filter.append(lambda x: not is_draft(x))

    _filter = all_predicates(*_filter)

    log.debug(f"Retrieving releases from https://github.com/{repo.full_name}")
    return filter(_filter, repo.get_releases())


def get_releases_with_asset(
    repo: str,
    asset: str,
    prerelease: Optional[bool | None] = False,
    draft: Optional[bool | None] = False,
) -> Generator[Update, None, None]:
    """
    Retrieve release information from a github repository, filtering out those without a certain asset.

    The `prerelease` and `draft` arguments take either a `bool` or `None`.
    `True` activates an inclusive filter, `False` activates an exclusive filter. `None` deactivates the filter.

    Information about published releases are available to everyone.
    Only users with push access will receive listings for draft releases.
    https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28

    Args:
        repo: A github repository in the format of `"owner/repo"`.
        asset: The name of an asset.
        prerelease: Whether to filter releases based on if they are prereleases.
        draft: Whether to filter releases based on if they are drafts.

    Returns:
        A Generator that yields `github.GitRelease.GitRelease` objects.
    """

    for release in get_releases(repo, prerelease, draft):
        for _asset in release.assets:
            if _asset.name == asset:
                yield Update(release, _asset, version.parse(release.tag_name))
                break

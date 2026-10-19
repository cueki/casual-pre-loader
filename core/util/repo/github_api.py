import logging
import re
from collections.abc import Generator, Iterable
from operator import attrgetter
from types import TracebackType

from github import Github
from github.GithubRetry import GithubRetry
from github.GitRelease import GitRelease
from github.Repository import Repository
from packaging.version import Version

# transitive through `PyGithub`, but importing the current file without `PyGithub` would error beforehand anyway
from urllib3 import Retry
from urllib3.connectionpool import ConnectionPool
from urllib3.exceptions import NameResolutionError
from urllib3.response import HTTPResponse

from core.util import all_predicates
from core.util.repo import Update

log = logging.getLogger(__name__)


# subclass `github.GithubRetry.GithubRetry` so that it short-circuits NameResolutionError
class GithubRetry(GithubRetry):
    def increment(  # type: ignore[override]
        self,
        method: str | None = None,
        url: str | None = None,
        response: HTTPResponse | None = None,  # type: ignore[override]
        error: Exception | None = None,
        _pool: ConnectionPool | None = None,
        _stacktrace: TracebackType | None = None,
    ) -> Retry:
        # This indicates that the user's system cannot use DNS to resolve github's IP
        # This can be caused by DNS being blocked or the lack of an internet connection
        # Retrying this does not make much sense
        if not response and isinstance(error, NameResolutionError):
            raise error

        # retry the request as usual
        return super().increment(method, url, response, error, _pool, _stacktrace)

gh: Github = Github(retry=GithubRetry(max_rate_limit_wait=5.0))

# https://github.com/PyGithub/PyGithub/issues/3561
logging.getLogger('github').handlers.clear()
logging.getLogger('github').setLevel(logging.NOTSET)

def get_repo(repo: str) -> Repository:
    '''
    Retrieve information about a github repository.

    Args:
        repo: A github repository in the format of `owner/repo`.

    Returns:
        An object representing the repository.
    '''

    log.debug(f'Retrieving repository ({repo})')

    return gh.get_repo(repo)


def get_releases(
    repo: str | Repository,
    prerelease: bool | None = False,
    draft: bool | None = False,
) -> Iterable[GitRelease]:
    '''
    Retrieve release information from a github repository.

    The `prerelease` and `draft` arguments take either a `bool` or `None`.
    `True` activates an inclusive filter, `False` activates an exclusive filter. `None` deactivates the filter.

    Information about published releases are available to everyone.
    Only users with push access will receive listings for draft releases.
    https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28

    Args:
        repo: A github repository in the format of `owner/repo`.
        prerelease: Whether to filter releases based on if they are prereleases.
        draft: Whether to filter releases based on if they are drafts.

    Returns:
        An Iterable of `github.GitRelease.GitRelease` objects.
    '''

    if not isinstance(repo, Repository):
        repo = get_repo(repo)

    _filter = []

    is_draft = attrgetter('draft')
    is_prerelease = attrgetter('prerelease')

    if prerelease:
        _filter.append(is_prerelease)
    elif prerelease is not None:
        _filter.append(lambda x: not is_prerelease(x))

    if draft:
        _filter.append(is_draft)
    elif draft is not None:
        _filter.append(lambda x: not is_draft(x))

    _filter = all_predicates(*_filter)

    log.debug(f'Retrieving releases from https://github.com/{repo.full_name}')
    return filter(_filter, repo.get_releases())


def get_releases_with_asset(
    repo: str,
    asset: str | re.Pattern,
    prerelease: bool | None = False,
    draft: bool | None = False,
) -> Generator[Update, None, None]:
    '''
    Retrieve release information from a github repository, filtering out those without a certain asset.

    The `prerelease` and `draft` arguments take either a `bool` or `None`.
    `True` activates an inclusive filter, `False` activates an exclusive filter. `None` deactivates the filter.

    Information about published releases are available to everyone.
    Only users with push access will receive listings for draft releases.
    https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28

    Args:
        repo: A github repository in the format of `owner/repo`.
        asset: The name of an asset or a regular expression that may match one.
        prerelease: Whether to filter releases based on if they are prereleases.
        draft: Whether to filter releases based on if they are drafts.

    Returns:
        A Generator that yields `github.GitRelease.GitRelease` objects.
    '''

    if isinstance(asset, re.Pattern):

        def test(name: str) -> bool:
            return asset.match(name) is not None
    else:

        def test(name: str) -> bool:
            return asset == name

    for release in get_releases(repo, prerelease=prerelease, draft=draft):
        for _asset in release.assets:
            if test(_asset.name):
                yield Update(_asset, release, Version(release.tag_name))
                break

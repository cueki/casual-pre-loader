from collections.abc import Iterable
from itertools import islice
from pathlib import Path, PurePath

# vertical lists get more room than inline ones
DEFAULT_LIST_LIMIT = 10
DEFAULT_INLINE_LIMIT = 5

# TODO: document
def abbrev_root(root: Path, path: Path, abbrev: str) -> PurePath:
    if path.is_relative_to(root):
        return PurePath(f'{{{abbrev}}}') / path.relative_to(root)
    return PurePath(path)


def _more(remaining: int, noun: str) -> str:
    '''
    Format the count of truncated items, e.g. "2 more VPK files" or "1 more VPK file".

    Args:
        remaining: How many items were left out.
        noun: Optional plural word for the items. When `remaining` is 1 a single
            trailing "s" is stripped, so irregular plurals like "directories"
            won't singularize correctly.

    Returns:
        The count, followed by the noun if one was given.
    '''

    if remaining == 1:
        noun = noun.removesuffix('s')
    return f"{remaining} more{f' {noun}' if noun else ''}"


def bullet_list(items: Iterable[object], limit: int = DEFAULT_LIST_LIMIT, *, noun: str = "", bullet: str = "• ") -> str:
    '''
    Format items one per line, truncating past `limit` with an "... and N more" line.

    Args:
        items: The things to list.
        limit: How many to show before truncating.
        noun: Optional plural word for the truncation line, e.g. "VPK files".
        bullet: Prefix for each line; pass "" for a plain newline-joined list.

    Returns:
        The formatted list, without a trailing newline.
    '''

    items = iter(items)
    lines = [f"{bullet}{item}" for item in islice(items, limit)]

    # whatever islice didn't take is the overflow
    remaining = sum(1 for _ in items)
    if remaining:
        lines.append(f"{bullet}... and {_more(remaining, noun)}")

    return "\n".join(lines)


def inline_list(items: Iterable[object], limit: int = DEFAULT_INLINE_LIMIT, *, noun: str = "", empty: str = "none") -> str:
    '''
    Format items as a comma-separated run, truncating past `limit` with "and N more".

    Args:
        items: The things to list.
        limit: How many to show before truncating.
        noun: Optional plural word for the truncation tail, e.g. "mods".
        empty: What to return when there is nothing to list.

    Returns:
        The formatted list, without a trailing newline.
    '''

    items = iter(items)
    shown = [str(item) for item in islice(items, limit)]
    if not shown:
        return empty

    text = ", ".join(shown)

    remaining = sum(1 for _ in items)
    if remaining:
        text += f", and {_more(remaining, noun)}"

    return text

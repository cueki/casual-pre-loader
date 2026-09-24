from collections.abc import Iterable

# vertical lists get more room than inline ones
DEFAULT_LIST_LIMIT = 10
DEFAULT_INLINE_LIMIT = 5


def _more(remaining: int, noun: str) -> str:
    # "2 more VPK files" / "1 more VPK file"
    if noun and remaining == 1 and noun.endswith('s'):
        noun = noun[:-1]
    return f"{remaining} more{f' {noun}' if noun else ''}"


def bullet_list(items: Iterable[object], limit: int = DEFAULT_LIST_LIMIT, *, bullet: str = "• ", noun: str = "") -> str:
    """
    Format items one per line, truncating past `limit` with an "... and N more" line.

    Args:
        items: The things to list.
        limit: How many to show before truncating.
        bullet: Prefix for each line; pass "" for a plain newline-joined list.
        noun: Optional plural word for the truncation line, e.g. "VPK files".

    Returns:
        The formatted list, without a trailing newline.
    """

    items = list(items)
    lines = [f"{bullet}{item}" for item in items[:limit]]

    remaining = len(items) - limit
    if remaining > 0:
        lines.append(f"{bullet}... and {_more(remaining, noun)}")

    return "\n".join(lines)


def inline_list(items: Iterable[object], limit: int = DEFAULT_INLINE_LIMIT, *, noun: str = "", empty: str = "none") -> str:
    """
    Format items as a comma-separated run, truncating past `limit` with "and N more".

    Args:
        items: The things to list.
        limit: How many to show before truncating.
        noun: Optional plural word for the truncation tail, e.g. "mods".
        empty: What to return when there is nothing to list.

    Returns:
        The formatted list.
    """

    items = list(items)
    if not items:
        return empty

    text = ", ".join(str(item) for item in items[:limit])

    remaining = len(items) - limit
    if remaining > 0:
        text += f", and {_more(remaining, noun)}"

    return text

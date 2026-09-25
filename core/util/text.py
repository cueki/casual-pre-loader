from pathlib import Path, PurePath


def abbrev_root(root: Path, path: Path, abbrev: str) -> PurePath:
    if path.is_relative_to(root):
        return PurePath(f'{{{abbrev}}}') / path.relative_to(root)
    return PurePath(path)

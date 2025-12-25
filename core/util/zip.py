import logging
from collections.abc import Callable
from pathlib import Path
from typing import Iterable, Optional, Union
from zipfile import Path as ZipFilePath
from zipfile import ZipFile

from core.util.file import PathLike, pathify

log = logging.getLogger()


# NOTE: Fuck this shit

def _sanitize_path(path: ZipFilePath) -> ZipFilePath:
    at = path.at.replace('/../', '/')
    if at.startswith('../'):
        at = at.ltrim('.')
    if at.endswith('/..'):
        at = at.rtrim('.')
    at = at.lstrip('/')

    return ZipFilePath(path.root.filename, at)


def _extract_member_to(member: ZipFilePath, path: Path, root: ZipFilePath) -> None:
    path /= _sanitize_path(member).relative_to(root)

    if member.is_dir():
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as fd:
            fd.write(member.read_bytes())

def _apply_filter(_filter: Callable, root: ZipFilePath):
    members = root.glob('**')
    _members = members
    if _filter:
        _members = tuple(filter(_filter(root), members))
    return _members

def _extract(
    zip_ref: ZipFile,
    dst: Optional[PathLike] = None,
    strip: Optional[int] = 0,
    noclobber: Optional[bool] = False,
    _filter: Optional[Callable[[str, list[str]], Iterable]] = None,
) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    if noclobber and len(tuple(dst.iterdir())):
        raise OSError(39, 'Directory not empty', str(dst))

    try:
        _root = ZipFilePath(zip_ref)
        if strip:
            roots = [_root]
            for i in range(strip):
                roots, _roots = [], roots.copy()

                for root in _roots:
                    roots += list(filter(lambda x: x.exists() and x.is_dir(), root.iterdir()))

                if not roots:
                    roots = _roots
                    break

            for root in roots:
                for member in _apply_filter(_filter, root):
                    _extract_member_to(member=member, path=dst, root=root)
        else:
            zip_ref.extractall(path=dst, members=map(lambda x: x.relative_to(_root) + (x.is_dir() and '/' or ''), _apply_filter(_filter, _root)))
    except Exception:
        log.exception(f'Error extracting {zip_ref.filename} -> {dst}')
        return
    finally:
        pass


def extract(
    zip_file: Union[PathLike, ZipFile],
    dst: Optional[PathLike] = None,
    strip: Optional[int] = 0,
    noclobber: Optional[bool] = False,
    _filter: Optional[Callable[[str, list[str]], Iterable]] = None,
) -> None:
    dst = pathify(dst)

    if isinstance(zip_file, ZipFile):
        _extract(zip_file, dst, strip, noclobber, _filter)

    else:
        with ZipFile(pathify(zip_file), 'r') as zip_ref:
            _extract(zip_ref, dst, strip, noclobber, _filter)

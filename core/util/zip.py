import logging
from collections.abc import Callable
from pathlib import Path
from typing import Iterable, Optional, Union
from zipfile import Path as ZipFilePath
from zipfile import ZipFile

from core.util.file import PathLike, pathify

log = logging.getLogger()


# NOTE: Fuck this shit

def _sanitize_path(member: ZipFilePath) -> None:
    member.at = member.at.replace('/../', '/')
    if member.at.startswith('../'):
        member.at = member.at.ltrim('.')
    if member.at.endswith('/..'):
        member.at = member.at.rtrim('.')
    member.at = member.at.lstrip('/')


def _extract_member_to(member: ZipFilePath, path: Path, root: ZipFilePath) -> None:
    _sanitize_path(member)
    path /= member.relative_to(root)

    if member.is_dir():
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as fd:
            fd.write(member.read_bytes())


def _apply_filter(_filter: Callable, root: ZipFilePath):
    members = root.glob('**')
    if _filter:
        members = filter(_filter(root), members)
    return members


def _extract(
    zip_ref: ZipFile,
    dst: Optional[PathLike] = None,
    strip: Optional[int] = 0,
    noclobber: Optional[bool] = False,
    _filter: Optional[Callable[[str, list[str]], Iterable]] = None,
) -> None:
    try:
        dst.mkdir(parents=True, exist_ok=True)
        if noclobber and len(tuple(dst.iterdir())):
            raise OSError(39, 'Directory not empty', str(dst))

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

        log.debug(f'Extracted {zip_ref.filename} -> {dst}')
    except Exception as e:
        raise Exception(f'Error extracting\n{zip_ref.filename} -> {dst}') from e


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

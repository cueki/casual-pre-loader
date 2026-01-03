import logging
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Optional, Sequence, Union

log = logging.getLogger()

PathLike = Union[str, os.PathLike]

#
# TODO: replace shutil with pathlib (except for rmtree) once we hit python 3.14 minimum version
#


def _get_next_new_file(file: Path) -> Path:
    while True:
        try:
            with file.open(os.O_CREAT | os.O_EXCL | os.O_WRONLY):
                return file
        except FileExistsError:
            file = file.with_name(file.name + '_')


def pathify(path: PathLike) -> os.PathLike:
    if not isinstance(path, os.PathLike):
        path = Path(path)
    return path.resolve()


def delete(file: PathLike, not_exist_ok: Optional[bool] = False) -> None:
    file = pathify(file)

    try:
        if not file.exists():
            if not_exist_ok:
                log.debug(f'Cannot delete {file} because it does not exist')
                return
            else:
                raise FileNotFoundError(f"[Errno 2] No such file or directory: {file}")

        is_file = file.is_file()

        if is_file:
            file.unlink()
        else:
            shutil.rmtree(file)

        log.debug(f'Deleted {is_file and "file" or "folder"} {file}')
    except Exception as e:
        raise Exception(f'Error deleting {file}') from e


def copy(
    src: PathLike,
    dst: PathLike,
    not_exist_ok: Optional[bool] = False,
    noclobber: Optional[bool] = False,
    ignore: Optional[Callable[[str, list[str]], Sequence]] = None,
) -> Path:
    src = pathify(src)
    dst = pathify(dst)

    try:
        if not src.exists():
            if not_exist_ok:
                log.debug(f'Cannot copy {src} -> {dst} as source does not exist')
                return
            else:
                raise FileNotFoundError(f"[Errno 2] No such file or directory: {src}")

        if noclobber is None:
            dst = _get_next_new_file(dst)
        elif noclobber and dst.exists():
            raise FileExistsError(f'[Errno 17] File exists: {dst}')

        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst, ignore, dirs_exist_ok=(not noclobber))

        log.debug(f'Copied {src} -> {dst}')
        return dst
    except Exception as e:
        raise Exception(f'Error copying {src} -> {dst}') from e


def move(
    src: PathLike,
    dst: PathLike,
    not_exist_ok: Optional[bool] = False,
    noclobber: Optional[bool] = False,
    ignore: Optional[Callable[[str, list[str]], Sequence]] = None,
) -> Path:
    src = pathify(src)
    dst = pathify(dst)

    try:
        if not src.exists():
            if not_exist_ok:
                log.debug(f'Cannot move {src} -> {dst} as source does not exist')
                return
            else:
                raise FileNotFoundError(f"[Errno 2] No such file or directory: {src}")

        if noclobber is None:
            dst = _get_next_new_file(dst)
        elif noclobber and dst.exists():
            raise FileExistsError(f'[Errno 17] File exists: {dst}')

        dst.parent.mkdir(parents=True, exist_ok=True)
        if ignore:
            copy(src, dst, False, noclobber, ignore)
            delete(src)
        else:
            shutil.move(src, dst)

        log.debug(f'Moved {src} -> {dst}')
        return dst
    except Exception as e:
        raise Exception(f'Error moving\n{src} -> {dst}') from e

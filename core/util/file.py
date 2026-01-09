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
    """
    Atomically create a new file, appending underscores to its name until valid, and return a path-like object representing it.

    Args:
        file: The base file name.
    Returns:
        A path-like object representing the new file.
    """

    while True:
        try:
            with file.open(os.O_CREAT | os.O_EXCL | os.O_WRONLY):
                return file
        except FileExistsError:
            file = file.with_name(file.name + '_')


def pathify(path: PathLike) -> os.PathLike:
    """
    Convert an object to an absolute path-like object.

    Args:
        path: A path-like object or something that can be converted to one (i.e. a string like `"/usr/bin/sh"`).

    Returns:
        An absolute path-like object.
    """

    if not isinstance(path, os.PathLike):
        path = Path(path)
    return path.resolve()


def delete(file: PathLike, not_exist_ok: Optional[bool] = False) -> None:
    """
    Delete a file or directory.

    Args:
        file: The file to delete.
        not_exist_ok: Do not throw an error if the file does not exist.
    """

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
) -> Path | None:
    """
    Copy a file or directory.

    Args:
        src: The source file.
        dst: The destination file.
        not_exist_ok: Do not throw an error if the source does not exist.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files).
        ignore: A callable that is passed to the `ignore` argument of `shutil.copytree()`.

    Returns:
        The destination path upon a successful copy.
    """

    src = pathify(src)
    dst = pathify(dst)

    if src == dst:
        log.debug(f'Tried copying {src} to itself, skipping...')
        return

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
) -> Path | None:
    """
    Move a file or directory.

    Args:
        src: The source file.
        dst: The destination file.
        not_exist_ok: Do not throw an error if the source does not exist.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files).
        ignore: A callable that is passed to the `ignore` argument of `shutil.copytree()`.

    Returns:
        The destination path upon a successful move.
    """

    src = pathify(src)
    dst = pathify(dst)

    if src == dst:
        log.debug(f'Tried moving {src} to itself, skipping...')
        return

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

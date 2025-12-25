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


def pathify(path: PathLike) -> os.PathLike:
    if not isinstance(path, os.PathLike):
        path = Path(path)
    return path


def delete(file: PathLike, not_exist_ok: bool = False) -> None:
    file = pathify(file)

    try:
        if not file.exists():
            raise FileNotFoundError

        is_file = file.is_file()

        if is_file:
            file.unlink()
        else:
            shutil.rmtree(file)

        log.debug(f"Deleted {is_file and 'file' or 'folder'} {file}")
    except FileNotFoundError:
        (not_exist_ok and log.warning or log.exception)(f"{file} does not exist and cannot be deleted")
    except Exception:
        log.exception(f"Error deleting {file}")


def copy(
    src: PathLike,
    dst: PathLike,
    noclobber: bool = False,
    ignore: Optional[Callable[[str, list[str]], Sequence]] = None,
) -> None:
    src = pathify(src)
    dst = pathify(dst)

    if noclobber and dst.exists():
        log.warning(f"Cannot copy because the destination already exists\n{src} -> {dst}")
        return

    try:
        if not src.exists():
            raise FileNotFoundError

        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst, ignore)

        log.debug(f"Copied {src} -> {dst}")
    except FileNotFoundError:
        log.exception(f"Cannot copy as source does not exist\n{src} -> {dst}")
    except Exception:
        log.exception(f"Error copying\n{src} -> {dst}")


def move(
    src: PathLike,
    dst: PathLike,
    noclobber: bool = False,
    ignore: Optional[Callable[[str, list[str]], Sequence]] = None,
) -> None:
    src = pathify(src)
    dst = pathify(dst)

    if noclobber and dst.exists():
        log.warning(f"Cannot move because the destination already exists\n{src} -> {dst}")
        return

    try:
        if not src.exists():
            raise FileNotFoundError

        dst.parent.mkdir(parents=True, exist_ok=True)
        if ignore:
            copy(src, dst, ignore)
            delete(src)
        else:
            shutil.move(src, dst)

        log.debug(f"Moved {src} -> {dst}")
    except FileNotFoundError:
        log.debug(f"Source does not exist and will not be moved\n{src} -> {dst}")
    except Exception:
        log.exception(f"Error moving\n{src} -> {dst}")

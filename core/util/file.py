import logging
import os
import shutil
import stat
from collections.abc import Callable, Sequence
from pathlib import Path

log = logging.getLogger()

#
# TODO: replace shutil with pathlib (except for rmtree) once we hit python 3.14 minimum version
#

type CopyFunction = Callable[[os.PathLike | str, os.PathLike | str], os.PathLike | str]  # return value is the same type as the second argument - i.e. passed-through


def _get_next_new_file(file: Path) -> Path:
    '''
    Atomically create a new file, appending underscores to its name until valid, and return a path-like object representing it.

    Args:
        file: The base file name.
    Returns:
        A path-like object representing the new file.
    '''

    while True:
        try:
            with file.open(os.O_CREAT | os.O_EXCL | os.O_WRONLY):
                return file
        except FileExistsError:
            file = file.with_name(file.name + '_')


def delete(file: Path, *, not_exist_ok: bool = False) -> None:
    '''
    Delete a file or directory.

    Args:
        file: The file to delete.
        not_exist_ok: Do not throw an error if the file does not exist.
    '''

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
    except Exception:
        log.exception(f'Error deleting {file}')
        raise


def _copy[**P](
    src: Path,
    dst: Path,
    noclobber: bool | None,
    not_exist_ok: bool,
    func: Callable[P, os.PathLike | str],
    # passed through to `func()`
    *args: P.args,
    **kwargs: P.kwargs,
) -> Path | None:
    if not src.exists():
        if not_exist_ok:
            log.debug(f'Cannot copy {src} -> {dst} as source does not exist')
            return
        else:
            raise FileNotFoundError(f"[Errno 2] No such file or directory: {src}")

    if src == dst:
        log.debug(f'Tried copying {src} to itself, skipping...')
        return

    try:
        if noclobber is None:
            dst = _get_next_new_file(dst)
        elif noclobber and dst.exists():
            raise FileExistsError(f'[Errno 17] File exists: {dst}')

        dst.parent.mkdir(parents=True, exist_ok=True)
        func(*args, src=src, dst=dst, **kwargs)

        log.debug(f'Copied {src} -> {dst}')
        return dst
    except Exception:
        log.exception(f'Error copying {src} -> {dst}')
        raise


def copy(
    src: Path,
    dst: Path,
    *,
    copy_function: CopyFunction = shutil.copy2,
    noclobber: bool | None = False,
    not_exist_ok: bool = False,
    # passed through to `copy_function()`
    follow_symlinks: bool | None = None,
) -> Path | None:
    '''
    Copy a file or directory.

    Args:
        src: The source file.
        dst: The destination file.
        not_exist_ok: Do not throw an error if the source does not exist.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files). A value of `None` tries to append a suffix to the filename.
        ignore: A callable that is passed to the `ignore` argument of `shutil.copytree()`.

    Returns:
        The destination path upon a successful copy.
    '''

    return _copy(
        src=src,
        dst=dst,
        noclobber=noclobber,
        not_exist_ok=not_exist_ok,
        func=copy_function,
        follow_symlinks=follow_symlinks,
    )


def copytree(
    src: Path,
    dst: Path,
    *,
    noclobber: bool | None = False,
    not_exist_ok: bool = False,
    # passed through to `shutil.copytree()`
    symlinks: bool | None = None,
    ignore: Callable[[str, list[str]], Sequence] | None = None,
    copy_function: CopyFunction = shutil.copy2,
    ignore_dangling_symlinks: bool | None = None,
) -> Path | None:
    return _copy(
        src=src,
        dst=dst,
        noclobber=noclobber,
        not_exist_ok=not_exist_ok,
        func=shutil.copytree,
        symlinks=symlinks,
        ignore=ignore,
        copy_function=copy_function,
        ignore_dangling_symlinks=ignore_dangling_symlinks,
        dirs_exist_ok=(not noclobber),
    )


def move(
    src: Path,
    dst: Path,
    not_exist_ok: bool = False,
    noclobber: bool | None = False,
    # passed through to `copytree()`
    ignore: Callable[[str, list[str]], Sequence] | None = None,
) -> Path | None:
    '''
    Move a file or directory.

    Args:
        src: The source file.
        dst: The destination file.
        not_exist_ok: Do not throw an error if the source does not exist.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files). A value of `None` tries to append a suffix to the filename.
        ignore: A callable that is passed to the `ignore` argument of `shutil.copytree()`.

    Returns:
        The destination path upon a successful move.
    '''

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
            copytree(
                src=src,
                dst=dst,
                not_exist_ok=False,
                noclobber=noclobber,
                ignore=ignore
            )
            delete(src)
        else:
            shutil.move(src, dst)

        log.debug(f'Moved {src} -> {dst}')
        return dst
    except Exception:
        log.exception(f'Error moving\n{src} -> {dst}')
        raise


def _format_mode(mode: int) -> str:
    '''
    Format a file permission mode into a human-readable representation (e.g. rwxrwxrwx).

    Args:
        mode: The mode bits to format.

    Returns:
        A human-readble representation of mode bits.
    '''

    ret = ''

    ret += 'r' if mode & stat.S_IRUSR else '-'
    ret += 'w' if mode & stat.S_IWUSR else '-'
    ret += 'x' if mode & stat.S_IXUSR else '-'

    ret += 'r' if mode & stat.S_IRGRP else '-'
    ret += 'w' if mode & stat.S_IWGRP else '-'
    ret += 'x' if mode & stat.S_IXGRP else '-'

    ret += 'r' if mode & stat.S_IROTH else '-'
    ret += 'w' if mode & stat.S_IWOTH else '-'
    ret += 'x' if mode & stat.S_IXOTH else '-'

    return ret


def _modeget(file: Path) -> tuple[int, str]:
    '''
    Retrieve a file's mode bits.

    Args:
        file: The file to operate on.
    Returns:
        A tuple of the file's mode bits and a human-readable representation.
    '''

    mode = file.stat().st_mode
    f_mode = _format_mode(mode)
    log.debug(f'got mode {f_mode} for {file}')
    return mode, f_mode


def modeset(file: Path, mode: int, not_exist_ok: bool = False) -> None:
    '''
    Change a file's mode bits.

    Args:
        file: The file to operate on.
        mode: The mode.
        not_exist_ok: Do not throw an error if the file does not exist.
    '''

    try:
        if not_exist_ok and not file.exists():
            log.debug(f'Cannot get/set mode for {file} because it does not exist')
            return

        file.chmod(mode)
        log.debug(f'set mode {_format_mode(mode)} for {file}')
    except Exception as e:
        raise Exception(f'unable to get/set mode for {file}') from e


def modeset_add(file: Path, mode: int, not_exist_ok: bool = False) -> None:
    '''
    Additively change a file's mode bits.

    Args:
        file: The file to operate on.
        mode: The mode bitwise OR with the file's mode.
        not_exist_ok: Do not throw an error if the file does not exist.
    '''

    try:
        if not_exist_ok and not file.exists():
            log.debug(f'Cannot get/set mode for {file} because it does not exist')
            return

        _mode, _ = _modeget(file)

        mode |= _mode
        file.chmod(mode)
        log.debug(f'set mode {_format_mode(mode)} for {file}')
    except Exception as e:
        raise Exception(f'unable to get/set mode for {file}') from e


def check_writable(file: Path) -> bool:
    '''
    Check if a file can be written to (not locked by another process).

    Args:
        file: The file to check.

    Returns:
        True if the file can be written to, False otherwise.
    '''

    try:
        with open(file, 'r+b'):
            pass
        return True
    except PermissionError:
        return False

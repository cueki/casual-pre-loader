import logging
import os
import shutil
import stat
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from _typeshed import BytesPath, StrOrBytesPath, StrPath

    # TODO: correct
    # taken from https://github.com/python/typeshed/blob/2e4d4dcf657f82305709bbe3e86bca4d27d4dd46/stdlib/builtins.pyi#L2035
    _StrOrBytesPathT = TypeVar('_StrOrBytesPathT', bound=StrOrBytesPath)
    _StrPathT = TypeVar('_StrPathT', bound=StrPath)
    _BytesPathT = TypeVar('_BytesPathT', bound=BytesPath)

    class CopyFunction(Protocol):
        @overload
        def __call__(self, src: StrPath, dst: _StrPathT, *, follow_symlinks: bool = True) -> _StrPathT | str: ...
        @overload
        def __call__(self, src: BytesPath, dst: _BytesPathT, *, follow_symlinks: bool = True) -> _BytesPathT | bytes: ...
        # def __call__(self, src: StrOrBytesPath, dst: StrOrBytesPathT, *, follow_symlinks: bool = True) -> StrOrBytesPathT | str | bytes: ...

    # type CopyFunction = Callable[[StrOrBytesPath, StrOrBytesPathT, bool], StrOrBytesPathT]   # return value is the same type as the second argument - i.e. passed-through
    # type CopyFunction = Callable[[StrPath, StrPath, bool], StrPath]  # return value is the same type as the second argument - i.e. passed-through

    # def type_check(func: CopyFunction) -> None: ...
    # type_check(shutil.copy2)
    # reveal_type(CopyFunction.__call__)
    # reveal_type(shutil.copy2)
    # assert_type(shutil.copy2, CopyFunction)


FILENAME_PADDING_CHAR = '_'
DEFAULT_COPY_FUNC = shutil.copy2
DEFAULT_COPYTREE_FUNC = shutil.copytree

log = logging.getLogger()

#
# TODO: replace shutil with pathlib (except for rmtree) once we hit python 3.14 minimum version
#


def _check_file_is_new(file: Path) -> None:
    # TODO: document
    with file.open('xb'):
        pass


def _check_dir_is_new(dir: Path) -> None:
    # TODO: document
    dir.mkdir(parents=True)


def _get_new_file(file: Path, is_file: bool) -> Path:
    '''
    Atomically create a new file or directory, appending underscores to its name until valid, and return a `Path` object representing it.

    Args:
        file: The base file name.
        is_file: True if a regular file should be created, false if a directory should be created.
    Returns:
        A `Path` object representing the new file or directory.
    '''

    func = _check_file_is_new if is_file else _check_dir_is_new
    while True:
        try:
            func(file)
            return file
        except FileExistsError:
            file = file.with_name(file.name + FILENAME_PADDING_CHAR)


def _check_src(file: Path, not_exist_ok: bool) -> bool | None:
    '''
    Check a source file.

    Args:
        file: The path to check.
        not_exist_ok: Whether to avoid raising an error if file does not exist.

    Returns:
        True, if file is a regular file; False, if it is a directory; None if it does not exist and not_exist_ok is True.
    '''

    if file.is_file():
        return True
    elif file.is_dir():
        return False
    elif not not_exist_ok:
        raise FileNotFoundError(f"[Errno 2] No such file or directory: {file}")


def _check_dst(src: Path, dst: Path, noclobber: bool | None, src_is_file: bool) -> Path:
    '''
    Check a destination file, changing it if required.

    Args:
        src: The relevant source paths
        dst: The destination path to check.
        noclobber: Whether to raise an error if dst already exists; tries to create a new destination if set to None.
    Returns:
        The resulting destination path.
    '''

    if noclobber and dst.exists():
        raise FileExistsError(f'[Errno 17] File exists: {dst}')
    elif noclobber is None:
        return _get_new_file(dst, src_is_file)
    return dst


# TODO: add windows-specific tests
def check_writable(file: Path) -> bool:
    '''
    Check if a file can be written to (not locked by another process).

    Args:
        file: The file to check.

    Returns:
        True if the file can be written to, False otherwise.
    '''

    try:
        with file.open('r+b'):
            pass
        return True
    except PermissionError:
        return False


def modeset(
        file: Path,
        mode: int,
        *,
        add: bool | None = None,
        not_exist_ok: bool = False,
        # passed through to `Path.chmod()`
        follow_symlinks: bool = True,
) -> int | None:
    '''
    Change a file's mode bits.

    Args:
        file: The file to operate on.
        mode: The mode bits.
        add: If True, adds the bits, if Talse, removes them. If None uses sets them as-is.
        not_exist_ok: Avoid rasing an error if the file does not exist.
    Return:
        The file's new mode bits.
    '''

    try:
        if add:
            mode |= stat.S_IMODE(file.stat().st_mode)
        elif add == False:
            mode = ~mode & stat.S_IMODE(file.stat().st_mode)

        file.chmod(mode, follow_symlinks=follow_symlinks)
    except FileNotFoundError:
        if not_exist_ok:
            log.debug(f'Cannot set mode for {file} because it does not exist')
            return
        raise

    log.debug(f'set mode {stat.filemode(mode)} for {file}')
    return mode


def delete(file: Path, *, not_exist_ok: bool = False) -> None:
    '''
    Delete a file or directory.

    Args:
        file: The file to delete.
        not_exist_ok: Do not throw an error if the file does not exist.
    '''

    is_file = _check_src(file=file, not_exist_ok=not_exist_ok)

    if is_file is None:
        log.debug(f'Cannot delete {file} because it does not exist')
        return

    if is_file:
        file.unlink()
    else:
        shutil.rmtree(file)
    log.debug(f'Deleted {is_file and 'file' or 'folder'} {file}')


def _copy(
    src: Path,
    dst: Path,
    func: Callable[[Path, Path], os.PathLike | str],
    *,
    noclobber: bool | None = False,
    not_exist_ok: bool = False,
    todir: bool = False,
) -> Path | None:
    is_file = _check_src(file=src, not_exist_ok=not_exist_ok)

    if is_file is None:
        log.debug(f'Cannot copy {src} -> {dst} because it does not exist')
        return

    dst = _check_dst(src=src, dst=dst, noclobber=noclobber, src_is_file=is_file)

    if todir:
        target_dst = dst

        if not is_file:
            dst /= src.name
    else:
        target_dst = dst.parent

    target_dst.mkdir(parents=True, exist_ok=True)
    dst = Path(func(src, dst))
    log.debug(f'Copied {src} -> {dst}')

    return dst


def copyfile(
    src: Path,
    dst: Path,
    *,
    noclobber: bool | None = False,
    not_exist_ok: bool = False,
    todir: bool = False,
    func: CopyFunction = DEFAULT_COPY_FUNC,
    # passed through to `func()`
    follow_symlinks: bool = True,
) -> Path | None:
    '''
    Copy a regular file.

    Args:
        src: The source file.
        dst: The destination file.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files). A value of `None` tries to append a suffix to the filename.
        not_exist_ok: Do not throw an error if the source does not exist.
        todir: Whether or not to treat dst as a dir to move src into.
    Returns:
        The destination path upon a successful copy.
    '''

    if src.is_dir():
        raise IsADirectoryError(src)

    func = partial(func, follow_symlinks=follow_symlinks)

    return _copy(
        src=src,
        dst=dst,
        func=func,
        noclobber=noclobber,
        not_exist_ok=not_exist_ok,
        todir=todir,
    )


def copytree(
    src: Path,
    dst: Path,
    *,
    noclobber: bool | None = False,
    not_exist_ok: bool = False,
    todir: bool = False,
    func: Callable = DEFAULT_COPYTREE_FUNC,
    # passed through to `func()`
    symlinks: bool = False,
    ignore: Callable[[str, list[str]], Sequence] | None = None,
    copy_function: CopyFunction = DEFAULT_COPY_FUNC,
    ignore_dangling_symlinks: bool = False,
) -> Path | None:
    '''
    Copy a directory and its contents.

    Args:
        src: The source file.
        dst: The destination file.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files). A value of `None` tries to append a suffix to the filename.
        not_exist_ok: Do not throw an error if the source does not exist.
        todir: Whether or not to treat dst as a dir to move src into.
    Returns:
        The destination path upon a successful copy.
    '''

    if src.is_file():
        raise NotADirectoryError(src)

    func = partial(func,
        symlinks=symlinks,
        ignore=ignore,
        copy_function=copy_function,
        ignore_dangling_symlinks=ignore_dangling_symlinks,
        dirs_exist_ok=(not noclobber),
    )

    return _copy(
        src=src,
        dst=dst,
        func=func,
        noclobber=noclobber,
        not_exist_ok=not_exist_ok,
        todir=todir,
    )


def move(
    src: Path,
    dst: Path,
    *,
    not_exist_ok: bool = False,
    noclobber: bool | None = False,
    todir: bool = False,
) -> Path | None:
    '''
    Move a file or directory to a new location.

    Args:
        src: The source file.
        dst: The destination file.
        not_exist_ok: Do not throw an error if the source does not exist.
        noclobber: Throw an error if the destination exists (i.e. do not overwrite files). A value of `None` tries to append a suffix to the filename.
        todir: Whether or not to treat dst as a dir to move src into.
    Returns:
        The destination path upon a successful move.
    '''

    is_file = _check_src(file=src, not_exist_ok=not_exist_ok)

    if is_file is None:
        log.debug(f'Cannot move {src} -> {dst} as source does not exist')
        return

    if not todir:
        dst = _check_dst(src=src, dst=dst, noclobber=noclobber, src_is_file=is_file)
        dst.parent.mkdir(parents=True, exist_ok=True)
    else:
        dst = _check_dst(src=src, dst=dst.parent, noclobber=noclobber, src_is_file=is_file) / dst.name
        dst.mkdir(parents=True, exist_ok=True)

    dst = Path(shutil.move(src, dst))
    log.debug(f'Moved {src} -> {dst}')

    return dst


def get_lockfile(file: PurePath) -> PurePath:
    return file.with_stem(file.stem + '.lock')

import errno
import random
import stat
import string
from collections.abc import Iterable
from pathlib import Path, PurePath

import pytest

from core.util.file import (
    DEFAULT_COPY_FUNC,
    DEFAULT_COPYTREE_FUNC,
    FILENAME_PADDING_CHAR,
    _check_dir_is_new,
    _check_dst,
    _check_file_is_new,
    _check_src,
    _copy,
    _get_new_file,
    check_writable,
    copyfile,
    copytree,
    delete,
    get_lockfile,
    modeset,
    move,
)

type FileState = bool | None
'''
True:  regular file (or symbolic link, pipe, etc. since most semantics do not differ all that much)
False: dir
None:  nonexistent
'''

# INFO: Keep in mind that any arguments that are simply passed through to other functions, such as those from from other libraries
# (e.g. `ignore` of `shutil.copytree()`), or called later (as `Callable` objects) or encapsulated, do not need to be tested.

dst_name = 'dst'
sample_file_size: int = 2 ** 10
modes: tuple[int, ...] = tuple(range(8**4))


def generate_random_text(length: int) -> str:
    return ''.join(random.choices(string.printable, k=length))


def generate_sample_file(path: Path, length: int = sample_file_size, other: str | Iterable[str] | None = None) -> str:
    cmp = (
        (lambda contents, other: contents == other)
        if isinstance(other, str) or not isinstance(other, Iterable)
        else lambda contents, other: contents in other
    )

    while True:
        contents = generate_random_text(length)
        if other is None or cmp(contents, other):
            break

    path.write_text(contents)
    return path.read_text()


def make_sample_dirs(path: Path, n: int = 8, depth: int = 3) -> list[tuple[Path, int, str]]:
    if depth == 0:
        raise ValueError('depth must be greater than 0')

    paths:  list[Path] = [path]
    _paths: list[Path] = []
    path.mkdir()
    for i in range(depth):
        for _path in paths:
            for j in range(n):
                dir = _path / str(j)
                dir.mkdir()
                _paths.append(dir)

        paths, _paths = _paths, []

    modes_iter = iter(modes)
    ret: list[tuple[Path, int, str]] = []
    for _path in paths:
        for i in range(n):
            file = _path / (str(i) + '.txt')
            mode = next(modes_iter)

            contents = generate_sample_file(file)
            file.chmod(mode=mode)
            ret.append((file.relative_to(path), mode, contents))

    return ret


@pytest.mark.parametrize('exists', [True, False])
def test__check_file_is_new(tmp_path: Path, exists: bool):
    file = tmp_path / 'file'

    if exists:
        file.touch()

        with pytest.raises(FileExistsError):
            assert _check_file_is_new(file) == None
    else:
        assert _check_file_is_new(file) == None


@pytest.mark.parametrize('exists', [True, False])
def test__check_dir_is_new(tmp_path: Path, exists: bool):
    file = tmp_path / 'file'

    if exists:
        file.mkdir()

        with pytest.raises(FileExistsError):
            assert _check_dir_is_new(file) == None
    else:
        assert _check_dir_is_new(file) == None


@pytest.mark.parametrize('exists', [True, False])
@pytest.mark.parametrize('is_file', [True, False])
def test__get_new_file(tmp_path: Path, is_file: bool, exists: bool):
    file = tmp_path / 'file.ext'

    if not exists:
        result = _get_new_file(file, is_file)

        assert result == file
    else:
        file.touch()

        result = _get_new_file(file, is_file)

        assert result != file
        assert result == file.with_name(file.name + FILENAME_PADDING_CHAR)

    assert (Path.is_file if is_file else Path.is_dir)(result)


@pytest.mark.parametrize('is_file', [True, False])
def test__get_new_file_repeat_and_charlimit(tmp_path: Path, is_file: bool):
    base_file = file = tmp_path / 'file.ext'

    file.touch()
    for i in range(2 ** 8):
        try:
           result = _get_new_file(file, is_file)
        except OSError as e:
            assert e.errno == errno.ENAMETOOLONG
            break

        assert result != file
        assert result == file.with_name(file.name + FILENAME_PADDING_CHAR)
        assert (Path.is_file if is_file else Path.is_dir)(result)

        assert result.name.startswith(base_file.name)
        suffix = result.name.removeprefix(base_file.name)
        assert suffix and all(c == FILENAME_PADDING_CHAR for c  in suffix)

        file  = result
    else:
        assert False


@pytest.mark.parametrize('state', ['file', 'dir', None])
@pytest.mark.parametrize('not_exist_ok', [True, False])
def test__check_src(tmp_path: Path, not_exist_ok: bool, state):
    file = tmp_path / 'file.ext'

    if not not_exist_ok and state is None:
        with pytest.raises(FileNotFoundError):
            _check_src(file, not_exist_ok)
        return

    if state == 'file':
        file.touch()
    elif state == 'dir':
        file.mkdir()

    result = _check_src(file, not_exist_ok)

    if state == 'file':
        assert result == True
    elif state == 'dir':
        assert result == False
    else:
        assert result == None


@pytest.mark.parametrize('dst_state', ['file', 'dir', None])
@pytest.mark.parametrize('src_is_file', [True, False])
@pytest.mark.parametrize('noclobber', [True, False, None])
def test__check_dst(tmp_path: Path, noclobber: bool | None, src_is_file: bool, dst_state):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if src_is_file:
        src.touch()
    else:
        src.mkdir()

    if dst_state == 'file':
        dst.touch()
    elif dst_state == 'dir':
        dst.mkdir()

    if noclobber and dst_state is not None:
        with pytest.raises(FileExistsError):
            _check_dst(src, dst, noclobber, src_is_file)
        return

    result = _check_dst(src, dst, noclobber, src_is_file)

    assert (result == dst) == (dst_state is None or noclobber is not None)


@pytest.mark.parametrize('writable', [True, False, None])
def test_check_writable(tmp_path: Path, writable: FileState):
    file = tmp_path / 'file'

    if writable:
        file.touch()
    elif writable == False:
        file.touch(mode=0o444)
    else:
        with pytest.raises(FileNotFoundError):
            check_writable(file)
        return

    assert check_writable(file) == writable


@pytest.mark.parametrize('add', [None, True, False])
def test_modeset(tmp_path: Path, add: bool | None):
    file = tmp_path / 'file'

    if add:
        start_mode = 0o0000
        _mode = 0o0400
        end_mode = start_mode | _mode
    elif add == False:
        start_mode = 0o0644
        _mode = 0o0444
        end_mode = ~_mode & start_mode
    else:
        start_mode = 0o0411
        _mode = end_mode = 0o0755

    file.touch(mode=start_mode)
    result = modeset(file, _mode, add=add)

    assert result == end_mode
    assert result == stat.S_IMODE(file.stat().st_mode)

    if add:
        with open(file, 'r'):
            pass
        with pytest.raises(PermissionError), open(file, 'w'):
            pass
    elif add == False:
        with open(file, 'w'):
            pass
        with pytest.raises(PermissionError), open(file, 'r'):
            pass
    else:
        with open(file, 'w'):
            pass
        with open(file, 'r'):
            pass


@pytest.mark.parametrize('not_exist_ok', [True, False])
def test_modeset_not_exist_ok(tmp_path: Path, not_exist_ok: bool):
    file = tmp_path / 'file'

    if not_exist_ok:
        assert modeset(file, 0o0000, not_exist_ok=not_exist_ok) == None
    else:
        with pytest.raises(FileNotFoundError):
            modeset(file, 0o0000, not_exist_ok=not_exist_ok)


def test_delete_file(tmp_path: Path):
    file = tmp_path / 'src.txt'

    generate_sample_file(file)
    assert delete(file) == None

    assert not file.exists()


def test_delete_dir(tmp_path: Path):
    file = tmp_path / 'src_dir'

    file.mkdir()
    assert delete(file) == None

    assert not file.exists()


@pytest.mark.parametrize('not_exist_ok', [False, True])
def test_delete_not_exist_ok(tmp_path: Path, not_exist_ok: bool):
    file = tmp_path / 'src_dir'

    if not_exist_ok:
        assert delete(file, not_exist_ok=not_exist_ok) == None
        return
    else:
        with pytest.raises(FileNotFoundError):
            delete(file, not_exist_ok=not_exist_ok)

    assert not file.exists()


# TODO: check for None return
@pytest.mark.parametrize('src_state', [True, False, None])
@pytest.mark.parametrize('todir', [False, True])
def test__copy(tmp_path: Path, todir: bool, src_state: FileState):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if src_state:
        src.touch()
        func = DEFAULT_COPY_FUNC
    elif src_state == False:
        src.mkdir()
        func = DEFAULT_COPYTREE_FUNC
    else:
        with pytest.raises(FileNotFoundError):
            _copy(src, dst, DEFAULT_COPY_FUNC, todir=todir)
        return

    result = _copy(src, dst, func, todir=todir)

    if todir:
        assert result == dst / src.name
    else:
        assert result == dst


@pytest.mark.parametrize('not_exist_ok', [False, True])
def test__copy_not_exist_ok(tmp_path: Path, not_exist_ok: bool):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if not_exist_ok:
        assert _copy(src, dst, DEFAULT_COPY_FUNC, not_exist_ok=not_exist_ok) == None
    else:
        with pytest.raises(FileNotFoundError):
            _copy(src, dst, DEFAULT_COPY_FUNC, not_exist_ok=not_exist_ok)


@pytest.mark.parametrize('src_state', [True, False, None])
def test_copyfile(tmp_path: Path, src_state: FileState):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if src_state:
        src_content = generate_sample_file(src)

        assert copyfile(src, dst) == dst
        assert dst.read_text() == src_content
    elif src_state == False:
        src.mkdir()

        with pytest.raises(IsADirectoryError):
            copyfile(src, dst)
    else:
        with pytest.raises(FileNotFoundError):
            copyfile(src, dst)


@pytest.mark.parametrize('src_state', [True, False, None])
def test_copytree(tmp_path: Path, src_state: FileState):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if src_state:
        src.touch()

        with pytest.raises(NotADirectoryError):
            copytree(src, dst)
    elif src_state == False:
        src.mkdir()
        src_file_content = generate_sample_file(src / 'file')

        assert copytree(src, dst) == dst
        assert (dst / 'file').read_text() == src_file_content
    else:
        with pytest.raises(FileNotFoundError):
            copyfile(src, dst)


@pytest.mark.parametrize('todir', [True, False])
@pytest.mark.parametrize('noclobber', [True, False, None])
def test_copytree_todir_noclobber(tmp_path: Path, noclobber: bool | None, todir: bool):
    src = tmp_path / 'src'
    dst = tmp_path / 'dst'

    if noclobber in (True, None):
        test__copy(tmp_path, todir, False)
        return

    src.mkdir()
    src_file_content = generate_sample_file(src / 'file')

    result = copytree(src, dst, noclobber=noclobber, todir=todir)

    if todir:
        dst = dst / src.name

    assert result == dst
    assert (dst / 'file').read_text() == src_file_content


def test_move_file(tmp_path: Path):
    src = tmp_path / 'src.txt'
    dst = tmp_path / 'dst'

    src_contents = generate_sample_file(src)
    result = move(src, dst)

    assert result == dst

    assert not src.exists()

    assert result.is_file()
    assert result.read_text() == src_contents


def test_move_dir(tmp_path: Path):
    src = tmp_path / 'src_dir'
    dst = tmp_path / dst_name

    src.mkdir()
    result  = move(src, dst)

    assert result == dst

    assert not src.exists()

    assert result.is_dir()


def test_move_dir_and_contents(tmp_path: Path):
    src = tmp_path / 'src_dir'
    dst = tmp_path / dst_name

    sample_files = make_sample_dirs(src)
    result = move(src, dst)

    assert result == dst

    assert not src.exists()

    assert result.is_dir()
    for file, mode, contents in sample_files:
        file = result / file

        _mode = file.stat().st_mode
        assert mode == stat.S_IMODE(_mode)
        assert stat.S_ISREG(_mode)

        file.chmod(mode=0o644)
        assert contents == file.read_text()


def test_move_to_self(tmp_path: Path):
    src = tmp_path / 'src.txt'
    dst = src

    src_contents = generate_sample_file(src)
    mtime = src.stat().st_mtime
    result = move(src, dst)

    assert result == src

    assert src.exists()
    assert src.stat().st_mtime == mtime
    assert src.read_text() == src_contents


def test_move_into_dir(tmp_path: Path):
    src = tmp_path / 'src.txt'
    dst = tmp_path / dst_name

    dst.mkdir()

    src_contents = generate_sample_file(src)
    result = move(src, dst)

    assert result == dst / src.name

    assert not src.exists()

    assert result.is_file()
    assert result.read_text() == src_contents


@pytest.mark.parametrize('not_exist_ok', [False, True])
def test_move_not_exist_ok(tmp_path: Path, not_exist_ok: bool):
    src = tmp_path / 'not_exist'
    dst = tmp_path / dst_name

    if not_exist_ok:
        assert move(src, dst, not_exist_ok=not_exist_ok) == None
        return
    else:
        with pytest.raises(FileNotFoundError):
            move(src, dst, not_exist_ok=not_exist_ok)

    assert not dst.exists()
    assert not src.exists()


@pytest.mark.parametrize('dst_exists', [False, True])
@pytest.mark.parametrize('noclobber', [False, True, None])
def test_move_noclobber(tmp_path: Path, noclobber: bool | None, dst_exists: bool):
    src = tmp_path / 'src.txt'
    dst = tmp_path / dst_name

    src_contents = generate_sample_file(src)

    if not dst_exists:
        result = move(src, dst, noclobber=noclobber)

        assert result == dst

        assert not src.exists()

        assert dst.exists()
        assert dst.read_text() == src_contents

        return

    dst_contents = src_contents
    while dst_contents == src_contents:
        dst_contents = generate_sample_file(dst)

    if noclobber:
        with pytest.raises(FileExistsError):
            move(src, dst, noclobber=noclobber)

        assert dst.exists()
        assert dst.read_text() != src_contents

        assert src.exists()
        assert src.read_text() == src_contents

        return

    result = move(src, dst, noclobber=noclobber)

    assert dst.exists()

    assert not src.exists()

    if noclobber is None:
        assert result is not None
        assert result != dst

        assert result.parent == dst.parent

        assert dst.read_text() == dst_contents

        assert not src.exists()

        assert result.exists()
        assert result.read_text() == src_contents
    else:
        assert result == dst

        assert dst.read_text() == src_contents


@pytest.mark.parametrize('todir', [False, True])
def test_move_todir(tmp_path: Path, todir: bool):
    src = tmp_path / 'src.txt'
    dst = tmp_path / dst_name

    src_contents = generate_sample_file(src)

    result = move(src, dst, todir=todir)

    if todir:
        assert result is not None
        assert result.parent == dst

        assert dst.is_dir()

        assert not src.exists()

        assert result.is_file()
        assert result.read_text() == src_contents
    else:
        assert result == dst

        assert not src.exists()

        assert result.is_file()
        assert result.read_text() == src_contents

# TODO: test for no ext
# TODO: use fuzzing??
def test_get_lockfile():
    file = PurePath(generate_random_text(20)+ '.ext')

    result = get_lockfile(file)

    assert result != file
    assert result.with_stem(file.stem) == file
    assert result.stem == file.stem + '.lock'

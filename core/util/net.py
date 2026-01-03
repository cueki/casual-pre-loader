import logging
import socket
import urllib.request
from pathlib import Path
from typing import Optional

from core.folder_setup import folder_setup
from core.util.file import move

log = logging.getLogger()


def download_file(url: str, path: Path, timeout: Optional[int] = None, reporthook=None) -> None:
    old_timeout = socket.getdefaulttimeout()

    try:
        socket.setdefaulttimeout(timeout)

        tmp_path = folder_setup.temp_download_dir / f"{path.name}"

        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, tmp_path, reporthook)

        move(tmp_path, path)

    except Exception as e:
        raise Exception(f'Error downloading file\n{url} -> {path}') from e
    finally:
        socket.setdefaulttimeout(old_timeout)


def download_reporthook(set_value = None, set_label = None, process = None, was_canceled = None):
    def func(block_num: int, block_size: float, total_size: float):
        if was_canceled and was_canceled():
            raise Exception('Download cancelled by user')

        if total_size > 0:
            percent = int((block_num * block_size / total_size) * 100)
            set_value(min(percent, 99))

            if process:
                process()

    return func

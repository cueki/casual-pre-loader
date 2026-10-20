#!/usr/bin/env python3

import logging
from sys import platform

from core.util.file import delete
from core.util.text import notimplemented_msg


#TODO: move to `gui/` and reorganize
def gui() -> int:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QPixmap
    from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

    from core.auto_updater import check_for_updates
    from core.backup_manager import prepare_runtime_environment
    from core.config import config
    from core.settings import settings
    from gui.first_time_setup import run_first_time_setup
    from gui.main_window import ParticleManagerGUI
    from gui.theme import GLOBAL_STYLESHEET
    from gui.update_dialog import show_update_dialog

    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    setup_error = prepare_runtime_environment()
    if setup_error:
        QMessageBox.critical(None, 'Preloader Setup Failed', setup_error)
        logging.critical('Preloader Setup Failed')
        return 1

    # first-time setup
    if settings.done_initial_setup:
        tf_dir = settings.game_path
    else:
        tf_dir = run_first_time_setup() # may exit

    # splash screen
    splash_pixmap = QPixmap(str(config.install_dir / 'gui/icons/cueki_splash.png'))
    scaled_pixmap = splash_pixmap.scaled(
        int(splash_pixmap.width() * 0.75),
        int(splash_pixmap.height() * 0.75),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    splash = QSplashScreen(scaled_pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.FramelessWindowHint)
    splash.show()

    window = ParticleManagerGUI(tf_dir)

    if config.update and settings.done_initial_setup:
        updates = check_for_updates()

        # TODO: update this once we can update multiple at a time
        if updates and settings.should_show_update_dialog(updates[0].version):
            splash.hide()
            show_update_dialog(updates) # NOTE: may eventually re-execute the interpreter
            splash.show()

    # set icon for Windows
    if platform == 'win32':
        import ctypes
        my_app_id = 'cool.app.id.yes'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
        window.setWindowIcon(QIcon(str(config.install_dir / 'gui/icons/cueki_icon.svg')))
    elif platform == 'linux':
        window.setWindowIcon(QIcon(str(config.install_dir / 'gui/icons/cueki_icon.svg')))
    else:
        logging.warning(notimplemented_msg('set an icon'))

    splash.finish(window)
    window.show()

    app.exec()
    delete(config.temp_dir, not_exist_ok=True)
    return 0

def main():
    import datetime

    from platformdirs import PlatformDirs
    from rich.logging import RichHandler
    from rich.traceback import install

    from core.constants import PROGRAM_AUTHOR, PROGRAM_NAME

    def fmt_time(t: datetime.datetime) -> str: # `logging` uses naive datetime objects by default (i.e. no tzdata)
        return t.astimezone().strftime('[%Y-%m-%d %H:%M:%S %z]')

    log = logging.getLogger()

    handler = RichHandler(rich_tracebacks=True)
    handler.setFormatter(logging.Formatter(datefmt=fmt_time))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    # TODO: Find a way to display bad exit messages with GUI popups when running the program's GUI.
    # This would require the program init to have zero side effects, i.e. not write to any non-instance-specific files on disk (log files and config files)

    if platform == 'win32':
        import ctypes

        if ctypes.windll.shell32.IsUserAnAdmin():
            log.critical('This program should not be run as administrator')
            raise SystemExit(1)
    elif platform == 'linux':
        import os

        if os.getuid() == 0:
            log.critical('This program should not be run as root')
            raise SystemExit(1)
    else:
        raise NotImplementedError(notimplemented_msg('determine privileges'))

    dirs = PlatformDirs(PROGRAM_NAME, PROGRAM_AUTHOR, ensure_exists=True)

    # TODO: see if using `filelock`/`portalocker` makes sense
    try:
        lock_file = dirs.place_runtime_file(f'{PROGRAM_NAME}.lock')
        log.info(f'lock file is {lock_file}') # TODO: make debug

        global lock_fd # avoid GC until exit
        lock_fd = open(lock_file, mode='a+b', buffering=0)  # ruff: ignore[open-file-with-context-handler]

        if platform == 'win32':
            import msvcrt

            lock_fd.seek(0)
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1) # lock one byte at the beginning of the file
        elif platform == 'linux':
            import fcntl

            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            raise NotImplementedError(notimplemented_msg('acquire file locks'))
    except OSError:
        log.critical('Another instance is already running.', exc_info=True)
        raise SystemExit(1)

    from core.config import config, subcommand

    install(show_locals=config.verbose, max_frames=(not config.verbose and 100 or 0)) # install the rich traceback handler
    log.setLevel(config.verbose and logging.DEBUG or logging.INFO)

    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    log.addHandler(logging.FileHandler(config.log_file, mode='a', encoding='utf-8'))

    raise SystemExit(subcommand(config))

if __name__ == '__main__':
    main()

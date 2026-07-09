#!/usr/bin/env python3

import logging
from sys import platform

from core.util.file import delete
from core.version import VERSION


def log_start() -> None:
    from core.config import config

    logging.info(f'Version {VERSION} on {platform} {"(portable)" if config.portable else ""}')
    logging.info(f'Application files are located in {config.install_dir}')
    logging.info(f'Project files are written to {config.project_dir}')
    logging.info(f'Settings files are in {config.settings_dir}')
    logging.info(f'Log is written to {config.log_file}')

    logging.debug('DEBUG OUTPUT HAS BEEN ENABLED')


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
        QMessageBox.critical(None, "Preloader Setup Failed", setup_error)
        return 1

    # first-time setup
    if settings.done_initial_setup:
        tf_dir = settings.game_path
    else:
        tf_dir = run_first_time_setup() # may exit

    # splash screen
    splash_pixmap = QPixmap('gui/icons/cueki_splash.png')
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
        logging.warning(f"We don't know how to set an icon for platform type: {platform}")

    splash.finish(window)
    window.show()

    app.exec()
    delete(config.temp_dir, not_exist_ok=True)
    return 0

def main():
    from rich.logging import RichHandler
    from rich.traceback import install

    logger = logging.getLogger()

    handler = RichHandler(rich_tracebacks=True)
    handler.setFormatter(logging.Formatter(datefmt='[%Y-%m-%d %H:%M:%S]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    from core.config import config, subcommand

    install(show_locals=config.verbose, max_frames=(not config.verbose and 100 or 0 )) # install the rich traceback handler

    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.addHandler(logging.FileHandler(config.log_file, mode='a', encoding='utf-8'))
    logger.setLevel(config.verbose and logging.DEBUG or logging.INFO),

    raise SystemExit(subcommand(config))

if __name__ == "__main__":
    main()

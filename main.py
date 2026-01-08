#!/usr/bin/env python3

import datetime
import logging
from sys import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

from core.auto_updater import check_for_updates
from core.backup_manager import prepare_working_copy
from core.folder_setup import folder_setup
from core.util.file import copy, delete
from core.version import VERSION
from gui.first_time_setup import run_first_time_setup
from gui.main_window import ParticleManagerGUI
from core.settings import SettingsManager
from gui.update_dialog import show_update_dialog

log = logging.getLogger()

def main():
    log.info(f'Version {VERSION} on {platform} {"(portable)" if folder_setup.portable else ""}')
    log.info(f'Application files are located in {folder_setup.install_dir}')
    log.info(f'Project files are written to {folder_setup.project_dir}')
    log.info(f'Settings files are in {folder_setup.settings_dir}')
    log.info(f'Log is written to {folder_setup.log_file}')

    copy(folder_setup.install_dir / "backup", folder_setup.project_dir / "backup", noclobber=False)

    app = QApplication([])
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    # first-time setup
    tf_directory = None
    if SettingsManager.is_first_time_setup():
        tf_directory = run_first_time_setup()
        if tf_directory is None:
            # user cancelled setup
            return

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

    prepare_working_copy()

    window = ParticleManagerGUI(tf_directory)

    if not SettingsManager.is_first_time_setup() and folder_setup.portable:
        settings_manager = SettingsManager()

        updates = check_for_updates()

        # TODO: update this once we can update multiple at a time
        if updates and settings_manager.should_show_update_dialog(updates[0].release.tag_name.lstrip('v')):
            splash.hide()
            show_update_dialog(updates) # NOTE: may eventually re-execute the interpreter
            splash.show()

    # set icon for Windows
    if platform == 'win32':
        import ctypes
        my_app_id = 'cool.app.id.yes'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
        window.setWindowIcon(QIcon(str(folder_setup.install_dir / 'gui/icons/cueki_icon.svg')))
    elif platform == 'linux':
        window.setWindowIcon(QIcon(str(folder_setup.install_dir / 'gui/icons/cueki_icon.svg')))
    else:
        log.warning(f"We don't know how to set an icon for platform type: {platform}")

    splash.finish(window)
    window.show()

    app.exec()
    delete(folder_setup.temp_dir, not_exist_ok=True)

def run():
    import core.migrations

    core.migrations.migrate()
    del core.migrations

    try:
        from rich.logging import RichHandler
        from rich.traceback import install

        stream_handler = RichHandler(rich_tracebacks=True)
        install(show_locals=True)
    except ModuleNotFoundError:
        stream_handler = logging.StreamHandler()

    def fmt_time(t: datetime.datetime) -> str:
        return t.strftime('[%Y-%m-%d %H:%M:%S]')

    folder_setup.log_file.parent.mkdir(parents=True, exist_ok=True)

    verbose = False
    logging.basicConfig(
        level=(verbose and logging.DEBUG or logging.INFO),
        format='%(message)s',
        datefmt=fmt_time,
        handlers=[logging.FileHandler(folder_setup.log_file, mode='a', encoding='utf-8'), stream_handler],
    )

    main()

if __name__ == "__main__":
    run()

#!/usr/bin/env python3

import datetime
import logging
from sys import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

from core.auto_updater import check_for_updates_sync
from core.backup_manager import prepare_working_copy
from core.folder_setup import folder_setup
from gui.first_time_setup import check_first_time_setup, run_first_time_setup
from gui.main_window import ParticleManagerGUI
from gui.settings_manager import SettingsManager
from gui.update_dialog import show_update_dialog

log = logging.getLogger()

def main():
    log.info(f'We{" ARE " if folder_setup.portable else " are NOT "}running a portable install')
    log.info(f'Application files are located in {folder_setup.install_dir}')
    log.info(f'Project files are written to {folder_setup.project_dir}')
    log.info(f'Settings files are in {folder_setup.settings_dir}')

    app = QApplication([])
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    # first-time setup
    tf_directory = None
    if check_first_time_setup():
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

    # cleanup old updater, old structure, and temp folders
    folder_setup.cleanup_old_updater()
    folder_setup.cleanup_old_structure()
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()
    prepare_working_copy()

    window = ParticleManagerGUI(tf_directory)

    # check for updates after first-time setup is complete (only for portable)
    update_info = None
    if not check_first_time_setup() and folder_setup.portable:
        settings_manager = SettingsManager()

        update_info = check_for_updates_sync()

        if update_info and settings_manager.should_show_update_dialog(update_info["version"]):
            splash.hide()
            show_update_dialog(update_info)
            splash.show()

    # pass update info to window for display
    if update_info:
        window.update_info = update_info

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
    folder_setup.cleanup_temp_folders()

def run():
    try:
        from rich.logging import RichHandler

        stream_handler = RichHandler(rich_tracebacks=True)
    except ModuleNotFoundError:
        stream_handler = logging.StreamHandler()

    def fmt_time(t: datetime.datetime) -> str:
        return t.strftime('[%Y-%m-%d %H:%M:%S]')

    verbose = False
    logging.basicConfig(
        level=(verbose and logging.DEBUG or logging.INFO),
        format='%(message)s',
        datefmt=fmt_time,
        handlers=[logging.FileHandler(folder_setup.project_dir / 'casual-pre-loader.log', mode='a', encoding='utf-8'), stream_handler],
    )

    main()

if __name__ == "__main__":
    run()

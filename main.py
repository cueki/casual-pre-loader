#!/usr/bin/env python3

from sys import platform
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from gui.main_window import ParticleManagerGUI
from gui.first_time_setup import check_first_time_setup, run_first_time_setup
from core.folder_setup import folder_setup
from core.backup_manager import prepare_working_copy
from core.auto_updater import check_for_updates_sync
from gui.update_dialog import show_update_dialog
from gui.settings_manager import SettingsManager


def main():
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
    splash_pixmap = QPixmap('gui/cueki_icon.png')
    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.FramelessWindowHint)
    splash.show()

    # cleanup old updater and temp folders
    folder_setup.cleanup_old_updater()
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()
    splash.showMessage("Preparing working copy...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                       Qt.GlobalColor.white)
    prepare_working_copy()

    window = ParticleManagerGUI(tf_directory)
    
    # check for updates after first-time setup is complete (only for portable)
    update_info = None
    if not check_first_time_setup() and folder_setup.portable:
        settings_manager = SettingsManager()

        splash.showMessage("Checking for updates...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)
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
        window.setWindowIcon(QIcon(str(folder_setup.install_dir / 'gui/cueki_icon.ico')))
    elif platform == 'linux':
        window.setWindowIcon(QIcon(str(folder_setup.install_dir / 'gui/cueki_icon.png')))
    else:
        print(f"[Warning] We don't know how to set an icon for platform type: {platform}")

    splash.finish(window)
    window.show()

    app.exec()
    folder_setup.cleanup_temp_folders()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from sys import platform
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
from gui.main_window import ParticleManagerGUI
from gui.setup import initial_setup
from gui.first_time_setup import (check_first_time_setup, run_first_time_setup, should_install_mods_zip,
                                  should_uninstall_mods_zip, uninstall_mods_zip)
from core.folder_setup import folder_setup
from core.backup_manager import prepare_working_copy
from core.auto_updater import check_for_updates_sync
from gui.update_dialog import show_update_dialog


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

    # handle included mods - install or uninstall based on settings
    should_install = should_install_mods_zip()
    should_uninstall = should_uninstall_mods_zip()
    
    if should_install:
        splash.showMessage("Installing included mods...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)
        initial_setup((folder_setup.install_dir / 'mods.zip', folder_setup.mods_dir))
    elif should_uninstall:
        splash.showMessage("Removing included mods...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)
        uninstall_mods_zip()
    else:
        splash.showMessage("Included mods up to date...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)

    # temp
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()
    splash.showMessage("Preparing working copy...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                       Qt.GlobalColor.white)
    prepare_working_copy()

    # check for updates
    splash.showMessage("Checking for updates...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                       Qt.GlobalColor.white)
    update_info = check_for_updates_sync()
    
    # show update dialog if update is available
    if update_info:
        splash.hide()  # hide splash while showing dialog
        show_update_dialog(update_info)
        splash.show()  # show splash again after dialog

    window = ParticleManagerGUI(tf_directory, update_info)

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

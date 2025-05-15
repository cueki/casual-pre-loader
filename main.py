#!/usr/bin/env python3

from sys import platform
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from gui.main_window import ParticleManagerGUI
from gui.setup import initial_setup
from core.folder_setup import folder_setup
from backup.backup_manager import prepare_working_copy


def main():
    app = QApplication([])
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    # splash screen
    splash_pixmap = QPixmap('gui/cueki_icon.png')
    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.FramelessWindowHint)
    splash.show()

    # initial setup
    if not folder_setup.mods_dir.exists():
        splash.showMessage("Initial setup...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)
        initial_setup((folder_setup.install_dir / 'mods.zip', folder_setup.mods_dir))

    # temp
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()
    splash.showMessage("Preparing working copy...",
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                       Qt.GlobalColor.white)
    prepare_working_copy()

    window = ParticleManagerGUI()

    # set icon for Windows
    if platform == 'win32':
        import ctypes
        my_app_id = 'cool.app.id.yes'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
    window.setWindowIcon(QIcon('gui/cueki_icon.ico'))

    splash.finish(window)
    window.show()

    app.exec()
    folder_setup.cleanup_temp_folders()


if __name__ == "__main__":
    main()

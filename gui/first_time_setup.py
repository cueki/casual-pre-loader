import os
import json
import socket
import shutil
import zipfile
import urllib.request
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QFileDialog, QMessageBox, QGroupBox, QTabWidget,
                             QWidget, QFrame, QProgressDialog, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from core.folder_setup import folder_setup
from core.constants import CUEKI_MODS_URL
from gui.settings_manager import SettingsManager, validate_tf_directory, auto_detect_tf2


class FirstTimeSetupDialog(QDialog):
    setup_completed = pyqtSignal(str)  # emits the selected tf/ directory path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_status_label = None
        self.settings_import_edit = None
        self.validation_label = None
        self.browse_button = None
        self.tf_path_edit = None
        self.finish_button = None
        self.tf_directory = ""
        self.import_settings_path = ""
        self.settings_manager = SettingsManager()
        self.import_mods_path = ""

        self.setWindowTitle("First Time Setup")
        self.setMinimumSize(750, 500)
        self.setModal(True)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # title
        welcome_label = QLabel("Welcome to the casual pre-loader!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)

        # tab widgets
        tab_widget = QTabWidget()
        tf_tab = self.create_tf_directory_tab()
        tab_widget.addTab(tf_tab, "TF2 Directory")
        import_tab = self.create_import_tab()
        tab_widget.addTab(import_tab, "Import Previous Settings")

        layout.addWidget(tab_widget)

        # separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.finish_button = QPushButton("Finish Setup")
        self.finish_button.clicked.connect(self.finish_setup)
        self.finish_button.setEnabled(False)
        button_layout.addWidget(self.finish_button)

        layout.addLayout(button_layout)

    def create_tf_directory_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        instructions = QLabel(
            "Please select your Team Fortress 2 'tf' directory.\n"
            "This is usually located in:\n"
            "• Steam/steamapps/common/Team Fortress 2/tf/\n"
            "• ~/.steam/steam/steamapps/common/Team Fortress 2/tf/ (Linux)"
        )
        instructions.setWordWrap(True)
        instructions.setMargin(10)
        layout.addWidget(instructions)

        # tf/ directory group
        tf_group = QGroupBox("tf/ Directory")
        tf_layout = QVBoxLayout()

        # directory selection
        dir_layout = QHBoxLayout()
        self.tf_path_edit = QLineEdit()
        self.tf_path_edit.setReadOnly(True)
        self.tf_path_edit.setPlaceholderText("Select your tf/ directory...")
        self.tf_path_edit.textChanged.connect(self.validate_setup)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_tf_dir)

        dir_layout.addWidget(self.tf_path_edit)
        dir_layout.addWidget(self.browse_button)
        tf_layout.addLayout(dir_layout)

        # auto-detect button
        auto_detect_button = QPushButton("Auto-Detect TF2 Installation")
        auto_detect_button.clicked.connect(self.auto_detect_tf2_dir)
        tf_layout.addWidget(auto_detect_button)

        # validation
        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        tf_layout.addWidget(self.validation_label)

        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)

        # mods download group
        layout.addWidget(mods_download_group(self))

        layout.addStretch()
        return tab

    def create_import_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        instructions = QLabel(
            "If you have previously used this preloader, you can import your settings.\n"
            "Select your app_settings.json file and the mods folder will be imported automatically.\n"
            "This is optional - you can skip this step if this is your first time using the preloader."
        )
        instructions.setWordWrap(True)
        instructions.setMargin(10)
        layout.addWidget(instructions)

        # import settings group
        import_group = QGroupBox("Import Previous Installation")
        import_layout = QVBoxLayout()

        # settings file import
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Settings file (app_settings.json):"))
        self.settings_import_edit = QLineEdit()
        self.settings_import_edit.setReadOnly(True)
        self.settings_import_edit.setPlaceholderText("Optional: Select app_settings.json...")

        settings_browse_button = QPushButton("Browse")
        settings_browse_button.clicked.connect(self.browse_settings_file)

        settings_layout.addWidget(self.settings_import_edit)
        settings_layout.addWidget(settings_browse_button)
        import_layout.addLayout(settings_layout)

        # clear imports button
        clear_imports_button = QPushButton("Clear Import Selections")
        clear_imports_button.clicked.connect(self.clear_import_selections)
        import_layout.addWidget(clear_imports_button)

        import_group.setLayout(import_layout)
        layout.addWidget(import_group)

        # import status
        self.import_status_label = QLabel("")
        self.import_status_label.setWordWrap(True)
        layout.addWidget(self.import_status_label)

        layout.addStretch()
        return tab

    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_directory = directory
            self.tf_path_edit.setText(directory)
            self.validate_tf_directory()

    def browse_settings_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select app_settings.json", "app_settings.json",
            "App Settings (app_settings.json);;JSON files (*.json);;All files (*)"
        )
        if file_path:
            self.import_settings_path = file_path
            self.settings_import_edit.setText(file_path)

            settings_path = Path(file_path)
            mods_path = settings_path.parent / "mods"
            if mods_path.exists() and mods_path.is_dir():
                self.import_mods_path = str(mods_path)
            else:
                self.import_mods_path = ""

            self.update_import_status()


    def auto_detect_tf2_dir(self):
        path = auto_detect_tf2()
        if path:
            self.tf_directory = path
            self.tf_path_edit.setText(path)
            validate_tf_directory(path, self.validation_label)
            QMessageBox.information(self, "Auto-Detection Successful", f"Found TF2 installation at:\n{path}")
        else:
            QMessageBox.information(self, "Auto-Detection Failed",
                                    "Could not automatically detect TF2 installation.\n"
                                    "Please manually select your tf/ directory.")


    def clear_import_selections(self):
        self.import_settings_path = ""
        self.import_mods_path = ""
        self.settings_import_edit.clear()
        self.update_import_status()

    def validate_tf_directory(self):
        result = validate_tf_directory(self.tf_directory, self.validation_label)
        self.validate_setup()
        return result

    def update_import_status(self):
        status_parts = []

        if self.import_settings_path:
            settings_path = Path(self.import_settings_path)
            if settings_path.exists():
                status_parts.append("Settings file selected")

                # check for mods folder in same directory
                if self.import_mods_path:
                    mods_path = Path(self.import_mods_path)
                    if mods_path.exists() and mods_path.is_dir():
                        status_parts.append("Mods folder found and will be imported")
                    else:
                        status_parts.append("Mods folder not found - settings only")
                else:
                    status_parts.append("No mods folder found - settings only")
            else:
                status_parts.append("Settings file not found")

        if not status_parts:
            status_parts.append("No import files selected (this is optional)")

        self.import_status_label.setText("\n".join(status_parts))

    def validate_setup(self):
        tf_valid = bool(self.tf_directory and Path(self.tf_directory).exists())
        self.finish_button.setEnabled(tf_valid)

    def finish_setup(self):
        if not self.tf_directory:
            QMessageBox.warning(self, "Setup Incomplete", "Please select a TF2 directory.")
            return

        # validate tf/ directory one more time
        if not validate_tf_directory(self.tf_directory):
            QMessageBox.warning(self, "Invalid Directory", "The selected TF2 directory is not valid.")
            return

        # import mods folder if provided
        if self.import_mods_path:
            try:
                mods_src = Path(self.import_mods_path)
                mods_dst = folder_setup.mods_dir

                if mods_dst.exists():
                    shutil.rmtree(mods_dst)

                shutil.copytree(mods_src, mods_dst)
            except Exception as e:
                QMessageBox.warning(
                    self, "Import Error",
                    f"Failed to import mods folder:\n{e}\n\nSetup will continue without importing mods."
                )

        # create or update app_settings.json
        try:
            folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = folder_setup.settings_dir / "app_settings.json"

            # start with imported settings if available
            settings_data = {}
            if self.import_settings_path:
                try:
                    settings_src = Path(self.import_settings_path)
                    with open(settings_src, 'r') as f:
                        settings_data = json.load(f)
                except Exception as e:
                    QMessageBox.warning(
                        self, "Import Error",
                        f"Failed to import settings file:\n{e}\n\nWill create new settings."
                    )

            # update with current setup values
            settings_data["tf_directory"] = self.tf_directory

            with open(settings_file, 'w') as f:
                json.dump(settings_data, f, indent=2)
        except Exception as e:
            QMessageBox.warning(
                self, "Settings Error",
                f"Failed to save settings:\n{e}\n\nSetup completed but settings may not persist."
            )

        # emit the setup completion signal with tf/ directory
        self.setup_completed.emit(self.tf_directory)
        self.accept()


def check_first_time_setup():
    settings_file = folder_setup.settings_dir / "app_settings.json"
    return not settings_file.exists()


def run_first_time_setup(parent=None):
    dialog = FirstTimeSetupDialog(parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.tf_directory
    else:
        return None


def mods_download_group(parent_dialog):
    mods_group = QGroupBox("Recommended Mods (Optional)")
    mods_layout = QVBoxLayout()

    mods_description = QLabel(
        "This collection contains TF2 particles + addons that have been personally fixed "
        "by me to work with this preloader (~77 MB)."
    )
    mods_description.setWordWrap(True)
    mods_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    mods_layout.addWidget(mods_description)

    download_mods_button = QPushButton("Download cueki's Mods")
    download_mods_button.clicked.connect(lambda: download_cueki_mods(parent_dialog, download_mods_button))
    mods_layout.addWidget(download_mods_button)

    mods_group.setLayout(mods_layout)
    return mods_group


def download_cueki_mods(parent=None, button=None):
    # disable button and show loading state
    original_text = ""
    if button:
        original_text = button.text()
        button.setEnabled(False)
        button.setText("Downloading...")
        button.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        QApplication.processEvents()

    try:
        # create progress dialog
        progress = QProgressDialog("Downloading cueki's mods (~77 MB)...", "Cancel", 0, 100, parent)
        progress.setWindowTitle("Downloading Mods")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        # download to temp location
        temp_zip = folder_setup.temp_dir / "cueki_mods.zip"
        folder_setup.temp_dir.mkdir(parents=True, exist_ok=True)

        def download_progress(block_num, block_size, total_size):
            if progress.wasCanceled():
                raise Exception("Download cancelled by user")
            if total_size > 0:
                percent = int((block_num * block_size / total_size) * 100)
                progress.setValue(min(percent, 99))
                QApplication.processEvents()

        # set timeout (10 seconds for connection/response)
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)

        try:
            urllib.request.urlretrieve(CUEKI_MODS_URL, temp_zip, download_progress)
        finally:
            socket.setdefaulttimeout(old_timeout)

        progress.setLabelText("Extracting mods...")
        progress.setValue(99)
        QApplication.processEvents()

        # extract to mods/
        folder_setup.mods_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(folder_setup.mods_dir)

        temp_zip.unlink()
        progress.setValue(100)
        progress.close()

        # refresh main window if not called from first time setup
        if not isinstance(parent, FirstTimeSetupDialog):
            main_window = parent.parent()
            if main_window and hasattr(main_window, 'refresh_all'):
                main_window.refresh_all()

        QMessageBox.information(
            parent,
            "Download Complete",
            "cueki's mods have been successfully downloaded and installed!"
        )

        # re-enable button
        if button:
            button.setEnabled(True)
            button.setText(original_text)
            button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        return True

    except Exception as e:
        if progress:
            progress.close()

        if "cancelled" not in str(e).lower():
            QMessageBox.critical(
                parent,
                "Download Failed",
                f"Failed to download mods:\n{str(e)}\n\n"
                f"You can manually download from:\n{CUEKI_MODS_URL}"
            )

        # re-enable button
        if button:
            button.setEnabled(True)
            button.setText(original_text)
            button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        return False

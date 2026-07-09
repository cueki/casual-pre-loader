import logging
from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.constants import Sourcemods
from core.download_mods import check_mods, download_mods
from core.services.setup import import_userdata, is_valid_userdata_folder
from core.settings import settings
from core.util.sourcemod import (
    InvalidSourcemodInstallationPath,
    auto_detect_sourcemod,
    validate_game_directory,
)
from gui.theme import BUTTON_STYLE_ALT, FONT_SIZE_HEADER

log = logging.getLogger()


class FirstTimeSetupDialog(QDialog):
    setup_completed = pyqtSignal(Path)  # emits the selected tf/ directory path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_status_label = None
        self.userdata_import_edit = None
        self.validation_label = None
        self.browse_button = None
        self.tf_path_edit = None
        self.finish_button = None
        self.tf_directory: Path | None = None
        self.import_userdata_path: Path | None = None

        self.setWindowTitle("First Time Setup")
        self.setFixedSize(650, 580)
        self.setModal(True)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # title
        welcome_label = QLabel("Welcome to the casual pre-loader!")
        welcome_label.setStyleSheet(f"font-size: {FONT_SIZE_HEADER}; font-weight: bold; margin: 10px;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)

        # tab widgets
        tab_widget = QTabWidget()
        tf_tab = self.create_tf_directory_tab()
        tab_widget.addTab(tf_tab, "TF2 Directory")
        import_tab = self.create_import_tab()
        tab_widget.addTab(import_tab, "Import Previous Settings")

        layout.addWidget(tab_widget)

        # bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.finish_button = QPushButton("Finish Setup")
        self.finish_button.setProperty("primary", True)
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
        self.browse_button.setStyleSheet(BUTTON_STYLE_ALT)
        self.browse_button.clicked.connect(self.browse_tf_dir)

        dir_layout.addWidget(self.tf_path_edit)
        dir_layout.addWidget(self.browse_button)
        tf_layout.addLayout(dir_layout)

        # auto-detect button
        auto_detect_button = QPushButton("Auto-Detect TF2 Installation")
        auto_detect_button.setStyleSheet(BUTTON_STYLE_ALT)
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
            "If you have previously used this preloader, you can import your data.\n"
            "Select the previous installation's 'userdata' folder - your mods, settings, and addon\n"
            "metadata will be copied into the new install.\n"
            "This is optional - you can skip this step if this is your first time using the preloader."
        )
        instructions.setWordWrap(True)
        instructions.setMargin(10)
        layout.addWidget(instructions)

        # import settings group
        import_group = QGroupBox("Import Previous Installation")
        import_layout = QVBoxLayout()

        # userdata folder import
        userdata_layout = QHBoxLayout()
        userdata_layout.addWidget(QLabel("Previous userdata folder:"))
        self.userdata_import_edit = QLineEdit()
        self.userdata_import_edit.setReadOnly(True)
        self.userdata_import_edit.setPlaceholderText("Optional: Select previous userdata/ folder...")

        userdata_browse_button = QPushButton("Browse")
        userdata_browse_button.setStyleSheet(BUTTON_STYLE_ALT)
        userdata_browse_button.clicked.connect(self.browse_userdata_folder)

        userdata_layout.addWidget(self.userdata_import_edit)
        userdata_layout.addWidget(userdata_browse_button)
        import_layout.addLayout(userdata_layout)

        # clear imports button
        clear_imports_button = QPushButton("Clear Import Selections")
        clear_imports_button.setStyleSheet(BUTTON_STYLE_ALT)
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
        if directory and self.tf_path_edit is not None:
            self.tf_directory = Path(directory)
            self.tf_path_edit.setText(directory)
            self.validate_directory()

    def browse_userdata_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Previous userdata/ Folder")
        if directory:
            self.import_userdata_path = Path(directory)
            self.userdata_import_edit.setText(directory)
            self.update_import_status()


    def auto_detect_tf2_dir(self):
        try:
            self.tf_directory = auto_detect_sourcemod()
            self.tf_path_edit.setText(str(self.tf_directory))

            validate_game_directory(self.tf_directory, self.validation_label)
            QMessageBox.information(self, "Auto-Detection Successful", f"Found TF2 installation at:\n{self.tf_directory}")
        except InvalidSourcemodInstallationPath:
            QMessageBox.information(self, "Auto-Detection Failed",
                                    "Could not automatically detect TF2 installation.\n"
                                    "Please manually select your tf/ directory.")


    def clear_import_selections(self):
        self.import_userdata_path = None
        self.userdata_import_edit.clear()
        self.update_import_status()

    def validate_directory(self):
        result = validate_game_directory(self.tf_directory, self.validation_label)
        self.validate_setup()
        return result

    def update_import_status(self):
        status_parts = []

        if self.import_userdata_path:
            userdata_path = Path(self.import_userdata_path)
            if not userdata_path.exists():
                status_parts.append("Selected folder does not exist")
            elif not is_valid_userdata_folder(userdata_path):
                status_parts.append(
                    "Selected folder is not a valid userdata/ folder (missing data/ or config/)"
                )
            else:
                found = []
                if (userdata_path / 'data' / 'mods').is_dir():
                    found.append("mods/")
                if (userdata_path / 'data' / 'modsinfo.json').is_file():
                    found.append("modsinfo.json")
                if (userdata_path / 'config' / 'app_settings.json').is_file():
                    found.append("app_settings.json")
                if (userdata_path / 'config' / 'addon_metadata.json').is_file():
                    found.append("addon_metadata.json")

                if found:
                    status_parts.append("Will import: " + ", ".join(found))
                else:
                    status_parts.append("No importable files found in selected userdata folder")

        if not status_parts:
            status_parts.append("No import folder selected (this is optional)")

        self.import_status_label.setText("\n".join(status_parts))

    def validate_setup(self):
        tf_valid = bool(self.tf_directory and self.tf_directory.is_dir())
        self.finish_button.setEnabled(tf_valid)

    def finish_setup(self):
        if not self.tf_directory:
            QMessageBox.warning(self, "Setup Incomplete", "Please select a TF2 directory.")
            return

        # validate tf/ directory one more time
        if not validate_game_directory(self.tf_directory):
            QMessageBox.warning(self, "Invalid Directory", "The selected TF2 directory is not valid.")
            return

        # import userdata if provided
        if self.import_userdata_path:
            success, warnings = import_userdata(self.import_userdata_path)
            if not success:
                QMessageBox.warning(
                    self, "Import Error",
                    "Failed to import userdata:\n" + "\n".join(warnings)
                    + "\n\nSetup will continue without importing."
                )
            elif warnings:
                log.warning("Userdata import completed with warnings: %s", warnings)

        settings._initialized = False
        try:
            # create or update app_settings.json (preserving any imported keys, overwriting tf_directory)
            if self.import_userdata_path:
                settings._load_settings(self.import_userdata_path / 'config' / 'app_settings.dir.json')

            settings.create_profile(name=Sourcemods.DEFAULT.name, game_path=self.tf_directory, sourcemod=Sourcemods.DEFAULT, activate=True)
            settings.done_initial_setup = True

            settings.save_settings()
        except Exception as e:
            QMessageBox.warning(
                self, "Settings Error",
                f"Failed to save settings:\n{e}\n\nSetup completed but settings may not persist."
            )
        finally:
            settings._initialized = True

        # emit the setup completion signal with tf/ directory
        self.setup_completed.emit(self.tf_directory)
        self.accept()


def run_first_time_setup(parent=None) -> Path:
    dialog = FirstTimeSetupDialog(parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return cast(Path, dialog.tf_directory)

    log.debug('User cancelled setup')
    raise SystemExit(1)


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
    download_mods_button.setStyleSheet(BUTTON_STYLE_ALT)
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

    progress = None
    try:
        # create progress dialog
        progress = QProgressDialog("Downloading cueki's mods (~77 MB)...", "Cancel", 0, 100, parent)
        progress.setWindowTitle("Downloading Mods")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        update = check_mods()
        if update is not None:
            download_mods(update, progress.setValue, progress.setLabelText, QApplication.processEvents, progress.wasCanceled)
        progress.close()

        # refresh main window if not called from first time setup
        if not isinstance(parent, FirstTimeSetupDialog):
            if hasattr(parent, 'refresh_all'):
                parent.refresh_all()
            elif parent.parent() and hasattr(parent.parent(), 'refresh_all'):
                parent.parent().refresh_all()

        QMessageBox.information(
            parent,
            'Download Complete',
            update is not None and "cueki's mods have been successfully downloaded and installed!" or "cueki's mods are already installed and up to date!"
        )
    except Exception as e:
        log.exception(e)

        if progress:
            progress.close()

        if 'cancelled' not in str(e).lower():
            QMessageBox.critical(
                parent,
                'Download Failed',
                f'Failed to download mods: {e}'
            )

        return False
    finally:
        if button: # re-enable button
            button.setEnabled(True)
            button.setText(original_text)
            button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

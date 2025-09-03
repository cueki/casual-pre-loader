import os
import json
import shutil
import zipfile
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QFileDialog, QMessageBox, QGroupBox, QTabWidget, 
                             QWidget, QFrame, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
from core.folder_setup import folder_setup
from gui.settings_manager import SettingsManager, validate_tf_directory


class FirstTimeSetupDialog(QDialog):
    setup_completed = pyqtSignal(str)  # emits the selected tf/ directory path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.install_mods_checkbox = None
        self.import_status_label = None
        self.mods_import_edit = None
        self.settings_import_edit = None
        self.validation_label = None
        self.browse_button = None
        self.tf_path_edit = None
        self.finish_button = None
        self.tf_directory = ""
        self.import_settings_path = ""
        self.settings_manager = SettingsManager()
        self.import_mods_path = ""
        self.install_included_mods = True
        self.mods_zip_available = self.check_mods_zip_available()
        
        self.setWindowTitle("First Time Setup")
        self.setMinimumSize(750, 500)
        self.setModal(True)
        
        self.setup_ui()
    
    def check_mods_zip_available(self):
        """Check if mods.zip exists using the same logic as other functions"""
        mods_zip_path = folder_setup.install_dir / 'mods.zip'
        return mods_zip_path.exists()
    
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
        auto_detect_button.clicked.connect(self.auto_detect_tf2)
        tf_layout.addWidget(auto_detect_button)
        
        # validation
        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        tf_layout.addWidget(self.validation_label)
        
        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)
        
        # included mods group
        mods_group = QGroupBox("Included Mods")
        mods_layout = QVBoxLayout()
        
        mods_description = QLabel(
            "This preloader comes with a collection of popular TF2 mods.\n"
            "Would you like to include these in the app?\n\n"
            "IMPORTANT: Enable this if you 'Import Previous Settings' from another version and used the pre-installed mods."
        )
        mods_description.setWordWrap(True)
        mods_layout.addWidget(mods_description)
        
        self.install_mods_checkbox = QCheckBox("Install included mods (mods.zip)")
        if self.mods_zip_available:
            self.install_mods_checkbox.setChecked(True)
        else:
            self.install_mods_checkbox.setChecked(False)
            self.install_mods_checkbox.setEnabled(False)
            self.install_mods_checkbox.setText("Install included mods (mods.zip not available)")
        self.install_mods_checkbox.toggled.connect(self.on_mods_checkbox_changed)
        mods_layout.addWidget(self.install_mods_checkbox)
        
        mods_group.setLayout(mods_layout)
        layout.addWidget(mods_group)
        
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
    
    
    def auto_detect_tf2(self):
        # attempt to automatically detect tf/ dir
        common_paths = [
            "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
            "D:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
            "~/.steam/steam/steamapps/common/Team Fortress 2/tf",
            "~/.local/share/Steam/steamapps/common/Team Fortress 2/tf",
            "/home/{}/Steam/steamapps/common/Team Fortress 2/tf".format(os.getenv('USER', '')),
        ]
        
        for path_str in common_paths:
            path = Path(path_str).expanduser()
            if path.exists() and (path / "gameinfo.txt").exists():
                self.tf_directory = str(path)
                self.tf_path_edit.setText(str(path))
                validate_tf_directory(str(path), self.validation_label)
                QMessageBox.information(
                    self, "Auto-Detection Successful", 
                    f"Found TF2 installation at:\n{path}"
                )
                return
        
        QMessageBox.information(
            self, "Auto-Detection Failed", 
            "Could not automatically detect TF2 installation.\n"
            "Please manually select your tf/ directory."
        )
    
    
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
    
    def on_mods_checkbox_changed(self, checked):
        self.install_included_mods = checked
    
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
            settings_data["included_mods_installed"] = self.install_included_mods
            
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


def get_mods_zip_enabled():
    # getter for mods.zip setting
    settings_file = folder_setup.settings_dir / "app_settings.json"
    
    if not settings_file.exists():
        return False
    
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        return settings.get("included_mods_installed", False)
    except Exception as e:
        print(f"Error reading mods setting: {e}")
        return False


def set_mods_zip_enabled(enabled):
    # setter for mods.zip setting
    settings_file = folder_setup.settings_dir / "app_settings.json"
    
    try:
        settings = {}
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        
        settings["included_mods_installed"] = enabled
        
        folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving mods setting: {e}")


def should_install_mods_zip():
    # check if included mods should be installed (checkbox enabled and mods.zip content not in mods/)
    if not get_mods_zip_enabled():
        return False
    
    mods_zip_path = folder_setup.install_dir / 'mods.zip'
    mods_dir = folder_setup.mods_dir
    
    if not mods_zip_path.exists():
        return False
    
    try:
        # get files in mods.zip
        with zipfile.ZipFile(mods_zip_path, 'r') as zip_ref:
            zip_files = {Path(name).as_posix() for name in zip_ref.namelist() if not name.endswith('/')}
        
        # get files currently installed
        installed_files = set()
        if mods_dir.exists():
            for file_path in mods_dir.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(mods_dir)
                    installed_files.add(rel_path.as_posix())
        
        # install if there are files in mods.zip that aren't installed
        return bool(zip_files - installed_files)
        
    except Exception as e:
        print(f"Error checking mods: {e}")
        return False


def should_uninstall_mods_zip():
    # check if included mods should be removed (checkbox disabled and mods.zip content is in mods/)
    if get_mods_zip_enabled():
        return False
    
    mods_zip_path = folder_setup.install_dir / 'mods.zip'
    mods_dir = folder_setup.mods_dir
    
    if not mods_zip_path.exists() or not mods_dir.exists():
        return False
    
    try:
        # get files in mods.zip
        with zipfile.ZipFile(mods_zip_path, 'r') as zip_ref:
            zip_files = {Path(name).as_posix() for name in zip_ref.namelist() if not name.endswith('/')}
        
        # get files currently installed
        installed_files = set()
        for file_path in mods_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(mods_dir)
                installed_files.add(rel_path.as_posix())
        
        # uninstall if there are mods.zip files found
        return bool(zip_files & installed_files)
        
    except Exception as e:
        print(f"Error checking mods: {e}")
        return False


def uninstall_mods_zip():
    # remove files that came from mods.zip
    mods_zip_path = folder_setup.install_dir / 'mods.zip'
    mods_dir = folder_setup.mods_dir
    
    if not mods_zip_path.exists() or not mods_dir.exists():
        return
    
    try:
        # get files in mods.zip
        with zipfile.ZipFile(mods_zip_path, 'r') as zip_ref:
            zip_files = {Path(name).as_posix() for name in zip_ref.namelist() if not name.endswith('/')}
        
        removed_count = 0
        for file_rel_path in zip_files:
            file_path = mods_dir / file_rel_path
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    removed_count += 1
                    print(f"Removed: {file_rel_path}")
                    
                    # remove empty parent directories
                    parent = file_path.parent
                    while parent != mods_dir and parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                        
                except Exception as e:
                    print(f"Error removing {file_rel_path}: {e}")
        
        print(f"Removed {removed_count} mod files")
        
    except Exception as e:
        print(f"Error uninstalling mods: {e}")
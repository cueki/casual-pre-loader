import json
import threading
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QProgressBar,
                             QListWidget, QFileDialog, QMessageBox,
                             QGroupBox, QApplication, QSplitter, QListWidgetItem, QTabWidget)
from PyQt6.QtCore import pyqtSignal, Qt
from core.folder_setup import folder_setup
from gui.drag_and_drop import ModDropZone
from gui.interface import ParticleOperations
from gui.preset_customizer import PresetSelectionManager
from gui.mod_descriptor import PresetDescription, AddonDescription
from operations.game_type import check_game_type
from tools.backup_manager import BackupManager


class ParticleManagerGUI(QMainWindow):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.preset_description = None
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.presets_list = None
        self.addons_list = None
        self.addon_description = None
        self.mod_drop_zone = None
        self.selection_manager = PresetSelectionManager()

        self.setWindowTitle("cukei's custom casual particle pre-loader :)")
        self.setFixedSize(1200, 600)

        self.tf_path = ""
        self.selected_preset_files = set()
        self.selected_addons = []
        self.processing = False

        self.operations = ParticleOperations()
        self.setup_ui()
        self.load_last_directory()
        self.load_presets_and_addons()

        self.operations.progress_signal.connect(self.update_progress)
        self.operations.error_signal.connect(self.show_error)
        self.operations.success_signal.connect(self.show_success)
        self.operations.operation_finished.connect(lambda: self.set_processing_state(False))

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # TF Directory Group
        tf_group = QGroupBox("tf/ Directory")
        tf_layout = QHBoxLayout()
        self.tf_path_edit = QLineEdit()
        self.tf_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_tf_dir)
        tf_layout.addWidget(self.tf_path_edit)
        tf_layout.addWidget(self.browse_button)
        tf_group.setLayout(tf_layout)
        main_layout.addWidget(tf_group)

        tab_widget = QTabWidget()

        # Mods Tab (Combined Presets and Addons)
        mods_tab = QWidget()
        mods_layout = QVBoxLayout(mods_tab)

        mod_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Lists
        lists_widget = QWidget()
        lists_layout = QVBoxLayout(lists_widget)

        # Presets Group
        presets_group = QGroupBox("Presets")
        presets_layout = QVBoxLayout()
        self.presets_list = QListWidget()
        self.presets_list.itemSelectionChanged.connect(self.on_preset_select)
        presets_layout.addWidget(self.presets_list)
        presets_group.setLayout(presets_layout)
        lists_layout.addWidget(presets_group)

        # Addons Group
        addons_group = QGroupBox("Addons")
        addons_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.addons_list.itemSelectionChanged.connect(self.on_addon_select)
        addons_layout.addWidget(self.addons_list)
        addons_group.setLayout(addons_layout)
        lists_layout.addWidget(addons_group)

        mod_splitter.addWidget(lists_widget)

        # Right side: Description
        description_group = QGroupBox("Details")
        description_layout = QVBoxLayout()
        self.preset_description = PresetDescription()
        self.addon_description = AddonDescription()
        description_layout.addWidget(self.preset_description)
        description_layout.addWidget(self.addon_description)
        description_group.setLayout(description_layout)

        mod_splitter.addWidget(description_group)
        mod_splitter.setSizes([300, 500])
        mods_layout.addWidget(mod_splitter)

        tab_widget.addTab(mods_tab, "Mods")

        # Custom Mods Tab
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)

        self.mod_drop_zone = ModDropZone(self)
        self.mod_drop_zone.mod_dropped.connect(self.on_mod_dropped)
        custom_layout.addWidget(self.mod_drop_zone)

        tab_widget.addTab(custom_tab, "Custom Mods")

        # Install Tab
        install_tab = QWidget()
        install_layout = QVBoxLayout(install_tab)

        install_controls = QGroupBox("Installation")
        controls_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install Selected Mods")
        self.install_button.clicked.connect(self.start_install_thread)
        button_layout.addWidget(self.install_button)

        self.restore_button = QPushButton("Uninstall Mods")
        self.restore_button.clicked.connect(self.start_restore_thread)
        button_layout.addWidget(self.restore_button)
        controls_layout.addLayout(button_layout)

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.status_label = QLabel()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        controls_layout.addWidget(progress_group)

        install_controls.setLayout(controls_layout)
        install_layout.addWidget(install_controls)
        install_layout.addStretch()

        tab_widget.addTab(install_tab, "Install")

        main_layout.addWidget(tab_widget)

    def on_mod_dropped(self):
        self.load_presets_and_addons()

    def load_presets_and_addons(self):
        self.load_presets()
        self.load_addons()

    def load_last_directory(self):
        try:
            if Path("last_directory.txt").exists():
                with open("last_directory.txt", "r") as f:
                    last_dir = f.read().strip()
                    if Path(last_dir).exists():
                        self.tf_path = last_dir
                        self.tf_path_edit.setText(last_dir)
                        self.update_restore_button_state()
                        self.prepare_game_files()
        except Exception as e:
            print(f"Error loading last directory: {e}")

    def prepare_game_files(self):
        if not self.tf_path:
            return

        try:
            backup_manager = BackupManager(self.tf_path)
            if backup_manager.create_initial_backup():
                backup_manager.prepare_working_copy()
        except Exception as e:
            self.show_error(f"Failed to prepare game files: {str(e)}")

    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_path = directory
            self.tf_path_edit.setText(directory)
            self.save_last_directory()
            self.update_restore_button_state()
            self.prepare_game_files()

    def save_last_directory(self):
        try:
            with open("last_directory.txt", "w") as f:
                f.write(self.tf_path)
        except Exception as e:
            print(f"Error saving last directory: {e}")

    def on_preset_select(self):
        selected_items = self.presets_list.selectedItems()
        if selected_items:
            selected_preset = selected_items[0].text()
            self.selected_preset_files = self.selection_manager.get_selection(selected_preset)
            preset_info = self.load_preset_info(selected_preset)
            self.preset_description.update_content(selected_preset, preset_info)
        else:
            self.preset_description.clear()

    def on_addon_select(self):
        selected_items = self.addons_list.selectedItems()
        if selected_items:
            selected_addon = selected_items[-1].text()
            addon_info = self.load_addon_info(selected_addon)
            self.addon_description.update_content(selected_addon, addon_info)
        else:
            self.addon_description.clear()

    def load_presets(self):
        presets_dir = folder_setup.presets_dir
        self.presets_list.clear()

        preset_groups = {"vanilla": [], "fun": [], "friend": [], "unknown": []}

        for preset in presets_dir.glob("*.zip"):
            preset_info = self.load_preset_info(preset.stem)
            preset_type = preset_info.get("type", "unknown").lower()
            preset_groups[preset_type].append(preset.stem)

        type_order = ["vanilla", "fun", "friend", "unknown"]
        first_item = None
        for preset_type in type_order:
            if preset_groups[preset_type]:
                for preset_name in sorted(preset_groups[preset_type]):
                    item = QListWidgetItem(preset_name)
                    self.presets_list.addItem(item)
                    if first_item is None:
                        first_item = item

        if first_item:
            self.presets_list.setCurrentItem(first_item)

    def load_addons(self):
        addons_dir = folder_setup.addons_dir
        self.addons_list.clear()
        addon_groups = {"texture": [], "model": [], "misc": [], "custom": [], "unknown": []}

        for addon in addons_dir.glob("*.zip"):
            addon_info = self.load_addon_info(addon.stem)
            addon_type = addon_info.get("type", "unknown").lower()
            addon_groups[addon_type].append(addon.stem)

        regular_types = ["texture", "model", "misc", "unknown"]
        for addon_type in regular_types:
            if addon_groups[addon_type]:
                for addon_name in sorted(addon_groups[addon_type]):
                    item = QListWidgetItem(addon_name)
                    self.addons_list.addItem(item)

        if addon_groups["custom"]:
            splitter = QListWidgetItem("──── Custom Addons ────")
            splitter.setFlags(Qt.ItemFlag.NoItemFlags)
            splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.addons_list.addItem(splitter)

            for addon_name in sorted(addon_groups["custom"]):
                item = QListWidgetItem(addon_name)
                self.addons_list.addItem(item)

    def validate_inputs(self):
        if not self.tf_path:
            self.show_error("Please select tf/ directory!")
            return False

        if not Path(self.tf_path).exists():
            self.show_error("Selected TF2 directory does not exist!")
            return False

        return True

    def start_install_thread(self):
        if not self.validate_inputs():
            return

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.install,
            args=(self.tf_path,)
        )
        thread.daemon = True
        thread.start()

    def start_restore_thread(self):
        if not self.tf_path:
            self.show_error("Please select tf/ directory!")
            return

        if QMessageBox.question(
                self,
                "Confirm Uninstall",
                "This will revert all changes that have been made to TF2 with this app. \nAre you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.restore_backup,
            args=(self.tf_path,)
        )
        thread.daemon = True
        thread.start()

    def update_restore_button_state(self):
        if not self.tf_path:
            self.restore_button.setEnabled(False)
            return

        gameinfo_path = Path(self.tf_path) / 'gameinfo.txt'
        is_modded = check_game_type(gameinfo_path) if gameinfo_path.exists() else False
        self.restore_button.setEnabled(is_modded)

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def set_processing_state(self, processing: bool):
        enabled = not processing
        self.browse_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)
        if not processing:
            self.update_restore_button_state()
        else:
            self.restore_button.setEnabled(False)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        QMessageBox.information(self, "Success", message)

    @staticmethod
    def load_preset_info(preset_name: str) -> dict:
        try:
            with open("presets/info.json", "r") as f:
                all_presets = json.load(f)
                return all_presets.get(preset_name, {
                    "type": "Unknown",
                    "description": "No description available.",
                    "features": []
                })
        except Exception as e:
            print(f"Error loading preset info: {e}")
            return {
                "type": "Unknown",
                "description": "Error loading preset information.",
                "features": []
            }

    @staticmethod
    def load_addon_info(addon_name: str) -> dict:
        try:
            with open("addons/info.json", "r") as f:
                all_addons = json.load(f)
                return all_addons.get(addon_name, {
                    "type": "Custom",
                    "description": "This addon was added by you.",
                    "contents": ["Custom content"]
                })
        except Exception as e:
            print(f"Error loading addon info: {e}")
            return {
                "type": "Misc",
                "description": "Information unavailable.",
                "contents": []
            }


def main():
    folder_setup.create_required_folders()
    app = QApplication([])
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    window = ParticleManagerGUI()
    window.show()
    app.exec()
    folder_setup.cleanup_temp_folders()

if __name__ == "__main__":
    main()
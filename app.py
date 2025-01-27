import json
import threading
import zipfile
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QProgressBar,
                             QListWidget, QFileDialog, QMessageBox,
                             QGroupBox, QApplication, QSplitter, QListWidgetItem, QTabWidget)
from PyQt6.QtCore import pyqtSignal, Qt

from core.folder_setup import folder_setup
from gui.drag_and_drop import DragDropZone
from gui.interface import ParticleOperations
from gui.preset_customizer import PresetSelectionManager, PresetCustomizer
from gui.mod_descriptor import PresetDescription, AddonDescription
from operations.game_type import check_game_type


class ParticleManagerGUI(QMainWindow):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # just waking up in the morning gotta thank god
        self.preset_description = None
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.customize_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.presets_list = None
        self.addons_list = None
        self.addon_description = None

        self.current_phase = ""
        self.current_phase_number = 0
        self.setWindowTitle("cukei's custom casual particle pre-loader :)")
        self.setFixedSize(800, 600)

        # initialize variables
        self.tf_path = ""
        self.selected_preset_files = set()
        self.selected_addons = []
        self.processing = False

        # initialize managers
        self.selection_manager = PresetSelectionManager()
        self.operations = ParticleOperations()

        # setup UI
        self.setup_ui()
        self.initialize_preset_selections()
        self.load_presets()
        self.load_addons()
        self.load_last_directory()

        # connect signals
        self.operations.progress_signal.connect(self.update_progress)
        self.operations.error_signal.connect(self.show_error)
        self.operations.success_signal.connect(self.show_success)
        self.operations.operation_finished.connect(lambda: self.set_processing_state(False))

    def setup_ui(self):
        central_widget = QWidget()
        tab_widget = QTabWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # tf Directory Group
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

        # presets Tab
        presets_tab = QWidget()
        presets_tab_layout = QVBoxLayout(presets_tab)
        presets_tab_layout.setContentsMargins(0, 0, 0, 0)

        # presets and Description in Splitter
        preset_splitter = QSplitter(Qt.Orientation.Horizontal)

        # presets Group
        presets_group = QGroupBox("Available Presets")
        presets_layout = QVBoxLayout()
        self.presets_list = QListWidget()
        self.presets_list.itemSelectionChanged.connect(self.on_preset_select)
        presets_layout.addWidget(self.presets_list)

        # customize button
        self.customize_button = QPushButton("Customize Selected Preset")
        self.customize_button.clicked.connect(self.open_customizer)
        self.customize_button.setEnabled(False)
        presets_layout.addWidget(self.customize_button)
        presets_group.setLayout(presets_layout)

        # description panel
        description_group = QGroupBox("Preset Details")
        description_layout = QVBoxLayout()
        self.preset_description = PresetDescription()
        description_layout.addWidget(self.preset_description)
        description_group.setLayout(description_layout)

        # add to splitter
        preset_splitter.addWidget(presets_group)
        preset_splitter.addWidget(description_group)
        preset_splitter.setSizes([200, 800])
        preset_splitter.setChildrenCollapsible(False)
        presets_tab_layout.addWidget(preset_splitter)

        addon_splitter = QSplitter(Qt.Orientation.Horizontal)

        # addons tab
        addons_tab = QWidget()
        addons_layout = QVBoxLayout(addons_tab)

        # addons list group
        addons_group = QGroupBox("Available Mods")
        addons_list_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.addons_list.itemSelectionChanged.connect(self.on_addon_select)
        addons_list_layout.addWidget(self.addons_list)

        # description panel for addons
        description_group = QGroupBox("Mod Details")
        description_layout = QVBoxLayout()
        self.addon_description = AddonDescription()
        description_layout.addWidget(self.addon_description)
        description_group.setLayout(description_layout)

        # add to splitter
        addon_splitter.addWidget(addons_group)
        addon_splitter.addWidget(description_group)
        addon_splitter.setSizes([200, 800])
        addon_splitter.setChildrenCollapsible(False)
        addons_layout.addWidget(addon_splitter)

        # drag and drop zone
        drag_zone = DragDropZone(self)
        drag_zone.addon_dropped.connect(lambda _: self.load_addons())
        addons_list_layout.addWidget(drag_zone)
        addons_group.setLayout(addons_list_layout)

        # install Tab
        install_tab = QWidget()
        install_layout = QVBoxLayout(install_tab)

        # installation controls group
        install_controls = QGroupBox("Installation")
        controls_layout = QVBoxLayout()

        # buttons
        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install Selected Preset and Mods")
        self.install_button.clicked.connect(self.start_install_thread)
        button_layout.addWidget(self.install_button)

        self.restore_button = QPushButton("Uninstall Mods")
        self.restore_button.clicked.connect(self.start_restore_thread)
        button_layout.addWidget(self.restore_button)
        controls_layout.addLayout(button_layout)

        # progress Group
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

        # add tabs to tab widget
        tab_widget.addTab(presets_tab, "Presets")
        tab_widget.addTab(addons_tab, "Mods")
        tab_widget.addTab(install_tab, "Install")

        # add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # connect signals directly to UI updates
        self.progress_signal.connect(self.update_progress)
        self.error_signal.connect(self.show_error)
        self.success_signal.connect(self.show_success)

    def load_last_directory(self):
        try:
            if Path("last_directory.txt").exists():
                with open("last_directory.txt", "r") as f:
                    last_dir = f.read().strip()
                    if Path(last_dir).exists():
                        self.tf_path = last_dir
                        self.tf_path_edit.setText(last_dir)
                        self.update_restore_button_state()
        except Exception as e:
            print(f"Error loading last directory: {e}")

    def save_last_directory(self):
        try:
            with open("last_directory.txt", "w") as f:
                f.write(self.tf_path)
        except Exception as e:
            print(f"Error saving last directory: {e}")

    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_path = directory
            self.tf_path_edit.setText(directory)
            self.save_last_directory()
            self.update_restore_button_state()

    def initialize_preset_selections(self):
        presets_dir = Path("presets")
        if not presets_dir.exists():
            return

        # get all preset names
        preset_names = [preset.stem for preset in presets_dir.glob("*.zip")]

        # initialize selections for presets that don't have them
        for preset_name in preset_names:
            if preset_name not in self.selection_manager.selections:
                # get available files from preset
                try:
                    with zipfile.ZipFile(presets_dir / f"{preset_name}.zip", 'r') as zip_ref:
                        files = [
                            name.split('/')[-1] for name in zip_ref.namelist()
                            if name.endswith('.pcf') and 'particles/' in name
                        ]
                        # initialize with all files selected
                        self.selection_manager.save_selection(preset_name, set(files))
                except Exception as e:
                    print(f"Error initializing selections for {preset_name}: {e}")

    def load_addons(self):
        addons_dir = folder_setup.addons_dir
        self.addons_list.clear()
        addon_groups = {"texture": [], "model": [], "misc": [], "custom": [], "unknown": []}

        for addon in addons_dir.glob("*.zip"):
            addon_info = self.load_addon_info(addon.stem)
            addon_type = addon_info.get("type", "unknown").lower()
            addon_groups[addon_type].append(addon.stem)

        # add regular addons first
        regular_types = ["texture", "model", "misc", "unknown"]
        for addon_type in regular_types:
            if addon_groups[addon_type]:
                for addon_name in sorted(addon_groups[addon_type]):
                    item = QListWidgetItem(addon_name)
                    self.addons_list.addItem(item)

        # add splitter if there are custom addons
        if addon_groups["custom"]:
            splitter = QListWidgetItem("──── Custom Addons ────")
            splitter.setFlags(Qt.ItemFlag.NoItemFlags)
            splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.addons_list.addItem(splitter)

            # add custom addons
            for addon_name in sorted(addon_groups["custom"]):
                item = QListWidgetItem(addon_name)
                self.addons_list.addItem(item)

    def get_selected_addons(self):
        return [item.text() for item in self.addons_list.selectedItems()]

    def load_presets(self):
        presets_dir = folder_setup.presets_dir
        self.presets_list.clear()

        # group presets by type
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

    def on_preset_select(self):
        selected_items = self.presets_list.selectedItems()
        if selected_items:
            selected_preset = selected_items[0].text()
            self.selected_preset_files = self.selection_manager.get_selection(selected_preset)
            self.customize_button.setEnabled(True)

            # update description panel
            preset_info = self.load_preset_info(selected_preset)
            self.preset_description.update_content(selected_preset, preset_info)
        else:
            self.customize_button.setEnabled(False)
            self.preset_description.clear()

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

    def on_addon_select(self):
        selected_items = self.addons_list.selectedItems()
        if selected_items:
            selected_addon = selected_items[-1].text()  # Get last selected item
            addon_info = self.load_addon_info(selected_addon)
            self.addon_description.update_content(selected_addon, addon_info)
        else:
            self.addon_description.clear()

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

    def validate_inputs(self):
        if not self.tf_path:
            self.show_error("Please select tf/ directory!")
            return False

        if not Path(self.tf_path).exists():
            self.show_error("Selected TF2 directory does not exist!")
            return False

        if not self.presets_list.selectedItems():
            self.show_error("Please select a preset!")
            return False

        return True

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
        self.customize_button.setEnabled(enabled)
        if not processing:
            self.update_restore_button_state()
        else:
            self.restore_button.setEnabled(False)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        QMessageBox.information(self, "Success", message)

    def open_customizer(self):
        if not self.presets_list.selectedItems():
            return

        selected_preset = self.presets_list.currentItem().text()
        self.selected_preset_files = self.selection_manager.get_selection(selected_preset)

        PresetCustomizer(self, selected_preset, self.selection_manager).exec()

    def start_install_thread(self):
        if not self.validate_inputs():
            return

        selected_preset = self.presets_list.selectedItems()[0].text()
        selected_addons = self.get_selected_addons()

        msg = []
        if self.selected_preset_files:
            msg.append(f"Installing {len(self.selected_preset_files)} selected files from preset '{selected_preset}'")
        else:
            msg.append(f"Installing all files from preset '{selected_preset}'")

        if selected_addons:
            msg.append(f"\nInstalling {len(selected_addons)} addons")

        if (QMessageBox.question(self, "Confirm Installation", f"{'. '.join(msg)}. \nContinue?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                != QMessageBox.StandardButton.Yes):
            return

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.install_preset,
            args=(self.tf_path, selected_preset, self.selected_preset_files, selected_addons)
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
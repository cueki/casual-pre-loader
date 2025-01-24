import json
import threading
import zipfile
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QProgressBar,
                             QListWidget, QFileDialog, QMessageBox,
                             QGroupBox, QApplication, QSplitter, QListWidgetItem)
from PyQt6.QtCore import pyqtSignal, Qt
from gui.interface import ParticleOperations
from gui.preset_customizer import PresetSelectionManager, PresetCustomizer


class ParticleManagerGUI(QMainWindow):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # waking up in the morning gotta thank god
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.customize_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.presets_list = None
        self.addons_list = None

        self.current_phase = ""
        self.current_phase_number = 0
        self.setWindowTitle("cukei's custom casual particle pre-loader :)")
        self.setFixedSize(500, 550)

        # tooltips
        self.tooltips = {}
        self.load_tooltips()

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
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # tf Directory Group
        tf_group = QGroupBox("tf/ Directory")
        tf_layout = QHBoxLayout()
        self.tf_path_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_tf_dir)
        tf_layout.addWidget(self.tf_path_edit)
        tf_layout.addWidget(self.browse_button)
        tf_group.setLayout(tf_layout)
        main_layout.addWidget(tf_group)

        lists_splitter = QSplitter(Qt.Orientation.Vertical)

        # presets Group
        presets_group = QGroupBox("Available Presets, pick one.")
        presets_layout = QVBoxLayout()
        self.presets_list = QListWidget()
        self.presets_list.itemSelectionChanged.connect(self.on_preset_select)

        # presets List
        self.presets_list = QListWidget()
        self.presets_list.itemSelectionChanged.connect(self.on_preset_select)
        presets_layout.addWidget(self.presets_list)

        # customize Button
        controls_layout = QHBoxLayout()
        self.customize_button = QPushButton("Customize Selected Preset")
        self.customize_button.clicked.connect(self.open_customizer)
        self.customize_button.setEnabled(False)
        controls_layout.addStretch()
        controls_layout.addWidget(self.customize_button)
        presets_layout.addLayout(controls_layout)
        presets_group.setLayout(presets_layout)
        lists_splitter.addWidget(presets_group)

        # addons Group
        addons_group = QGroupBox("Available Addons, add as many as you'd like, be sure to preload.")
        addons_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        addons_layout.addWidget(self.addons_list)
        addons_group.setLayout(addons_layout)
        lists_splitter.addWidget(addons_group)

        # splitter
        main_layout.addWidget(lists_splitter)

        # buttons
        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install Selected Preset and Addons")
        self.install_button.clicked.connect(self.start_install_thread)
        self.restore_button = QPushButton("Restore Backup")
        self.restore_button.clicked.connect(self.start_restore_thread)
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.restore_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # progress Group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.status_label = QLabel()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

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

    def load_tooltips(self):
        tooltips_path = Path("tooltips.json")
        if tooltips_path.exists():
            with open(tooltips_path, 'r') as f:
                self.tooltips = json.load(f)

    def load_addons(self):
        addons_dir = Path("addons")
        if not addons_dir.exists():
            addons_dir.mkdir(exist_ok=True)
            return

        recommended_file = Path("recommended.txt")
        recommended_addons = set()
        if recommended_file.exists():
            with open(recommended_file, 'r') as f:
                recommended_addons = {line.strip() for line in f}

        self.addons_list.clear()
        for addon in addons_dir.glob("*.zip"):
            item = QListWidgetItem(addon.stem)
            # if addon.stem in recommended_addons:
            #     item.setText(f"{addon.stem} (recommended!)")
            # if addon.stem in self.tooltips:
            #     item.setToolTip(self.tooltips[addon.stem])
            self.addons_list.addItem(item)

    def get_selected_addons(self):
        return [item.text().replace(" (recommended!)", "") for item in self.addons_list.selectedItems()]

    def load_presets(self):
        presets_dir = Path("presets")
        if not presets_dir.exists():
            self.show_error("Presets directory not found!")
            return

        recommended_file = Path("recommended.txt")
        recommended_presets = set()
        if recommended_file.exists():
            with open(recommended_file, 'r') as f:
                recommended_presets = {line.strip() for line in f}

        self.presets_list.clear()
        for preset in presets_dir.glob("*.zip"):
            item = QListWidgetItem(preset.stem)
            # if preset.stem in recommended_presets:
            #     item.setText(f"{preset.stem} (recommended!)")
            # if preset.stem in self.tooltips:
            #     item.setToolTip(self.tooltips[preset.stem])
            self.presets_list.addItem(item)

    def on_preset_select(self):
        selected_items = self.presets_list.selectedItems()
        if selected_items:
            selected_preset = selected_items[0].text().replace(" (recommended!)", "")
            self.selected_preset_files = self.selection_manager.get_selection(selected_preset)
            self.customize_button.setEnabled(True)
            button_text = "Install Selected Preset and Addons"
            self.install_button.setText(button_text)
        else:
            self.customize_button.setEnabled(False)
            self.install_button.setText("Install Selected Preset and Addons")

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

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def set_processing_state(self, processing: bool):
        enabled = not processing
        self.browse_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)
        self.restore_button.setEnabled(enabled)
        self.customize_button.setEnabled(enabled)

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

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.restore_backup,
            args=(self.tf_path,)
        )
        thread.daemon = True
        thread.start()


def main():
    app = QApplication([])
    app.setStyle("windowsvista")
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    window = ParticleManagerGUI()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
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
from gui.mod_descriptor import AddonDescription
from operations.file_processors import check_game_type
from tools.backup_manager import prepare_working_copy


class ParticleManagerGUI(QMainWindow):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.addons_list = None
        self.addon_description = None
        self.mod_drop_zone = None

        self.setWindowTitle("cukei's custom casual particle pre-loader :)")
        self.setMinimumSize(800, 400)
        self.resize(1200, 600)

        self.tf_path = ""
        self.selected_addons = []
        self.processing = False

        self.operations = ParticleOperations()
        self.setup_ui()
        self.load_last_directory()
        self.load_addons()

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

        # mods
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        self.mod_drop_zone = ModDropZone(self)
        custom_layout.addWidget(self.mod_drop_zone)
        self.mod_drop_zone.update_matrix()

        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        # add spacer to push button to the right
        nav_layout.addStretch()

        # create Next button
        next_button = QPushButton("Next")
        next_button.setFixedWidth(100)
        next_button.clicked.connect(lambda: tab_widget.setCurrentIndex(1))
        nav_layout.addWidget(next_button)

        # add navigation container to custom layout
        custom_layout.addWidget(nav_container)
        tab_widget.addTab(custom_tab, "Mods")

        # install
        install_tab = QWidget()
        install_layout = QVBoxLayout(install_tab)

        # vertical splitter for install tab
        install_splitter = QSplitter(Qt.Orientation.Vertical)

        # addons list and description
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # horizontal splitter for description
        addons_splitter = QSplitter(Qt.Orientation.Horizontal)

        # addons Group
        addons_group = QGroupBox("Addons")
        addons_layout = QVBoxLayout()
        self.addons_list = QListWidget()
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.addons_list.itemSelectionChanged.connect(self.on_addon_select)
        addons_layout.addWidget(self.addons_list)
        addons_group.setLayout(addons_layout)
        addons_splitter.addWidget(addons_group)
        addons_splitter.setChildrenCollapsible(False)

        # description
        description_group = QGroupBox("Details")
        description_layout = QVBoxLayout()
        self.addon_description = AddonDescription()
        description_layout.addWidget(self.addon_description)
        description_group.setLayout(description_layout)
        addons_splitter.addWidget(description_group)

        # set initial split sizes (300 pixels for addons list, rest for description)
        addons_splitter.setSizes([300, 300])

        left_layout.addWidget(addons_splitter)

        install_splitter.addWidget(left_widget)
        install_splitter.setChildrenCollapsible(False)

        # installation controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        install_controls = QGroupBox("Installation")
        controls_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        self.install_button.clicked.connect(self.start_install_thread)
        button_layout.addWidget(self.install_button)

        self.restore_button = QPushButton("Uninstall")
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
        right_layout.addWidget(install_controls)
        right_layout.addStretch()

        install_splitter.addWidget(right_widget)
        install_splitter.setSizes([600, 300])  # Set initial split sizes

        install_layout.addWidget(install_splitter)
        tab_widget.addTab(install_tab, "Install")

        main_layout.addWidget(tab_widget)

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


    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_path = directory
            self.tf_path_edit.setText(directory)
            self.save_last_directory()
            self.update_restore_button_state()

    def save_last_directory(self):
        try:
            with open("last_directory.txt", "w") as f:
                f.write(self.tf_path)
        except Exception as e:
            print(f"Error saving last directory: {e}")

    def on_addon_select(self):
        selected_items = self.addons_list.selectedItems()

        # reset all items to their original text
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item.flags() & Qt.ItemFlag.ItemIsSelectable:
                original_text = item.text().split(' [#')[0]
                item.setText(original_text)

        # load order number
        for pos, item in enumerate(selected_items, 1):
            original_text = item.text().split(' [#')[0]
            item.setText(f"{original_text} [#{pos}]")

        # description update
        if selected_items:
            selected_item = selected_items[-1]
            addon_name = selected_item.text().split(' [#')[0]

            addon_info = self.load_addon_info(addon_name)
            self.addon_description.update_content(addon_name, addon_info)
        else:
            self.addon_description.clear()

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

    def get_selected_addons(self):
        return [item.text().split(' [#')[0] for item in self.addons_list.selectedItems()]

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

        self.mod_drop_zone.apply_particle_selections()
        selected_addons = self.get_selected_addons()

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.install,
            args=(self.tf_path, selected_addons)
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
    prepare_working_copy()
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
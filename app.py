import json
import threading
import zipfile
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QProgressBar,
                             QListWidget, QFileDialog, QMessageBox,
                             QGroupBox, QApplication, QSplitter, QListWidgetItem, QTabWidget, QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt
from core.folder_setup import folder_setup
from gui.drag_and_drop import ModDropZone
from gui.interface import ParticleOperations
from gui.mod_descriptor import AddonDescription
from gui.settings_manager import SettingsManager
from operations.file_processors import check_game_type
from backup.backup_manager import prepare_working_copy


class ParticleManagerGUI(QMainWindow):
    progress_signal = pyqtSignal(int, str)
    error_signal = pyqtSignal(str)
    success_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.saved_addon_selections = None
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.addons_list = None
        self.addons_file_paths = {}
        self.addon_description = None
        self.mod_drop_zone = None
        self.prop_filter_checkbox = QCheckBox

        self.setWindowTitle("cukei's casual pre-loader :)")
        self.setMinimumSize(800, 400)
        self.resize(1200, 600)

        self.tf_path = ""
        self.selected_addons = []
        self.processing = False

        # save state
        self.settings_manager = SettingsManager()

        self.operations = ParticleOperations()
        self.setup_ui()
        self.load_last_directory()
        self.load_addons()

        self.operations.progress_signal.connect(self.update_progress)
        self.operations.error_signal.connect(self.show_error)
        self.operations.success_signal.connect(self.show_success)
        self.operations.operation_finished.connect(lambda: self.set_processing_state(False))

        self.prop_filter_checkbox.setChecked(self.settings_manager.get_prop_filter_state())
        self.prop_filter_checkbox.stateChanged.connect(
            lambda state: self.settings_manager.set_prop_filter_state(bool(state))
        )

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
        self.mod_drop_zone = ModDropZone(self, self.settings_manager)
        custom_layout.addWidget(self.mod_drop_zone)
        self.mod_drop_zone.update_matrix()

        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        # create Deselect All button
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.setFixedWidth(100)
        deselect_all_button.clicked.connect(lambda: self.mod_drop_zone.conflict_matrix.deselect_all())
        nav_layout.addWidget(deselect_all_button)

        # add spacer to push Next button to the right
        nav_layout.addStretch()

        # create Next button
        next_button = QPushButton("Next")
        next_button.setFixedWidth(100)
        next_button.clicked.connect(lambda: tab_widget.setCurrentIndex(1))
        nav_layout.addWidget(next_button)

        # add navigation container to custom layout
        custom_layout.addWidget(nav_container)
        tab_widget.addTab(custom_tab, "Particles")

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

        # add prop filter checkbox
        self.prop_filter_checkbox = QCheckBox(
            "Fast load (Experimental, less stable, may cause 'black cosmetic' bugs and other errors)")
        self.prop_filter_checkbox.setToolTip(
            "When unchecked (default), the game will load into itemtest + use the quick precache script")
        controls_layout.addWidget(self.prop_filter_checkbox)

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
        install_splitter.setSizes([600, 300])

        install_layout.addWidget(install_splitter)
        tab_widget.addTab(install_tab, "Install")

        main_layout.addWidget(tab_widget)

    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_path = directory
            self.tf_path_edit.setText(directory)
            self.save_last_directory()
            self.update_restore_button_state()

    def save_last_directory(self):
        self.settings_manager.set_last_directory(self.tf_path)

    def load_last_directory(self):
        last_dir = self.settings_manager.get_last_directory()
        if last_dir and Path(last_dir).exists():
            self.tf_path = last_dir
            self.tf_path_edit.setText(last_dir)
            self.update_restore_button_state()

    def on_addon_select(self):
        selected_items = self.addons_list.selectedItems()
        # reset all items
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
            addon_info = self.addons_file_paths[addon_name]
            self.addon_description.update_content(addon_name, addon_info)
        else:
            self.addon_description.clear()

        # save selections
        self.settings_manager.set_addon_selections([
            item.text().split(' [#')[0] for item in selected_items
        ])

    def apply_saved_addon_selections(self):
        saved_selections = self.settings_manager.get_addon_selections()
        if not saved_selections:
            return

        # block signals temporarily
        self.addons_list.blockSignals(True)

        # clear current selections
        self.addons_list.clearSelection()

        # apply saved selections
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                if item.text() in saved_selections:
                    item.setSelected(True)

        # re-enable signals
        self.addons_list.blockSignals(False)

        # trigger the on_addon_select manually to update UI
        self.on_addon_select()

    def load_addons(self):
        addons_dir = folder_setup.addons_dir
        self.addons_list.clear()
        addon_groups = {"texture": [], "model": [], "misc": [], "animation": [], "unknown": []}

        for addon in addons_dir.glob("*.zip"):
            addon_info = self.load_addon_info(addon.stem)
            addon_type = addon_info.get("type", "unknown").lower()
            if addon_type not in addon_groups:
                addon_groups[addon_type] = []
            addon_groups[addon_type].append(addon_info)

        # sort the addon groups alphabetically
        addon_groups = {group: addon_groups[group] for group in sorted(addon_groups)}

        # go through the addon groups and sort addons. Add splitters for each group. Unknown remains at the bottom.
        for addon_type in addon_groups:
            if addon_type != "unknown":
                splitter = QListWidgetItem("──── " + str.title(addon_type) + " ────")
                splitter.setFlags(Qt.ItemFlag.NoItemFlags)
                splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.addons_list.addItem(splitter)

                for addon_info_dict in addon_groups[addon_type]:
                    item = QListWidgetItem(addon_info_dict['addon_name'])
                    self.addons_list.addItem(item)
                    self.addons_file_paths[addon_info_dict['addon_name']] = addon_info_dict

            if addon_type == 'unknown':
                splitter = QListWidgetItem("──── Unknown Addons ────")
                splitter.setFlags(Qt.ItemFlag.NoItemFlags)
                splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.addons_list.addItem(splitter)

                for addon_info_dict in addon_groups[addon_type]:
                    item = QListWidgetItem(addon_info_dict['addon_name'])
                    self.addons_list.addItem(item)
                    self.addons_file_paths[addon_info_dict['addon_name']] = addon_info_dict

        self.apply_saved_addon_selections()

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
        prop_filter_state = not self.prop_filter_checkbox.isChecked()

        self.set_processing_state(True)
        thread = threading.Thread(
            target=self.operations.install,
            args=(self.tf_path, selected_addons, prop_filter_state)
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
    def load_addon_info(addon_stem: str) -> dict:
        file_path = f'addons/{addon_stem}.zip'
        try:
            with zipfile.ZipFile(file_path, 'r') as addon_zip:
                if 'mod.json' not in addon_zip.namelist():
                    raise FileNotFoundError

                with addon_zip.open('mod.json') as addon_json:
                    try:
                        addon_info = json.load(addon_json)
                        addon_info['file_path'] = addon_stem
                        return addon_info
                    except json.JSONDecodeError:
                        pass 
        except (FileNotFoundError, zipfile.BadZipFile):
            pass

        # fallback return for any failure
        return {
            "addon_name": addon_stem,
            "type": "Unknown",
            "description": "",
            "contents": ["Custom content"],
            "file_path": addon_stem
        }


def main():
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()
    prepare_working_copy()
    app = QApplication([])
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    window = ParticleManagerGUI()
    import platform
    if platform.system() == 'Windows':
        import ctypes
        my_app_id = 'cool.app.id.yes' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id) # silly ctypes let me pick my icon !!
    window.setWindowIcon(QIcon('gui/cueki_icon.ico'))
    window.show()
    app.exec()
    folder_setup.cleanup_temp_folders()

if __name__ == "__main__":
    main()
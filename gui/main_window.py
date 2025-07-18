import os
from sys import platform
import subprocess
import threading
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QProgressBar, QFileDialog, QMessageBox, QGroupBox, QSplitter, QTabWidget,
                             QCheckBox)
from core.folder_setup import folder_setup
from core.handlers.file_handler import scan_for_valve_rc_files
from gui.settings_manager import SettingsManager
from gui.drag_and_drop import ModDropZone
from gui.addon_manager import AddonManager
from gui.installation import InstallationManager
from gui.addon_panel import AddonPanel


class ParticleManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # managers
        self.settings_manager = SettingsManager()
        self.addon_manager = AddonManager(self.settings_manager)
        self.install_manager = InstallationManager()

        # UI components
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.browse_button = None
        self.tf_path_edit = None
        self.addons_list = None
        self.addon_description = None
        self.mod_drop_zone = None

        # setup UI and connect signals
        self.setWindowTitle("cukei's casual pre-loader :)")
        self.setMinimumSize(800, 400)
        self.resize(1200, 700)
        self.setup_ui()
        self.setup_signals()

        # load initial data
        self.load_last_directory()
        self.load_addons()
        self.scan_for_mcp_files()
        self.rescan_addon_contents()

        # valve.rc flag
        self.valve_rc_found = None

    def setup_ui(self):
        # main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # TF Directory Group
        tf_group = QGroupBox("tf/ Directory")
        tf_layout = QHBoxLayout()
        self.tf_path_edit = QLineEdit()
        self.tf_path_edit.setReadOnly(True)
        self.browse_button = QPushButton("Browse")
        tf_layout.addWidget(self.tf_path_edit)
        tf_layout.addWidget(self.browse_button)
        tf_group.setLayout(tf_layout)
        main_layout.addWidget(tf_group)

        # tab widget for particles and install
        tab_widget = QTabWidget()
        particles_tab = self.setup_particles_tab(tab_widget)
        tab_widget.addTab(particles_tab, "Particles")
        install_tab = self.setup_install_tab()
        tab_widget.addTab(install_tab, "Install")
        main_layout.addWidget(tab_widget)

    def setup_particles_tab(self, parent):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # mod drop zone
        self.mod_drop_zone = ModDropZone(self, self.settings_manager, self.rescan_addon_contents)
        layout.addWidget(self.mod_drop_zone)
        self.mod_drop_zone.update_matrix()

        # nav buttons
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        # Deselect All
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.setFixedWidth(100)
        deselect_all_button.clicked.connect(lambda: self.mod_drop_zone.conflict_matrix.deselect_all())
        nav_layout.addWidget(deselect_all_button)

        # spacer
        nav_layout.addStretch()

        # next button
        next_button = QPushButton("Next")
        next_button.setFixedWidth(100)
        next_button.clicked.connect(lambda: parent.setCurrentIndex(1))
        nav_layout.addWidget(next_button)

        layout.addWidget(nav_container)
        return tab

    def setup_install_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # main splitter
        install_splitter = QSplitter(Qt.Orientation.Vertical)
        addon_panel = AddonPanel()
        self.addons_list = addon_panel.addons_list
        self.addon_description = addon_panel.addon_description

        # linking addon signals to main
        addon_panel.refresh_button_clicked.connect(self.load_addons)
        addon_panel.delete_button_clicked.connect(self.delete_selected_addons)
        addon_panel.open_addons_button_clicked.connect(self.open_addons_folder)
        addon_panel.addon_selection_changed.connect(self.on_addon_select)
        install_splitter.addWidget(addon_panel)

        # install
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        install_group = QGroupBox("Installation")
        install_controls_layout = QVBoxLayout()

        # buttons
        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        button_layout.addWidget(self.install_button)

        self.restore_button = QPushButton("Uninstall")
        button_layout.addWidget(self.restore_button)
        install_controls_layout.addLayout(button_layout)

        # progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.status_label = QLabel()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        install_controls_layout.addWidget(progress_group)

        install_group.setLayout(install_controls_layout)
        controls_layout.addWidget(install_group)
        controls_layout.addStretch()

        install_splitter.addWidget(controls_widget)
        install_splitter.setSizes([1000, 300]) # forces install widget to bottom on resize

        layout.addWidget(install_splitter)
        return tab

    def setup_signals(self):
        # button signals
        self.browse_button.clicked.connect(self.browse_tf_dir)
        self.install_button.clicked.connect(self.start_install)
        self.restore_button.clicked.connect(self.start_restore)

        # addon signals
        self.addons_list.itemSelectionChanged.connect(self.on_addon_select)
        self.mod_drop_zone.addon_updated.connect(self.load_addons)

        # installation signals
        self.install_manager.progress_update.connect(self.update_progress)
        self.install_manager.operation_error.connect(self.show_error)
        self.install_manager.operation_success.connect(self.show_success)
        self.install_manager.operation_finished.connect(self.on_operation_finished)

    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.install_manager.set_tf_path(directory)
            self.tf_path_edit.setText(directory)
            self.settings_manager.set_last_directory(directory)
            self.update_restore_button_state()
            self.scan_for_mcp_files()
            self.scan_for_valve_rc(directory)

    def load_last_directory(self):
        last_dir = self.settings_manager.get_last_directory()
        if last_dir and Path(last_dir).exists():
            self.install_manager.set_tf_path(last_dir)
            self.tf_path_edit.setText(last_dir)
            self.update_restore_button_state()
            self.scan_for_valve_rc(last_dir)

    def load_addons(self):
        updates_found = self.addon_manager.scan_addon_contents()
        self.addon_manager.load_addons(self.addons_list)
        self.apply_saved_addon_selections()
        if updates_found:
            self.status_label.setText("Addons refreshed - updates found")
        else:
            self.status_label.setText("Addons refreshed")
            
    def get_selected_addons(self):
        selected_addon_names = [item.text().split(' [#')[0] for item in self.addons_list.selectedItems()]
        file_paths = []
        for name in selected_addon_names:
            if name in self.addon_manager.addons_file_paths:
                file_paths.append(self.addon_manager.addons_file_paths[name]['file_path'])
        return file_paths

    def on_addon_select(self):
        try:
            # first time setup - store original names
            selected_items = self.addons_list.selectedItems()
            for i in range(self.addons_list.count()):
                item = self.addons_list.item(i)
                if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                    if not item.data(Qt.ItemDataRole.UserRole):
                        item.setData(Qt.ItemDataRole.UserRole, item.text())

            # reset all items to original names
            for i in range(self.addons_list.count()):
                item = self.addons_list.item(i)
                if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                    original_name = item.data(Qt.ItemDataRole.UserRole)
                    if original_name:
                        item.setText(original_name)
                    item.setToolTip("")

            # mark selected items with order numbers and check conflicts
            addon_contents = self.settings_manager.get_addon_contents()
            for pos, item in enumerate(selected_items, 1):
                original_name = item.data(Qt.ItemDataRole.UserRole) or item.text()
                display_text = f"{original_name} [#{pos}]"

                if addon_contents and original_name in addon_contents:
                    conflicts = {}
                    addon_files = set(addon_contents[original_name])

                    # check against other addons
                    for other_item in selected_items:
                        if other_item != item:
                            other_name = other_item.data(Qt.ItemDataRole.UserRole) or other_item.text()
                            if other_name in addon_contents:
                                other_files = set(addon_contents[other_name])
                                common_files = addon_files.intersection(other_files)
                                if common_files:
                                    conflicts[other_name] = list(common_files)

                    if conflicts:
                        display_text += " ⚠️"
                        tooltip = "Conflicts with:\n"
                        for conflict_addon, conflict_files in conflicts.items():
                            tooltip += f"• {conflict_addon}: "
                            if conflict_files:
                                tooltip += f"{len(conflict_files)} files including {conflict_files[0]}\n"
                            else:
                                tooltip += "Unknown files\n"

                        item.setToolTip(tooltip)

                item.setText(display_text)

            # description panel
            if selected_items:
                selected_item = selected_items[-1]
                original_name = selected_item.data(Qt.ItemDataRole.UserRole) or selected_item.text()

                if original_name in self.addon_manager.addons_file_paths:
                    addon_info = self.addon_manager.addons_file_paths[original_name]
                    self.addon_description.update_content(original_name, addon_info)
                else:
                    self.addon_description.clear()
            else:
                self.addon_description.clear()

            # save selections
            self.settings_manager.set_addon_selections([
                item.data(Qt.ItemDataRole.UserRole) or item.text()
                for item in selected_items
            ])

        except Exception as e:
            print(f"Error in on_addon_select: {e}")
            import traceback
            traceback.print_exc()

    def apply_saved_addon_selections(self):
        saved_selections = self.settings_manager.get_addon_selections()
        if not saved_selections:
            return

        # block signals temporarily
        self.addons_list.blockSignals(True)

        # clear current selections
        self.addons_list.clearSelection()

        # apply saved selections
        item_map = {}
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
                item_map[item.text()] = item

        for addon_name in saved_selections:
            if addon_name in item_map:
                item_map[addon_name].setSelected(True)

        self.addons_list.blockSignals(False)
        self.on_addon_select()

    def scan_for_mcp_files(self):
        tf_path = self.install_manager.tf_path
        if not tf_path:
            return

        custom_dir = Path(tf_path) / 'custom'
        if not custom_dir.exists():
            return

        conflicting_items = {
            "folders": ["_modern casual preloader"],
            "files": [
                "_mcp hellfire hale fix.vpk",
                "_mcp mvm victory screen fix.vpk",
                "_mcp saxton hale fix.vpk"
            ]
        }

        found_conflicts = []

        for folder_name in conflicting_items["folders"]:
            folder_path = custom_dir / folder_name
            if folder_path.exists() and folder_path.is_dir():
                found_conflicts.append(f"Folder: {folder_name}")

        for file_name in conflicting_items["files"]:
            file_path = custom_dir / file_name
            if file_path.exists() and file_path.is_file():
                found_conflicts.append(f"File: {file_name}")

        if found_conflicts:
            conflict_list = "\n• ".join(found_conflicts)
            QMessageBox.warning(
                self,
                "Conflicting Files Detected",
                f"The following items in your custom folder may conflict with this method:\n\n• {conflict_list}\n\nIt's recommended to remove these to avoid issues."
            )

    def scan_for_valve_rc(self, directory):
        found_files, self.valve_rc_found = scan_for_valve_rc_files(directory)
        skip_valve_rc_warning = self.settings_manager.get_skip_valve_rc_warning()
        if found_files and not skip_valve_rc_warning:
            conflict_list = "\n• ".join(found_files)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("valve.rc found (most likely in HUD)")
            msg_box.setText(f"The following valve.rc files were found in your custom folder:\n• {conflict_list}\n\n"
                            "You have two options.\n"
                            "   1. Add +exec w/config.cfg to your launch options\n"
                            "   2. Remove the file from the HUD")
            msg_box.setIcon(QMessageBox.Icon.Warning)

            dont_show_checkbox = QCheckBox("I put '+exec w/config' in my launch options, don't show this warning again")
            msg_box.setCheckBox(dont_show_checkbox)
            msg_box.exec()

            if dont_show_checkbox.isChecked():
                self.settings_manager.set_skip_valve_rc_warning(True)

    def rescan_addon_contents(self):
        thread = threading.Thread(target=self.addon_manager.scan_addon_contents)
        thread.daemon = True
        thread.start()

    def start_install(self):
        selected_addons = self.get_selected_addons()
        self.set_processing_state(True)
        self.install_manager.install(selected_addons, self.mod_drop_zone, self.valve_rc_found)

    def start_restore(self):
        if self.install_manager.restore():
            self.set_processing_state(True)

    def update_restore_button_state(self):
        is_modified = self.install_manager.is_modified()
        self.restore_button.setEnabled(is_modified)

    def set_processing_state(self, processing: bool):
        enabled = not processing
        self.browse_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)
        if not processing:
            self.update_restore_button_state()
        else:
            self.restore_button.setEnabled(False)

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_operation_finished(self):
        self.set_processing_state(False)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        QMessageBox.information(self, "Success", message)

    def delete_selected_addons(self):
        success, message = self.addon_manager.delete_selected_addons(self.addons_list)
        if success is None:
            return
        elif success:
            self.show_success(message)
            self.load_addons()
        else:
            self.show_error(message)

    def open_addons_folder(self):
        addons_path = folder_setup.addons_dir

        if not addons_path.exists():
            self.show_error("Addons folder does not exist!")
            return

        try:
            if platform == "win32":
                os.startfile(str(addons_path))
            else:
                subprocess.run(["xdg-open", str(addons_path)])

            self.status_label.setText("Opened addons folder")
        except Exception as e:
            self.show_error(f"Failed to open addons folder: {str(e)}")

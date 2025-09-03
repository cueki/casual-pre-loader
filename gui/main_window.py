import os
from sys import platform
import subprocess
import threading
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QProgressBar, QFileDialog, QMessageBox, QGroupBox, QSplitter, QTabWidget,
                             QCheckBox,  QDialog)
from PyQt6.QtGui import QAction
from core.folder_setup import folder_setup
from gui.settings_manager import SettingsManager, validate_tf_directory
from gui.drag_and_drop import ModDropZone
from gui.addon_manager import AddonManager
from gui.installation import InstallationManager
from gui.addon_panel import AddonPanel
from gui.first_time_setup import get_mods_zip_enabled, set_mods_zip_enabled
from core.version import VERSION


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ok_button = None
        self.validation_label = None
        self.browse_button = None
        self.tf_path_edit = None
        self.tf_directory = ""
        self.mods_checkbox = None
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 375)
        self.setModal(True)
        
        # get current tf/ directory from parent's install manager
        if hasattr(parent, 'install_manager') and parent.install_manager.tf_path:
            self.tf_directory = parent.install_manager.tf_path
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # tf/ Directory Group
        tf_group = QGroupBox("TF2 Directory")
        tf_layout = QVBoxLayout()
        
        # directory display
        current_label = QLabel("Current TF2 directory:")
        tf_layout.addWidget(current_label)
        
        # directory selection
        dir_layout = QHBoxLayout()
        self.tf_path_edit = QLineEdit()
        self.tf_path_edit.setReadOnly(True)
        self.tf_path_edit.setText(self.tf_directory)
        self.tf_path_edit.setPlaceholderText("No TF2 directory selected...")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_tf_dir)
        
        dir_layout.addWidget(self.tf_path_edit)
        dir_layout.addWidget(self.browse_button)
        tf_layout.addLayout(dir_layout)
        
        # validation
        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        tf_layout.addWidget(self.validation_label)
        
        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)
        
        # validate initial directory
        if self.tf_directory:
            validate_tf_directory(self.tf_directory, self.validation_label)
        
        # included mods group
        mods_group = QGroupBox("Included Mods")
        mods_layout = QVBoxLayout()
        
        mods_description = QLabel(
            "Control whether included mods (mods.zip) should be available in the app.\n"
            "Note: Changing this setting will take effect on next app restart."
        )
        mods_description.setWordWrap(True)
        mods_layout.addWidget(mods_description)
        
        self.mods_checkbox = QCheckBox("Include built-in mods (mods.zip)")
        # set current value from settings
        self.mods_checkbox.setChecked(get_mods_zip_enabled())
        mods_layout.addWidget(self.mods_checkbox)
        mods_group.setLayout(mods_layout)
        layout.addWidget(mods_group)
        
        # version group
        version_group = QGroupBox("About")
        version_layout = QVBoxLayout()
        version_label = QLabel(f"Version: {VERSION}")
        version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(version_label)
        
        # show update info if available
        if self.update_info:
            update_label = QLabel(f"Update available: v{self.update_info['version']}")
            update_label.setStyleSheet("color: orange; font-weight: bold;")
            version_layout.addWidget(update_label)
        
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        layout.addStretch()
        
        # buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.save_and_accept)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
    
    def browse_tf_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf/ Directory")
        if directory:
            self.tf_directory = directory
            self.tf_path_edit.setText(directory)
            validate_tf_directory(directory, self.validation_label)
    
    
    def get_tf_directory(self):
        return self.tf_directory

    def save_and_accept(self):
        # save mods.zip setting
        set_mods_zip_enabled(self.mods_checkbox.isChecked())
        self.accept()


class ParticleManagerGUI(QMainWindow):
    def __init__(self, tf_directory=None, update_info=None):
        super().__init__()
        # store initial tf directory from first-time setup
        self.initial_tf_directory = tf_directory
        self.update_info = update_info
        
        # managers
        self.settings_manager = SettingsManager()
        self.addon_manager = AddonManager(self.settings_manager)
        self.install_manager = InstallationManager(self.settings_manager)

        # UI components
        self.status_label = None
        self.progress_bar = None
        self.restore_button = None
        self.install_button = None
        self.addons_list = None
        self.addon_description = None
        self.mod_drop_zone = None

        # setup UI and connect signals
        self.setWindowTitle("cukei's casual pre-loader :)")
        self.setMinimumSize(800, 400)
        self.resize(1200, 700)
        self.setAcceptDrops(True)
        self.setup_menu_bar()
        self.setup_ui()
        self.setup_signals()

        # load initial data
        if self.initial_tf_directory:
            # set tf/ directory from first-time setup and save it
            self.install_manager.set_tf_path(self.initial_tf_directory)
            self.settings_manager.set_tf_directory(self.initial_tf_directory)
        else:
            self.load_tf_directory()
        
        self.load_addons()
        self.scan_for_mcp_files()
        self.rescan_addon_contents()


    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # options menu
        options_menu = menubar.addMenu("Options")
        
        # settings action
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        options_menu.addAction(settings_action)

    def setup_ui(self):
        # main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

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


    def load_tf_directory(self):
        tf_dir = self.settings_manager.get_tf_directory()
        if tf_dir and Path(tf_dir).exists():
            self.install_manager.set_tf_path(tf_dir)
            self.update_restore_button_state()

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

    def show_launch_options_popup(self):
        skip_launch_popup = self.settings_manager.get_skip_launch_options_popup()
        if not skip_launch_popup:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Installation Complete - Launch Options Required")
            msg_box.setText("Installation completed successfully!\n\n"
                            "IMPORTANT: You must add the following to your TF2 launch options:\n\n"
                            "+exec w/config.cfg\n\n"
                            "This ensures the preloader works correctly with your game.")
            msg_box.setIcon(QMessageBox.Icon.Information)

            dont_show_checkbox = QCheckBox("Don't show this popup again")
            msg_box.setCheckBox(dont_show_checkbox)
            msg_box.exec()

            if dont_show_checkbox.isChecked():
                self.settings_manager.set_skip_launch_options_popup(True)

    def rescan_addon_contents(self):
        thread = threading.Thread(target=self.addon_manager.scan_addon_contents)
        thread.daemon = True
        thread.start()

    def start_install(self):
        selected_addons = self.get_selected_addons()
        self.set_processing_state(True)
        self.install_manager.install(selected_addons, self.mod_drop_zone)

    def start_restore(self):
        if self.install_manager.restore():
            self.set_processing_state(True)

    def update_restore_button_state(self):
        is_modified = self.install_manager.is_modified()
        self.restore_button.setEnabled(is_modified)

    def set_processing_state(self, processing: bool):
        enabled = not processing
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
        self.show_launch_options_popup()

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

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # update TF directory if changed
            new_tf_dir = dialog.get_tf_directory()
            if new_tf_dir and new_tf_dir != self.install_manager.tf_path:
                self.install_manager.set_tf_path(new_tf_dir)
                self.settings_manager.set_tf_directory(new_tf_dir)
                self.update_restore_button_state()
                self.scan_for_mcp_files()
                self.status_label.setText("TF2 directory updated successfully")

    def dragEnterEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragLeaveEvent(event)

    def dropEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dropEvent(event)

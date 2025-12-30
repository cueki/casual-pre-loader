import logging
import os
import subprocess
import threading
from pathlib import Path
from sys import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.folder_setup import folder_setup
from core.particle_splits import migrate_old_particle_files
from core.version import VERSION
from gui.addons_manager import AddonsManager
from gui.addon_panel import AddonPanel
from gui.drag_and_drop import ModDropZone
from gui.first_time_setup import mods_download_group
from gui.interface import Interface
from core.settings import SettingsManager
from core.util.sourcemod import (
    auto_detect_goldrush,
    auto_detect_tf2,
    validate_goldrush_directory,
    validate_tf_directory,
)

log = logging.getLogger()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ok_button = None
        self.validation_label = None
        self.browse_button = None
        self.tf_path_edit = None
        self.goldrush_validation_label = None
        self.goldrush_browse_button = None
        self.goldrush_path_edit = None
        self.console_checkbox = None
        self.suppress_updates_checkbox = None
        self.skip_launch_popup_checkbox = None
        self.disable_paint_checkbox = None
        self.tf_directory = ""
        self.goldrush_directory = ""

        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 625)
        self.setModal(True)

        # get current tf/ directory from parent's install manager
        if hasattr(parent, 'install_manager') and parent.install_manager.tf_path:
            self.tf_directory = parent.install_manager.tf_path

        # get current goldrush directory from parent's settings manager
        if hasattr(parent, 'settings_manager'):
            self.goldrush_directory = parent.settings_manager.get_goldrush_directory()

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

        # auto-detect button
        auto_detect_tf_button = QPushButton("Auto-Detect TF2")
        auto_detect_tf_button.clicked.connect(self.auto_detect_tf2_dir)
        tf_layout.addWidget(auto_detect_tf_button)

        # validation
        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        tf_layout.addWidget(self.validation_label)

        tf_group.setLayout(tf_layout)
        layout.addWidget(tf_group)

        # validate initial directory
        if self.tf_directory:
            validate_tf_directory(self.tf_directory, self.validation_label)

        # Gold Rush stuff - maybe change this
        goldrush_group = QGroupBox("Gold Rush Directory (Optional)")
        goldrush_layout = QVBoxLayout()

        goldrush_label = QLabel("TF2 Gold Rush mod directory:")
        goldrush_layout.addWidget(goldrush_label)

        # directory selection
        goldrush_dir_layout = QHBoxLayout()
        self.goldrush_path_edit = QLineEdit()
        self.goldrush_path_edit.setReadOnly(True)
        self.goldrush_path_edit.setText(self.goldrush_directory)
        self.goldrush_path_edit.setPlaceholderText("No Gold Rush directory selected...")

        self.goldrush_browse_button = QPushButton("Browse...")
        self.goldrush_browse_button.clicked.connect(self.browse_goldrush_dir)

        goldrush_dir_layout.addWidget(self.goldrush_path_edit)
        goldrush_dir_layout.addWidget(self.goldrush_browse_button)
        goldrush_layout.addLayout(goldrush_dir_layout)

        # auto-detect button
        auto_detect_gr_button = QPushButton("Auto-Detect Gold Rush")
        auto_detect_gr_button.clicked.connect(self.auto_detect_goldrush_dir)
        goldrush_layout.addWidget(auto_detect_gr_button)

        # validation
        self.goldrush_validation_label = QLabel("")
        self.goldrush_validation_label.setWordWrap(True)
        goldrush_layout.addWidget(self.goldrush_validation_label)

        goldrush_group.setLayout(goldrush_layout)
        layout.addWidget(goldrush_group)

        # validate initial goldrush directory
        if self.goldrush_directory:
            validate_goldrush_directory(self.goldrush_directory, self.goldrush_validation_label)

        # mods download group
        layout.addWidget(mods_download_group(self))

        # preloader settings group
        preloader_group = QGroupBox("Preloader Settings")
        preloader_layout = QVBoxLayout()

        self.console_checkbox = QCheckBox("Enable TF2 console on startup")
        self.suppress_updates_checkbox = QCheckBox("Suppress update notifications")
        self.skip_launch_popup_checkbox = QCheckBox("Suppress launch options reminder")
        self.disable_paint_checkbox = QCheckBox("Disable paint colors on cosmetics")

        # load current settings from parent's settings_manager
        parent_widget = self.parent()
        if parent_widget and hasattr(parent_widget, 'settings_manager'):
            self.console_checkbox.setChecked(parent_widget.settings_manager.get_show_console_on_startup())
            self.suppress_updates_checkbox.setChecked(parent_widget.settings_manager.get_suppress_update_notifications())
            self.skip_launch_popup_checkbox.setChecked(parent_widget.settings_manager.get_skip_launch_options_popup())
            self.disable_paint_checkbox.setChecked(parent_widget.settings_manager.get_disable_paint_colors())
        else:
            # defaults
            self.console_checkbox.setChecked(True)
            self.suppress_updates_checkbox.setChecked(False)
            self.skip_launch_popup_checkbox.setChecked(False)
            self.disable_paint_checkbox.setChecked(False)

        preloader_layout.addWidget(self.console_checkbox)
        preloader_layout.addWidget(self.suppress_updates_checkbox)
        preloader_layout.addWidget(self.skip_launch_popup_checkbox)
        preloader_layout.addWidget(self.disable_paint_checkbox)

        preloader_group.setLayout(preloader_layout)
        layout.addWidget(preloader_group)
        layout.addStretch()

        # buttons with version in bottom left
        button_layout = QHBoxLayout()
        version_label = QLabel(f"Version: {VERSION}")
        version_label.setStyleSheet("color: gray;")
        button_layout.addWidget(version_label)
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

    def browse_goldrush_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select tf_goldrush/ Directory")
        if directory:
            self.goldrush_directory = directory
            self.goldrush_path_edit.setText(directory)
            validate_goldrush_directory(directory, self.goldrush_validation_label)

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

    def auto_detect_goldrush_dir(self):
        path = auto_detect_goldrush()
        if path:
            self.goldrush_directory = path
            self.goldrush_path_edit.setText(path)
            validate_goldrush_directory(path, self.goldrush_validation_label)
            QMessageBox.information(self, "Auto-Detection Successful", f"Found Gold Rush installation at:\n{path}")
        else:
            QMessageBox.information(self, "Auto-Detection Failed",
                                    "Could not automatically detect Gold Rush installation.\n"
                                    "Please manually select your tf_goldrush/ directory.")

    def get_tf_directory(self):
        return self.tf_directory

    def get_goldrush_directory(self):
        return self.goldrush_directory

    def get_show_console_on_startup(self):
        return self.console_checkbox.isChecked()

    def get_suppress_update_notifications(self):
        return self.suppress_updates_checkbox.isChecked()

    def get_skip_launch_options_popup(self):
        return self.skip_launch_popup_checkbox.isChecked()

    def get_disable_paint_colors(self):
        return self.disable_paint_checkbox.isChecked()

    def save_and_accept(self):
        self.accept()


class ParticleManagerGUI(QMainWindow):
    def __init__(self, tf_directory=None):
        super().__init__()
        # store initial tf directory from first-time setup
        self.simple_mode_action = None
        self.addon_panel = None
        self.initial_tf_directory = tf_directory

        # managers
        self.settings_manager = SettingsManager()
        self.addon_manager = AddonsManager(self.settings_manager)
        self.install_manager = Interface(self.settings_manager)

        # UI components
        self.restore_button = None
        self.install_button = None
        self.addons_list = None
        self.addon_description = None
        self.progress_dialog = None
        self.mod_drop_zone: ModDropZone | None = None

        # setup UI and connect signals
        self.setWindowTitle("cukei's casual pre-loader :)")
        self.setMinimumSize(1200, 700)
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

        # migrate old particle files to new split format
        migrate_old_particle_files()

        # apply saved simple mode preference
        saved_mode = self.settings_manager.get_simple_particle_mode()
        if saved_mode:
            self.mod_drop_zone.conflict_matrix.set_simple_mode(True)

        self.mod_drop_zone.update_matrix()

        self.load_addons()
        self.scan_for_mcp_files()
        self.rescan_addon_contents()

        # update install target dropdown based on Gold Rush availability
        self.update_install_target_dropdown()

        # ensure load order display is updated on startup
        self.update_load_order_display()


    def setup_menu_bar(self):
        menubar = self.menuBar()

        # options menu
        options_menu = menubar.addMenu("Options")

        # jank simple mode toggle because checkbox breaks formatting
        saved_mode = self.settings_manager.get_simple_particle_mode()
        simple_mode_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogYesButton if saved_mode else QStyle.StandardPixmap.SP_DialogNoButton
        )
        simple_mode_action = QAction(simple_mode_icon, "Simple Particle Mode", self)
        simple_mode_action.triggered.connect(self.toggle_particle_mode)
        options_menu.addAction(simple_mode_action)
        self.simple_mode_action = simple_mode_action

        # separator
        options_menu.addSeparator()

        # refresh all
        refresh_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        refresh_action = QAction(refresh_icon, "Refresh All", self)
        refresh_action.triggered.connect(self.refresh_all)
        options_menu.addAction(refresh_action)

        # open addons folder
        folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        open_folder_action = QAction(folder_icon, "Open Addons Folder", self)
        open_folder_action.triggered.connect(self.open_addons_folder)
        options_menu.addAction(open_folder_action)

        # separator
        options_menu.addSeparator()

        # settings action
        settings_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        settings_action = QAction(settings_icon, "Settings...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        options_menu.addAction(settings_action)

    def toggle_particle_mode(self):
        # toggle current state
        current_state = self.settings_manager.get_simple_particle_mode()
        new_state = not current_state

        # update icon
        new_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogYesButton if new_state else QStyle.StandardPixmap.SP_DialogNoButton
        )
        self.simple_mode_action.setIcon(new_icon)

        # update mode
        if self.mod_drop_zone and self.mod_drop_zone.conflict_matrix:
            self.mod_drop_zone.conflict_matrix.set_simple_mode(new_state)
        self.settings_manager.set_simple_particle_mode(new_state)

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
        # don't call update_matrix here - it will be called after setting simple mode in __init__

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

        # addon panel with install buttons
        self.addon_panel = AddonPanel()
        self.addons_list = self.addon_panel.addons_list
        self.addon_description = self.addon_panel.addon_description
        self.install_button = self.addon_panel.install_button
        self.restore_button = self.addon_panel.restore_button

        # linking addon signals to main
        self.addon_panel.delete_button_clicked.connect(self.delete_selected_addons)
        self.addon_panel.addon_selection_changed.connect(self.on_addon_click)
        self.addon_panel.addon_checkbox_changed.connect(self.on_addon_checkbox_changed)
        self.addon_panel.load_order_changed.connect(self.on_load_order_changed)
        self.addon_panel.target_changed.connect(self.update_restore_button_state)
        self.addon_description.addon_modified.connect(self.load_addons)

        layout.addWidget(self.addon_panel)
        return tab

    def setup_signals(self):
        # button signals
        self.install_button.clicked.connect(self.start_install)
        self.restore_button.clicked.connect(self.start_restore)

        # addon signals - handled by addon_panel connections
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

    def update_install_target_dropdown(self):
        goldrush_dir = self.settings_manager.get_goldrush_directory()
        goldrush_available = bool(goldrush_dir and Path(goldrush_dir).exists())
        self.addon_panel.update_target_options(goldrush_available)

    def load_addons(self):
        self.addon_manager.service.scan_addon_contents()
        self.addon_manager.load_addons(self.addons_list)
        self.apply_saved_addon_selections()

    def refresh_all(self):
        # refresh both particles and addons
        self.mod_drop_zone.update_matrix()
        self.load_addons()

    def get_selected_addons(self):
        # get addons from load order list (which preserves user's drag-drop order)
        load_order = self.addon_panel.get_load_order()

        file_paths = []
        for name in load_order:
            if name in self.addon_manager.addons_file_paths:
                file_paths.append(self.addon_manager.addons_file_paths[name]['file_path'])
        return file_paths

    def on_addon_click(self):
        # when user clicks an addon, show its description
        try:
            selected_items = self.addons_list.selectedItems()
            if selected_items:
                selected_item = selected_items[0]
                addon_name = selected_item.text().split(' [#')[0]

                if addon_name in self.addon_manager.addons_file_paths:
                    addon_info = self.addon_manager.addons_file_paths[addon_name]
                    self.addon_description.update_content(addon_name, addon_info)
                else:
                    self.addon_description.clear()
            else:
                self.addon_description.clear()

        except Exception:
            log.exception("Error in on_addon_click")

    def on_addon_checkbox_changed(self):
        # when checkboxes change, update load order and save
        try:
            # update load order list with numbering and conflicts
            self.update_load_order_display()

            # save load order
            load_order = self.addon_panel.get_load_order()
            self.settings_manager.set_addon_selections(load_order)

        except Exception:
            log.exception("Error in on_addon_checkbox_changed")

    def on_load_order_changed(self):
        # when user drags to reorder, update display and save
        try:
            # update numbering and conflicts for new order
            self.update_load_order_display()

            # save the new order
            load_order = self.addon_panel.get_load_order()
            self.settings_manager.set_addon_selections(load_order)

        except Exception:
            log.exception("Error in on_load_order_changed")

    def update_load_order_display(self):
        # delegate to load order panel
        addon_contents = self.settings_manager.get_addon_contents()
        addon_name_mapping = self.addon_manager.addons_file_paths
        self.addon_panel.load_order_panel.update_display(addon_contents, addon_name_mapping)

    def apply_saved_addon_selections(self):
        saved_selections = self.settings_manager.get_addon_selections()
        if not saved_selections:
            return

        # block signals temporarily
        self.addons_list.blockSignals(True)

        # apply saved checkbox states
        item_map = {}
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item_map[item.text()] = item

        # only include addons that still exist
        valid_selections = []
        for addon_name in saved_selections:
            if addon_name in item_map:
                item_map[addon_name].setCheckState(Qt.CheckState.Checked)
                valid_selections.append(addon_name)

        # restore load order with only valid addons
        self.addon_panel.load_order_panel.restore_order(valid_selections)

        # save the selections if any were removed
        if len(valid_selections) != len(saved_selections):
            self.settings_manager.set_addon_selections(valid_selections)

        self.addons_list.blockSignals(False)
        self.on_addon_checkbox_changed()

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
        thread = threading.Thread(
            target=self.addon_manager.service.scan_addon_contents,
            daemon=True
        )
        thread.start()

    def start_install(self):
        selected_addons = self.get_selected_addons()

        # warn if no addons selected
        if not selected_addons:
            result = QMessageBox.question(
                self,
                "No Addons Selected",
                "No addons selected. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result != QMessageBox.StandardButton.Yes:
                return

        # determine target path based on dropdown selection
        selected_target = self.addon_panel.get_selected_target()
        if selected_target == "goldrush":
            target_path = self.settings_manager.get_goldrush_directory()
            target_name = "Gold Rush"
        else:
            target_path = self.install_manager.tf_path
            target_name = "TF2"

        if not target_path:
            log.error(f"No {target_name} directory configured!", stack_info=True)
            self.show_error(f"No {target_name} directory configured!")
            return

        self.set_processing_state(True)

        self.progress_dialog = QProgressDialog(f"Installing to {target_name}...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Installing")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setFixedSize(275, 100)
        self.progress_dialog.canceled.connect(self.install_manager.cancel_operation)
        self.progress_dialog.show()

        self.install_manager.install(selected_addons, self.mod_drop_zone, target_path)

    def start_restore(self):
        # determine target path based on dropdown selection
        selected_target = self.addon_panel.get_selected_target()
        if selected_target == "goldrush":
            target_path = self.settings_manager.get_goldrush_directory()
            target_name = "Gold Rush"
        else:
            target_path = self.install_manager.tf_path
            target_name = "TF2"

        if not target_path:
            log.error(f"No {target_name} directory configured!", stack_info=True)
            self.show_error(f"No {target_name} directory configured!")
            return

        if self.install_manager.uninstall(target_path):
            self.set_processing_state(True)

            self.progress_dialog = QProgressDialog(f"Restoring {target_name}...", None, 0, 100, self)
            self.progress_dialog.setWindowTitle("Restoring")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.show()

    def update_restore_button_state(self):
        # check based on selected target
        selected_target = self.addon_panel.get_selected_target()
        if selected_target == "goldrush":
            target_path = self.settings_manager.get_goldrush_directory()
        else:
            target_path = self.install_manager.tf_path

        is_modified = self.install_manager.is_modified(target_path)
        self.restore_button.setEnabled(is_modified)

    def set_processing_state(self, processing: bool):
        enabled = not processing
        self.install_button.setEnabled(enabled)
        if not processing:
            self.update_restore_button_state()
        else:
            self.restore_button.setEnabled(False)

    def update_progress(self, progress, message):
        dialog = self.progress_dialog
        if dialog:
            try:
                dialog.setValue(progress)
                dialog.setLabelText(message)
            except (AttributeError, RuntimeError):
                log.exception('Dialog was closed/deleted between check and call')

    def on_operation_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.set_processing_state(False)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_success(self, message):
        QMessageBox.information(self, "Success", message)
        self.show_launch_options_popup()

    def delete_selected_addons(self):
        selected_items = self.addons_list.selectedItems()
        deleted_addon_names = []
        for item in selected_items:
            display_name = item.data(Qt.ItemDataRole.UserRole) or item.text().split(' [#')[0]
            deleted_addon_names.append(display_name)

        success, message = self.addon_manager.delete_selected_addons(self.addons_list)
        if success is None:
            return
        elif success:
            # remove deleted addons from saved load order
            current_load_order = self.settings_manager.get_addon_selections()
            updated_load_order = [name for name in current_load_order if name not in deleted_addon_names]
            self.settings_manager.set_addon_selections(updated_load_order)

            self.load_addons()
        else:
            log.error(message, stack_info=True)
            self.show_error(message)

    def open_addons_folder(self):
        addons_path = folder_setup.addons_dir

        if not addons_path.exists():
            log.error("Addons folder does not exist!", stack_info=True)
            self.show_error("Addons folder does not exist!")
            return

        try:
            if platform == "win32":
                os.startfile(str(addons_path))
            else:
                subprocess.run(["xdg-open", str(addons_path)])
        except Exception:
            log.exception("Failed to open addons folder")
            self.show_error("Failed to open addons folder")

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

            # update Gold Rush directory
            new_goldrush_dir = dialog.get_goldrush_directory()
            self.settings_manager.set_goldrush_directory(new_goldrush_dir)
            self.update_install_target_dropdown()

            # update preloader settings
            self.settings_manager.set_show_console_on_startup(dialog.get_show_console_on_startup())
            self.settings_manager.set_suppress_update_notifications(dialog.get_suppress_update_notifications())
            self.settings_manager.set_skip_launch_options_popup(dialog.get_skip_launch_options_popup())
            self.settings_manager.set_disable_paint_colors(dialog.get_disable_paint_colors())

    def dragEnterEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragLeaveEvent(event)

    def dropEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dropEvent(event)

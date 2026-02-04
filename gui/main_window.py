import logging
import os
import subprocess
import threading
from pathlib import Path
from sys import platform

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.folder_setup import folder_setup
from core.particle_splits import migrate_old_particle_files
from core.services.conflicts import scan_for_legacy_conflicts
from core.version import VERSION
from gui.addons_manager import AddonsManager
from gui.addon_panel import AddonPanel
from gui.mod_drop_zone import ModDropZone
from gui.first_time_setup import download_cueki_mods
from gui.install_controller import InstallController
from gui.profile_dialog import ProfileDialog
from gui.theme import (
    BG_DEFAULT, CODE_BG, FG_DEFAULT, FG_LIGHTER, FG_MUTED,
    FONT_SIZE_HEADER, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, PRIMARY,
    BUTTON_STYLE, DANGER_BUTTON_STYLE, PROFILE_ADD_BUTTON_STYLE,
    PROFILE_BUTTON_STYLE, SIDEBAR_NAV_STYLE,
)
from core.settings import SettingsManager

log = logging.getLogger()


class SidebarNav(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(20, 20))
        self.setSpacing(2)
        self.setStyleSheet(SIDEBAR_NAV_STYLE)


class ParticleManagerGUI(QMainWindow):
    def __init__(self, tf_directory=None):
        super().__init__()
        self.initial_tf_directory = tf_directory

        # managers
        self.settings_manager = SettingsManager()
        self.addon_manager = AddonsManager(self.settings_manager)
        self.install_manager = InstallController(self.settings_manager)

        # UI components
        self.progress_dialog = None
        self.mod_drop_zone: ModDropZone | None = None
        self.addon_panel: AddonPanel | None = None
        self.addons_list = None
        self.addon_description = None
        self.install_button = None
        self.download_mods_button = None
        self.nav_list = None
        self.content_stack = None
        self.profile_add_btn = None

        # settings page widgets
        self.console_checkbox = None
        self.suppress_updates_checkbox = None
        self.skip_launch_popup_checkbox = None
        self.disable_paint_checkbox = None
        self.restore_button = None
        self.current_profile_label = None

        # profile UI
        self.profile_btn = None
        self.profile_menu = None

        # simple mode toggle
        self.simple_mode_btn = None

        # setup
        self.setWindowTitle("cukei's casual pre-loader :)")
        self.setMinimumSize(1200, 700)
        self.resize(1200, 700)
        self.setAcceptDrops(True)
        self.setup_ui()
        self.setup_signals()

        # ensure a profile exists (first-time setup creates tf_directory but not profile)
        if self.initial_tf_directory:
            profiles = self.settings_manager.get_profiles()
            if not profiles:
                self.settings_manager.create_profile("TF2", self.initial_tf_directory)
            else:
                # set the active profile's game_path if needed
                active = self.settings_manager.get_active_profile()
                if active and not active.game_path:
                    self.settings_manager.set_tf_directory(self.initial_tf_directory)

        # load initial data
        self.load_tf_directory()

        # migrate old particle files to new split format
        migrate_old_particle_files()

        # apply saved simple mode preference
        saved_mode = self.settings_manager.get_simple_particle_mode()
        if saved_mode:
            self.mod_drop_zone.conflict_matrix.set_simple_mode(True)
        self.update_simple_mode_button()

        self.mod_drop_zone.update_matrix()

        self.load_addons()
        self.scan_for_mcp_files()
        self.rescan_addon_contents()

        # update profile selector
        self.rebuild_profile_menu()

        # ensure load order display is updated on startup
        self.update_load_order_display()

        # sync settings page with current profile
        self.sync_settings_page()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(150)
        sidebar.setStyleSheet(f"background-color: {CODE_BG};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 8, 0, 8)
        sidebar_layout.setSpacing(0)

        # nav list
        self.nav_list = SidebarNav()
        for name, icon_char in [("Particles", "\u25C6"), ("Addons", "\u25C7"), ("Settings", "\u2699")]:
            leading = " " if platform == "win32" and name == "Settings" else "  "
            item = QListWidgetItem(f"{leading}{icon_char}  {name}")
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(0)
        sidebar_layout.addWidget(self.nav_list)

        # spacer
        sidebar_layout.addStretch()

        # profile selector
        profile_group = QWidget()
        profile_layout = QVBoxLayout(profile_group)
        profile_layout.setContentsMargins(10, 10, 10, 10)

        profile_label = QLabel("Profile")
        profile_label.setStyleSheet(f"color: {FG_MUTED}; font-size: {FONT_SIZE_SMALL};")
        profile_layout.addWidget(profile_label)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(0)

        self.profile_btn = QPushButton(" TF2")
        self.profile_btn.setFixedHeight(28)
        self.profile_btn.setStyleSheet(PROFILE_BUTTON_STYLE)
        self.profile_menu = QMenu(self)
        self.profile_btn.setMenu(self.profile_menu)
        profile_row.addWidget(self.profile_btn, 1)

        self.profile_add_btn = QPushButton("+")
        self.profile_add_btn.setFixedSize(28, 28)
        self.profile_add_btn.setStyleSheet(PROFILE_ADD_BUTTON_STYLE)
        self.profile_add_btn.clicked.connect(self.create_new_profile)
        profile_row.addWidget(self.profile_add_btn, 0)

        profile_layout.addLayout(profile_row)
        sidebar_layout.addWidget(profile_group)

        # install button
        install_container = QWidget()
        install_layout = QVBoxLayout(install_container)
        install_layout.setContentsMargins(10, 0, 10, 10)

        self.install_button = QPushButton("Install")
        self.install_button.setFixedHeight(36)
        self.install_button.setProperty("primary", True)
        self.install_button.setStyleSheet(
            f"background-color: {PRIMARY}; color: white; font-weight: bold; font-size: {FONT_SIZE_NORMAL};"
        )
        install_layout.addWidget(self.install_button)
        sidebar_layout.addWidget(install_container)

        main_layout.addWidget(sidebar, 0)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background-color: {BG_DEFAULT};")

        self.content_stack.addWidget(self.create_particles_page())
        self.content_stack.addWidget(self.create_addons_page())
        self.content_stack.addWidget(self.create_settings_page())

        main_layout.addWidget(self.content_stack, 1)

        # nav connection
        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)

    def create_particles_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Particle Selection")
        header.setStyleSheet(f"font-size: {FONT_SIZE_HEADER}; font-weight: bold; color: {FG_DEFAULT};")
        layout.addWidget(header)

        # mod drop zone (contains conflict matrix)
        self.mod_drop_zone = ModDropZone(self, self.settings_manager, self.rescan_addon_contents)
        layout.addWidget(self.mod_drop_zone, 1)

        # bottom bar
        btn_layout = QHBoxLayout()

        deselect_btn = QPushButton("Deselect All")
        deselect_btn.setStyleSheet(BUTTON_STYLE)
        deselect_btn.clicked.connect(lambda: self.mod_drop_zone.conflict_matrix.deselect_all())
        btn_layout.addWidget(deselect_btn)

        btn_layout.addStretch()

        self.simple_mode_btn = QPushButton("Simple Mode: ON")
        self.simple_mode_btn.setStyleSheet(BUTTON_STYLE)
        self.simple_mode_btn.setCheckable(True)
        self.simple_mode_btn.setChecked(True)
        self.simple_mode_btn.clicked.connect(self.toggle_particle_mode)
        btn_layout.addWidget(self.simple_mode_btn)

        layout.addLayout(btn_layout)
        return page

    def create_addons_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Addon Management")
        header.setStyleSheet(f"font-size: {FONT_SIZE_HEADER}; font-weight: bold; color: {FG_DEFAULT};")
        layout.addWidget(header)

        # addon panel
        self.addon_panel = AddonPanel()
        self.addons_list = self.addon_panel.addons_list
        self.addon_description = self.addon_panel.addon_description

        self.addon_panel.delete_button_clicked.connect(self.delete_selected_addons)
        self.addon_panel.addon_selection_changed.connect(self.on_addon_click)
        self.addon_panel.addon_checkbox_changed.connect(self.on_addon_checkbox_changed)
        self.addon_panel.load_order_changed.connect(self.on_load_order_changed)
        self.addon_panel.open_folder_clicked.connect(self.open_addons_folder)
        self.addon_description.addon_modified.connect(self.load_addons)

        layout.addWidget(self.addon_panel)
        return page

    def create_settings_page(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Settings")
        header.setStyleSheet(f"font-size: {FONT_SIZE_HEADER}; font-weight: bold; color: {FG_DEFAULT};")
        page_layout.addWidget(header)

        # scroll area for settings content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        profile_group = QGroupBox("Profile Settings")
        profile_group_layout = QVBoxLayout(profile_group)

        self.current_profile_label = QLabel("Current profile: TF2")
        self.current_profile_label.setStyleSheet(f"color: {FG_MUTED};")
        profile_group_layout.addWidget(self.current_profile_label)

        profile_btn_layout = QHBoxLayout()
        edit_profile_btn = QPushButton("Edit Profile...")
        edit_profile_btn.setStyleSheet(BUTTON_STYLE)
        edit_profile_btn.clicked.connect(self.edit_current_profile)
        profile_btn_layout.addWidget(edit_profile_btn)

        delete_profile_btn = QPushButton("Delete Profile")
        delete_profile_btn.setStyleSheet(BUTTON_STYLE)
        delete_profile_btn.clicked.connect(self.delete_current_profile)
        profile_btn_layout.addWidget(delete_profile_btn)
        profile_btn_layout.addStretch()
        profile_group_layout.addLayout(profile_btn_layout)

        layout.addWidget(profile_group)

        preloader_group = QGroupBox("Preloader Settings")
        preloader_layout = QVBoxLayout(preloader_group)

        self.console_checkbox = QCheckBox("Enable TF2 console on startup")
        self.console_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_show_console_on_startup(self.console_checkbox.isChecked())
        )
        preloader_layout.addWidget(self.console_checkbox)

        self.suppress_updates_checkbox = QCheckBox("Suppress update notifications")
        self.suppress_updates_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_suppress_update_notifications(self.suppress_updates_checkbox.isChecked())
        )
        preloader_layout.addWidget(self.suppress_updates_checkbox)

        self.skip_launch_popup_checkbox = QCheckBox("Suppress launch options reminder")
        self.skip_launch_popup_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_skip_launch_options_popup(self.skip_launch_popup_checkbox.isChecked())
        )
        preloader_layout.addWidget(self.skip_launch_popup_checkbox)

        self.disable_paint_checkbox = QCheckBox("Disable paint colors on cosmetics")
        self.disable_paint_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_disable_paint_colors(self.disable_paint_checkbox.isChecked())
        )
        preloader_layout.addWidget(self.disable_paint_checkbox)

        layout.addWidget(preloader_group)

        # downloads group
        downloads_group = QGroupBox("Recommended Mods")
        downloads_layout = QHBoxLayout(downloads_group)

        self.download_mods_button = QPushButton("Download cueki's Mods")
        self.download_mods_button.setStyleSheet(BUTTON_STYLE)
        self.download_mods_button.clicked.connect(lambda: download_cueki_mods(self, self.download_mods_button))
        downloads_layout.addWidget(self.download_mods_button)

        downloads_desc = QLabel("TF2 particles + addons personally fixed to work with this preloader (~77 MB)")
        downloads_desc.setStyleSheet(f"color: {FG_MUTED};")
        downloads_desc.setWordWrap(True)
        downloads_layout.addWidget(downloads_desc, 1)

        layout.addWidget(downloads_group)

        # restore group
        restore_group = QGroupBox("Restore")
        restore_layout = QHBoxLayout(restore_group)

        self.restore_button = QPushButton("Restore Game Files")
        self.restore_button.setStyleSheet(DANGER_BUTTON_STYLE)
        self.restore_button.clicked.connect(self.start_restore)
        restore_layout.addWidget(self.restore_button)

        restore_desc = QLabel("Remove all installed mods and restore the game to its original state.")
        restore_desc.setStyleSheet(f"color: {FG_MUTED};")
        restore_desc.setWordWrap(True)
        restore_layout.addWidget(restore_desc, 1)

        layout.addWidget(restore_group)

        layout.addStretch()

        # version label
        version_label = QLabel(f"Version: {VERSION}")
        version_label.setStyleSheet(f"color: {FG_LIGHTER};")
        layout.addWidget(version_label)

        scroll.setWidget(scroll_content)
        page_layout.addWidget(scroll)
        return page

    def setup_signals(self):
        self.install_button.clicked.connect(self.start_install)

        self.mod_drop_zone.addon_updated.connect(self.load_addons)

        self.install_manager.progress_update.connect(self.update_progress)
        self.install_manager.operation_error.connect(self.show_error)
        self.install_manager.operation_success.connect(self.show_success)
        self.install_manager.operation_finished.connect(self.on_operation_finished)

    def toggle_particle_mode(self):
        current_state = self.settings_manager.get_simple_particle_mode()
        new_state = not current_state

        if self.mod_drop_zone and self.mod_drop_zone.conflict_matrix:
            self.mod_drop_zone.conflict_matrix.set_simple_mode(new_state)
        self.settings_manager.set_simple_particle_mode(new_state)
        self.update_simple_mode_button()

    def update_simple_mode_button(self):
        is_simple = self.settings_manager.get_simple_particle_mode()
        self.simple_mode_btn.blockSignals(True)
        self.simple_mode_btn.setChecked(is_simple)
        self.simple_mode_btn.setText(f"Simple Mode: {'ON' if is_simple else 'OFF'}")
        self.simple_mode_btn.blockSignals(False)

    def rebuild_profile_menu(self):
        self.profile_menu.clear()
        profiles = self.settings_manager.get_profiles()
        active = self.settings_manager.get_active_profile()

        for p in profiles:
            action = self.profile_menu.addAction(p.name)
            action.triggered.connect(lambda checked, pid=p.id: self.switch_profile(pid))

        if active:
            self.profile_btn.setText(f" {active.name}")

    def switch_profile(self, profile_id):
        active = self.settings_manager.get_active_profile()
        if active and active.id == profile_id:
            return

        # save current state
        load_order = self.addon_panel.get_load_order()
        self.settings_manager.set_addon_selections(load_order)

        # switch
        self.settings_manager.set_active_profile(profile_id)

        new_profile = self.settings_manager.get_active_profile()
        if new_profile:
            self.profile_btn.setText(f" {new_profile.name}")

            # update install manager path
            self.install_manager.set_tf_path(new_profile.game_path)

            # reload addons (different selections per profile)
            self.load_addons()

            # reload conflict matrix (simple mode may differ per profile)
            new_simple = self.settings_manager.get_simple_particle_mode()
            if self.mod_drop_zone and self.mod_drop_zone.conflict_matrix:
                self.mod_drop_zone.conflict_matrix.set_simple_mode(new_simple)
            self.update_simple_mode_button()
            self.mod_drop_zone.update_matrix()

            # sync settings page
            self.sync_settings_page()

            self.update_load_order_display()

    def create_new_profile(self):
        dialog = ProfileDialog(self)
        if dialog.exec():
            name = dialog.get_name()
            game_path = dialog.get_game_path()
            game_target = dialog.get_game_target()
            profile = self.settings_manager.create_profile(name, game_path, game_target)
            self.rebuild_profile_menu()
            self.switch_profile(profile.id)

    def edit_current_profile(self):
        active = self.settings_manager.get_active_profile()
        if not active:
            return
        dialog = ProfileDialog(self, name=active.name, game_path=active.game_path, game_target=active.game_target)
        if dialog.exec():
            self.settings_manager.update_profile(
                active.id,
                name=dialog.get_name(),
                game_path=dialog.get_game_path(),
                game_target=dialog.get_game_target(),
            )
            self.rebuild_profile_menu()

            # update path if changed
            updated = self.settings_manager.get_active_profile()
            if updated:
                self.install_manager.set_tf_path(updated.game_path)
                self.sync_settings_page()

    def delete_current_profile(self):
        active = self.settings_manager.get_active_profile()
        if not active:
            return
        profiles = self.settings_manager.get_profiles()
        if len(profiles) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "You must have at least one profile.")
            return
        result = QMessageBox.question(
            self, "Delete Profile",
            f"Delete profile '{active.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.settings_manager.delete_profile(active.id)
            self.rebuild_profile_menu()
            new_active = self.settings_manager.get_active_profile()
            if new_active:
                self.switch_profile(new_active.id)

    def sync_settings_page(self):
        active = self.settings_manager.get_active_profile()
        if not active:
            return

        self.current_profile_label.setText(f"Current profile: {active.name}")

        # block signals while syncing checkboxes
        for cb in [self.console_checkbox, self.suppress_updates_checkbox,
                    self.skip_launch_popup_checkbox, self.disable_paint_checkbox]:
            cb.blockSignals(True)

        self.console_checkbox.setChecked(self.settings_manager.get_show_console_on_startup())
        self.suppress_updates_checkbox.setChecked(self.settings_manager.get_suppress_update_notifications())
        self.skip_launch_popup_checkbox.setChecked(self.settings_manager.get_skip_launch_options_popup())
        self.disable_paint_checkbox.setChecked(self.settings_manager.get_disable_paint_colors())

        for cb in [self.console_checkbox, self.suppress_updates_checkbox,
                    self.skip_launch_popup_checkbox, self.disable_paint_checkbox]:
            cb.blockSignals(False)

        self.update_restore_button_state()

    def load_tf_directory(self):
        tf_dir = self.settings_manager.get_tf_directory()
        if tf_dir and Path(tf_dir).exists():
            self.install_manager.set_tf_path(tf_dir)

    def load_addons(self):
        self.addon_manager.service.scan_addon_contents()
        self.addon_manager.load_addons(self.addons_list)
        self.apply_saved_addon_selections()

    def refresh_all(self):
        self.mod_drop_zone.update_matrix()
        self.load_addons()

    def get_selected_addons(self):
        load_order = self.addon_panel.get_load_order()
        file_paths = []
        for name in load_order:
            if name in self.addon_manager.addons_file_paths:
                file_paths.append(self.addon_manager.addons_file_paths[name]['file_path'])
        return file_paths

    def on_addon_click(self):
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
        try:
            self.update_load_order_display()
            load_order = self.addon_panel.get_load_order()
            self.settings_manager.set_addon_selections(load_order)
        except Exception:
            log.exception("Error in on_addon_checkbox_changed")

    def on_load_order_changed(self):
        try:
            self.update_load_order_display()
            load_order = self.addon_panel.get_load_order()
            self.settings_manager.set_addon_selections(load_order)
        except Exception:
            log.exception("Error in on_load_order_changed")

    def update_load_order_display(self):
        addon_contents = self.settings_manager.get_addon_contents()
        addon_name_mapping = self.addon_manager.addons_file_paths
        self.addon_panel.load_order_panel.update_display(addon_contents, addon_name_mapping)

    def apply_saved_addon_selections(self):
        saved_selections = self.settings_manager.get_addon_selections()
        if not saved_selections:
            return

        self.addons_list.blockSignals(True)

        item_map = {}
        for i in range(self.addons_list.count()):
            item = self.addons_list.item(i)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item_map[item.text()] = item

        valid_selections = []
        for addon_name in saved_selections:
            if addon_name in item_map:
                item_map[addon_name].setCheckState(Qt.CheckState.Checked)
                valid_selections.append(addon_name)

        self.addon_panel.load_order_panel.restore_order(valid_selections)

        if len(valid_selections) != len(saved_selections):
            self.settings_manager.set_addon_selections(valid_selections)

        self.addons_list.blockSignals(False)
        self.on_addon_checkbox_changed()

    def scan_for_mcp_files(self):
        tf_path = self.install_manager.tf_path
        if not tf_path:
            return

        custom_dir = Path(tf_path) / 'custom'
        found_conflicts = scan_for_legacy_conflicts(custom_dir)

        if found_conflicts:
            conflict_list = "\n\u2022 ".join(found_conflicts)
            QMessageBox.warning(
                self,
                "Conflicting Files Detected",
                f"The following items in your custom folder may conflict with this method:\n\n\u2022 {conflict_list}\n\nIt's recommended to remove these to avoid issues."
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

        if not selected_addons:
            result = QMessageBox.question(
                self, "No Addons Selected", "No addons selected. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        target_path = self.install_manager.tf_path
        if not target_path:
            log.error("No game directory configured!", stack_info=True)
            self.show_error("No game directory configured! Set it in Settings.")
            return

        self.set_processing_state(True)

        active = self.settings_manager.get_active_profile()
        target_name = active.name if active else "game"

        self.progress_dialog = QProgressDialog(f"Installing to {target_name}...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Installing")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setFixedSize(275, 100)
        self.progress_dialog.canceled.connect(self.install_manager.cancel_operation)
        self.progress_dialog.show()

        self.install_manager.install(selected_addons, self.mod_drop_zone, target_path)

    def start_restore(self):
        target_path = self.install_manager.tf_path
        if not target_path:
            log.error("No game directory configured!", stack_info=True)
            self.show_error("No game directory configured!")
            return

        active = self.settings_manager.get_active_profile()
        target_name = active.name if active else Path(target_path).name

        result = QMessageBox.question(
            self,
            "Confirm Restore",
            f"This will revert all changes made to {target_name} by this app.\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if result != QMessageBox.StandardButton.Yes:
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

    def dragEnterEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dragLeaveEvent(event)

    def dropEvent(self, event):
        if hasattr(self, 'mod_drop_zone') and self.mod_drop_zone:
            self.mod_drop_zone.dropEvent(event)

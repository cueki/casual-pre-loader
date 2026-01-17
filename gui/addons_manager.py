from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox

from core.services.addons import AddonService


class AddonsManager(QObject):
    # Qt wrapper for AddonService

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.service = AddonService(settings_manager)

    @property
    def addons_file_paths(self) -> dict:
        # compatibility for main_window
        return self.service.addons_cache

    def load_addons(self, addons_list):
        # populate QListWidget with grouped addons
        addon_groups = self.service.get_addons_grouped()

        addons_list.blockSignals(True)
        addons_list.clear()
        addons_list.blockSignals(False)

        # group splitters
        for addon_type in addon_groups:
            if addon_type != "unknown":
                splitter = QListWidgetItem("──── " + str.title(addon_type) + " ────")
                splitter.setFlags(Qt.ItemFlag.NoItemFlags)
                splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                addons_list.addItem(splitter)

                for addon_info_dict in addon_groups[addon_type]:
                    item = QListWidgetItem(addon_info_dict['addon_name'])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    addons_list.addItem(item)

        if addon_groups.get("unknown"):
            splitter = QListWidgetItem("──── Unknown Addons ────")
            splitter.setFlags(Qt.ItemFlag.NoItemFlags)
            splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            addons_list.addItem(splitter)

            for addon_info_dict in addon_groups["unknown"]:
                item = QListWidgetItem(addon_info_dict['addon_name'])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                addons_list.addItem(item)

    def delete_selected_addons(self, addons_list):
        selected_items = addons_list.selectedItems()
        if not selected_items:
            return False, "No addons selected for deletion."

        selected_addon_names = []
        selected_folder_names = []
        for item in selected_items:
            display_name = item.data(Qt.ItemDataRole.UserRole) or item.text().split(' [#')[0]
            selected_addon_names.append(display_name)
            if display_name in self.addons_file_paths:
                folder_name = self.addons_file_paths[display_name]['file_path']
                selected_folder_names.append(folder_name)
            else:
                selected_folder_names.append(display_name)

        addon_list = "\n• ".join(selected_addon_names)
        result = QMessageBox.warning(
            None,
            "Confirm Deletion",
            f"The following addons will be permanently deleted:\n\n• {addon_list}\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # this forces default to "no" if someone spams enter (me)
        )

        if result != QMessageBox.StandardButton.Yes:
            return None, None

        # delegated to service
        success, message = self.service.delete_addons(selected_folder_names)
        return success, message

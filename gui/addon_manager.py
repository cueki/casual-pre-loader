import json
import shutil
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox
from PyQt6.QtCore import Qt, QObject
from core.folder_setup import folder_setup


class AddonManager(QObject):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.addons_file_paths = {}

    def load_addons(self, addons_list):
        addons_dir = folder_setup.addons_dir
        # block the signal so the addons list doesn't clear in the app_settings.json
        addons_list.blockSignals(True)
        addons_list.clear()
        addons_list.blockSignals(False)
        addon_groups = {"texture": [], "model": [], "misc": [], "animation": [], "unknown": []}

        for addon_path in addons_dir.iterdir():
            if addon_path.is_dir():
                addon_info = self.load_addon_info(addon_path.name)
                addon_type = addon_info.get("type", "unknown").lower()
                if addon_type not in addon_groups:
                    addon_groups[addon_type] = []
                addon_groups[addon_type].append(addon_info)

        # sort the addon groups alphabetically
        addon_groups = {group: addon_groups[group] for group in sorted(addon_groups)}

        # sort the addons in each group alphabetically based on mod.json name
        for group in addon_groups:
            addon_groups[group].sort(key=lambda x: x['addon_name'].lower())

        # add addons to list widget with group splitters
        for addon_type in addon_groups:
            if addon_type != "unknown" and addon_groups[addon_type]:
                splitter = QListWidgetItem("──── " + str.title(addon_type) + " ────")
                splitter.setFlags(Qt.ItemFlag.NoItemFlags)
                splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                addons_list.addItem(splitter)

                for addon_info_dict in addon_groups[addon_type]:
                    item = QListWidgetItem(addon_info_dict['addon_name'])
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    addons_list.addItem(item)
                    self.addons_file_paths[addon_info_dict['addon_name']] = addon_info_dict

        # add unknown addons at the end
        if addon_groups["unknown"]:
            splitter = QListWidgetItem("──── Unknown Addons ────")
            splitter.setFlags(Qt.ItemFlag.NoItemFlags)
            splitter.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            addons_list.addItem(splitter)

            for addon_info_dict in addon_groups["unknown"]:
                item = QListWidgetItem(addon_info_dict['addon_name'])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                addons_list.addItem(item)
                self.addons_file_paths[addon_info_dict['addon_name']] = addon_info_dict

    @staticmethod
    def load_addon_info(addon_name: str) -> dict:
        addon_path = folder_setup.addons_dir / addon_name
        try:
            mod_json_path = addon_path / 'mod.json'
            if mod_json_path.exists():
                with open(mod_json_path, 'r') as addon_json:
                    try:
                        addon_info = json.load(addon_json)
                        addon_info['file_path'] = addon_name
                        return addon_info
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass

        # default
        return {
            "addon_name": addon_name,
            "type": "Unknown",
            "description": "",
            "contents": ["Custom content"],
            "file_path": addon_name
        }

    def scan_addon_contents(self):
        addon_metadata = self.settings_manager.get_addon_metadata() or {}
        addons_dir = folder_setup.addons_dir
        addons = [d for d in addons_dir.iterdir() if d.is_dir()]
        processed = 0
        new_or_updated = 0

        for addon_dir in addons:
            addon_name = addon_dir.name
            # get the last modified time of the most recently changed file
            last_modified = max((f.stat().st_mtime for f in addon_dir.glob('**/*') if f.is_file()), default=0)
            processed += 1

            # check if addon has been scanned before and hasn't changed
            if (addon_name in addon_metadata and
                    addon_metadata[addon_name].get('last_modified') == last_modified):
                continue

            # addon is new or modified, scan it
            try:
                addon_files = []
                for file_path in addon_dir.glob('**/*'):
                    if file_path.is_file() and file_path.name != 'mod.json' and file_path.name != 'sound.cache':
                        rel_path = str(file_path.relative_to(addon_dir))
                        addon_files.append(rel_path)

                new_or_updated += 1

                if addon_name not in addon_metadata:
                    addon_metadata[addon_name] = {}

                addon_metadata[addon_name].update({
                    'last_modified': last_modified,
                    'files': addon_files,
                    'file_count': len(addon_files)
                })

            except Exception as e:
                print(f"Error scanning {addon_name}: {e}")

        self.settings_manager.set_addon_metadata(addon_metadata)
        return new_or_updated > 0

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
            QMessageBox.StandardButton.No # this forces default to "no" if someone spams enter (me)
        )

        if result != QMessageBox.StandardButton.Yes:
            return None, None

        errors = []
        for display_name, folder_name in zip(selected_addon_names, selected_folder_names):
            addon_path = folder_setup.addons_dir / folder_name
            if addon_path.exists() and addon_path.is_dir():
                try:
                    shutil.rmtree(addon_path)
                except Exception as e:
                    errors.append(f"Failed to delete {display_name}: {str(e)}")

        if errors:
            return False, "\n".join(errors)

        # update addon_metadata.json
        addon_metadata = self.settings_manager.get_addon_metadata()
        for folder_name in selected_folder_names:
            if folder_name in addon_metadata:
                del addon_metadata[folder_name]

        self.settings_manager.set_addon_metadata(addon_metadata)
        return True, "Selected addons have been deleted."
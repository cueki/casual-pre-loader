import json
from pathlib import Path


class SettingsManager:
    # listen up students, in this class we will learn how to write java getters and setters
    def __init__(self, settings_file="app_settings.json"):
        self.settings_file = Path(settings_file)
        self.settings = self._load_settings()

    def _load_settings(self):
        default_settings = {
            "last_directory": "",
            "addon_selections": [],
            "matrix_selections": {},
            "prop_filter_checkbox": False
        }

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")

        return default_settings

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_last_directory(self):
        return self.settings.get("last_directory", "")

    def set_last_directory(self, directory):
        self.settings["last_directory"] = directory
        self.save_settings()

    def get_addon_selections(self):
        return self.settings.get("addon_selections", [])

    def set_addon_selections(self, selections):
        self.settings["addon_selections"] = selections
        self.save_settings()

    def get_matrix_selections(self):
        return self.settings.get("matrix_selections", {})

    def set_matrix_selections(self, selections):
        self.settings["matrix_selections"] = selections
        self.save_settings()

    def get_prop_filter_state(self):
        return self.settings.get("prop_filter_checkbox", False)

    def set_prop_filter_state(self, enabled):
        self.settings["prop_filter_checkbox"] = enabled
        self.save_settings()

    def get_addon_contents(self):
        metadata = self.get_addon_metadata()
        return {name: data.get('files', []) for name, data in metadata.items()}

    def get_addon_metadata(self):
        return self.settings.get("addon_metadata", {})

    def set_addon_metadata(self, metadata):
        self.settings["addon_metadata"] = metadata
        self.save_settings()

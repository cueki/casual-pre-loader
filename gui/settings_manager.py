import json
import logging
from pathlib import Path

from core.folder_setup import folder_setup

log = logging.getLogger()


def validate_tf_directory(directory, validation_label=None):
    if not directory:
        if validation_label:
            validation_label.setText("")
        return False

    tf_path = Path(directory)

    # check if directory exists
    if not tf_path.exists():
        if validation_label:
            validation_label.setText("Directory does not exist!")
            validation_label.setStyleSheet("color: red;")
        return False

    # check if it's actually a tf directory
    if not (tf_path.name == "tf" or tf_path.name.endswith("/tf")):
        if validation_label:
            validation_label.setText("Selected directory should be named 'tf'")
            validation_label.setStyleSheet("color: orange;")

    # check for gameinfo.txt
    if not (tf_path / "gameinfo.txt").exists():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid tf/ directory")
            validation_label.setStyleSheet("color: red;")
        return False

    # check for tf2_misc_dir.vpk
    if not (tf_path / "tf2_misc_dir.vpk").exists():
        if validation_label:
            validation_label.setText("tf2_misc_dir.vpk not found - some features may not work")
            validation_label.setStyleSheet("color: orange;")
    else:
        if validation_label:
            validation_label.setText("Valid TF2 directory detected!")
            validation_label.setStyleSheet("color: green;")

    return True


def validate_goldrush_directory(directory, validation_label=None):
    if not directory:
        if validation_label:
            validation_label.setText("")
        return False

    gr_path = Path(directory)

    # check if directory exists
    if not gr_path.exists():
        if validation_label:
            validation_label.setText("Directory does not exist!")
            validation_label.setStyleSheet("color: red;")
        return False

    # check if it's actually a tf_goldrush directory
    if not (gr_path.name == "tf_goldrush" or gr_path.name.endswith("/tf_goldrush")):
        if validation_label:
            validation_label.setText("Selected directory should be named 'tf_goldrush'")
            validation_label.setStyleSheet("color: orange;")

    # check for gameinfo.txt
    if not (gr_path / "gameinfo.txt").exists():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid tf_goldrush/ directory")
            validation_label.setStyleSheet("color: red;")
        return False

    # check for tf_goldrush_dir.vpk
    if not (gr_path / "tf_goldrush_dir.vpk").exists():
        if validation_label:
            validation_label.setText("tf_goldrush_dir.vpk not found - some features may not work")
            validation_label.setStyleSheet("color: orange;")
    else:
        if validation_label:
            validation_label.setText("Valid Gold Rush directory detected!")
            validation_label.setStyleSheet("color: green;")

    return True


def auto_detect_tf2():
    common_paths = [
        "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
        "D:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
        "~/.steam/steam/steamapps/common/Team Fortress 2/tf",
        "~/.local/share/Steam/steamapps/common/Team Fortress 2/tf",
    ]

    for path_str in common_paths:
        path = Path(path_str).expanduser()
        if path.exists() and (path / "gameinfo.txt").exists():
            return str(path)
    return None


def auto_detect_goldrush():
    common_paths = [
        "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "D:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "~/.steam/steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "~/.local/share/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
    ]

    for path_str in common_paths:
        path = Path(path_str).expanduser()
        if path.exists() and (path / "gameinfo.txt").exists():
            return str(path)
    return None


class SettingsManager:
    # listen up students, in this class we will learn how to write java getters and setters
    def __init__(self, settings_file="app_settings.json", metadata_file="addon_metadata.json"):
        folder_setup.settings_dir.mkdir(parents=True, exist_ok=True)  # Ensure that settings directory exists

        self.settings_file = folder_setup.settings_dir / settings_file
        self.metadata_file = folder_setup.settings_dir / metadata_file

        self.settings = self._load_settings()
        self.addon_metadata = self._load_metadata()

    def _load_settings(self):
        default_settings = {
            "tf_directory": "",
            "goldrush_directory": "",
            "addon_selections": [],
            "matrix_selections": {},
            "matrix_selections_simple": {},
            "simple_particle_mode": True,
            "skip_launch_options_popup": False,
            "suppress_update_notifications": False,
            "skipped_update_version": None,
            "show_console_on_startup": True
        }

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading settings")

        return default_settings

    def _load_metadata(self):
        default_metadata = {
            "addon_contents": {},
            "addon_metadata": {}
        }

        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading addon metadata")

        return default_metadata

    def save_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            log.exception("Error saving settings")

    def save_metadata(self):
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.addon_metadata, f, indent=2)
        except Exception:
            log.exception("Error saving addon metadata")

    def get_tf_directory(self):
        return self.settings.get("tf_directory", "")

    def set_tf_directory(self, directory):
        self.settings["tf_directory"] = directory
        self.save_settings()

    def get_goldrush_directory(self):
        return self.settings.get("goldrush_directory", "")

    def set_goldrush_directory(self, directory):
        self.settings["goldrush_directory"] = directory
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

    def get_matrix_selections_simple(self):
        return self.settings.get("matrix_selections_simple", {})

    def set_matrix_selections_simple(self, selections):
        self.settings["matrix_selections_simple"] = selections
        self.save_settings()

    def get_simple_particle_mode(self):
        return self.settings.get("simple_particle_mode", True)

    def set_simple_particle_mode(self, enabled):
        self.settings["simple_particle_mode"] = enabled
        self.save_settings()

    def get_addon_metadata(self):
        return self.addon_metadata.get("addon_metadata", {})

    def set_addon_metadata(self, metadata):
        self.addon_metadata["addon_metadata"] = metadata
        self.save_metadata()

    def get_addon_contents(self):
        metadata = self.get_addon_metadata()
        return {name: data.get('files', []) for name, data in metadata.items()}

    def get_skip_launch_options_popup(self):
        return self.settings.get("skip_launch_options_popup", False)

    def set_skip_launch_options_popup(self, skip_popup):
        self.settings["skip_launch_options_popup"] = skip_popup
        self.save_settings()

    def get_suppress_update_notifications(self):
        return self.settings.get("suppress_update_notifications", False)

    def set_suppress_update_notifications(self, suppress):
        self.settings["suppress_update_notifications"] = suppress
        self.save_settings()

    def get_skipped_update_version(self):
        return self.settings.get("skipped_update_version", None)

    def set_skipped_update_version(self, version):
        self.settings["skipped_update_version"] = version
        self.save_settings()

    def should_show_update_dialog(self, version):
        if self.get_suppress_update_notifications():
            return False
        return version != self.get_skipped_update_version()

    def get_show_console_on_startup(self):
        return self.settings.get("show_console_on_startup", True)

    def set_show_console_on_startup(self, show_console):
        self.settings["show_console_on_startup"] = show_console
        self.save_settings()

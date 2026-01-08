import json
import logging

from core.folder_setup import folder_setup

log = logging.getLogger()


class SettingsManager:
    def __init__(self):
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
            "show_console_on_startup": True,
            "disable_paint_colors": False
        }

        if folder_setup.app_settings_file.exists():
            try:
                with open(folder_setup.app_settings_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading settings")

        return default_settings

    def _load_metadata(self):
        default_metadata = {
            "addon_contents": {},
            "addon_metadata": {}
        }

        if folder_setup.addon_metadata_file.exists():
            try:
                with open(folder_setup.addon_metadata_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading addon metadata")

        return default_metadata

    def save_settings(self):
        try:
            folder_setup.app_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(folder_setup.app_settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            log.exception("Error saving settings")

    def save_metadata(self):
        try:
            folder_setup.addon_metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(folder_setup.addon_metadata_file, "w") as f:
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

    def get_disable_paint_colors(self):
        return self.settings.get("disable_paint_colors", False)

    def set_disable_paint_colors(self, disable):
        self.settings["disable_paint_colors"] = disable
        self.save_settings()

    def get_mod_urls(self):
        if folder_setup.mod_urls_file.exists():
            try:
                with open(folder_setup.mod_urls_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading mod URLs")
        return {}

    def set_mod_urls(self, urls):
        try:
            with open(folder_setup.mod_urls_file, "w") as f:
                json.dump(urls, f, indent=2)
        except Exception:
            log.exception("Error saving mod URLs")

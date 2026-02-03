import json
import logging
import uuid

from core.folder_setup import folder_setup
from core.profile import Profile

log = logging.getLogger()


class SettingsManager:
    @staticmethod
    def is_first_time_setup() -> bool:
        return not folder_setup.app_settings_file.exists()

    def __init__(self):
        self.settings = self._load_settings()
        self.addon_metadata = self._load_metadata()

    def _load_settings(self):
        default_settings = {
            "active_profile_id": None,
            "profiles": [],
            "skip_launch_options_popup": False,
            "suppress_update_notifications": False,
            "skipped_update_version": None,
        }

        if folder_setup.app_settings_file.exists():
            try:
                with open(folder_setup.app_settings_file, "r") as f:
                    data = json.load(f)

                # migrate old flat format to profile format
                if "tf_directory" in data and "profiles" not in data:
                    return self._migrate_flat_settings(data)

                return data
            except Exception:
                log.exception("Error loading settings")

        return default_settings

    @staticmethod
    def _migrate_flat_settings(old):
        """Migrate old settings to profile-based format."""
        profiles = []

        # create TF2 profile from existing settings
        tf_profile = Profile(
            id=str(uuid.uuid4()),
            name="TF2",
            game_path=old.get("tf_directory", ""),
            addon_selections=old.get("addon_selections", []),
            matrix_selections=old.get("matrix_selections", {}),
            matrix_selections_simple=old.get("matrix_selections_simple", {}),
            simple_particle_mode=old.get("simple_particle_mode", True),
            show_console_on_startup=old.get("show_console_on_startup", True),
            disable_paint_colors=old.get("disable_paint_colors", False),
        )
        profiles.append(tf_profile.to_dict())

        # create Gold Rush profile if configured
        goldrush_dir = old.get("goldrush_directory", "")
        if goldrush_dir:
            gr_profile = Profile(
                id=str(uuid.uuid4()),
                name="Gold Rush",
                game_path=goldrush_dir,
            )
            profiles.append(gr_profile.to_dict())

        settings = {
            "active_profile_id": profiles[0]["id"],
            "profiles": profiles,
            "skip_launch_options_popup": old.get("skip_launch_options_popup", False),
            "suppress_update_notifications": old.get("suppress_update_notifications", False),
            "skipped_update_version": old.get("skipped_update_version", None),
        }

        log.info(f"Migrated old settings to profile format ({len(profiles)} profile(s))")
        return settings

    @staticmethod
    def _load_metadata():
        default_metadata = {
            "addon_contents": {},
            "addon_metadata": {}
        }

        if folder_setup.addon_metadata_file.exists():
            try:
                with open(folder_setup.addon_metadata_file, "r") as f:
                    content = f.read()
                    if content:
                        return json.loads(content)
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

    def get_profiles(self) -> list[Profile]:
        return [Profile.from_dict(p) for p in self.settings.get("profiles", [])]

    def get_active_profile(self) -> Profile | None:
        profiles = self.get_profiles()
        if not profiles:
            return None

        active_id = self.settings.get("active_profile_id")
        for p in profiles:
            if p.id == active_id:
                return p

        # fallback to first profile
        return profiles[0]

    def set_active_profile(self, profile_id: str):
        self.settings["active_profile_id"] = profile_id
        self.save_settings()

    def create_profile(self, name: str, game_path: str, game_target: str = "Team Fortress 2") -> Profile:
        profile = Profile.create(name, game_path, game_target)
        profiles = self.settings.get("profiles", [])
        profiles.append(profile.to_dict())
        self.settings["profiles"] = profiles

        # if this is the first profile, make it active
        if len(profiles) == 1:
            self.settings["active_profile_id"] = profile.id

        self.save_settings()
        return profile

    def update_profile(self, profile_id: str, **kwargs):
        profiles = self.settings.get("profiles", [])
        for i, p in enumerate(profiles):
            if p["id"] == profile_id:
                for key, value in kwargs.items():
                    p[key] = value
                profiles[i] = p
                break
        self.settings["profiles"] = profiles
        self.save_settings()

    def delete_profile(self, profile_id: str):
        profiles = self.settings.get("profiles", [])
        profiles = [p for p in profiles if p["id"] != profile_id]
        self.settings["profiles"] = profiles

        # if we deleted the active profile, switch to first remaining
        if self.settings.get("active_profile_id") == profile_id and profiles:
            self.settings["active_profile_id"] = profiles[0]["id"]

        self.save_settings()

    def _get_active_profile_dict(self) -> dict | None:
        active_id = self.settings.get("active_profile_id")
        for p in self.settings.get("profiles", []):
            if p["id"] == active_id:
                return p
        profiles = self.settings.get("profiles", [])
        return profiles[0] if profiles else None

    def _set_active_profile_field(self, key, value):
        profile = self._get_active_profile_dict()
        if profile:
            profile[key] = value
            self.save_settings()

    def get_tf_directory(self):
        profile = self._get_active_profile_dict()
        return profile.get("game_path", "") if profile else ""

    def set_tf_directory(self, directory):
        self._set_active_profile_field("game_path", directory)

    def get_addon_selections(self):
        profile = self._get_active_profile_dict()
        return profile.get("addon_selections", []) if profile else []

    def set_addon_selections(self, selections):
        self._set_active_profile_field("addon_selections", selections)

    def get_matrix_selections(self):
        profile = self._get_active_profile_dict()
        return profile.get("matrix_selections", {}) if profile else {}

    def set_matrix_selections(self, selections):
        self._set_active_profile_field("matrix_selections", selections)

    def get_matrix_selections_simple(self):
        profile = self._get_active_profile_dict()
        return profile.get("matrix_selections_simple", {}) if profile else {}

    def set_matrix_selections_simple(self, selections):
        self._set_active_profile_field("matrix_selections_simple", selections)

    def get_simple_particle_mode(self):
        profile = self._get_active_profile_dict()
        return profile.get("simple_particle_mode", True) if profile else True

    def set_simple_particle_mode(self, enabled):
        self._set_active_profile_field("simple_particle_mode", enabled)

    def get_show_console_on_startup(self):
        profile = self._get_active_profile_dict()
        return profile.get("show_console_on_startup", True) if profile else True

    def set_show_console_on_startup(self, show_console):
        self._set_active_profile_field("show_console_on_startup", show_console)

    def get_disable_paint_colors(self):
        profile = self._get_active_profile_dict()
        return profile.get("disable_paint_colors", False) if profile else False

    def set_disable_paint_colors(self, disable):
        self._set_active_profile_field("disable_paint_colors", disable)

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

    def get_addon_metadata(self):
        return self.addon_metadata.get("addon_metadata", {})

    def set_addon_metadata(self, metadata):
        self.addon_metadata["addon_metadata"] = metadata
        self.save_metadata()

    def get_addon_contents(self):
        metadata = self.get_addon_metadata()
        return {name: data.get('files', []) for name, data in metadata.items()}

    @staticmethod
    def get_mod_urls():
        if folder_setup.mod_urls_file.exists():
            try:
                with open(folder_setup.mod_urls_file, "r") as f:
                    return json.load(f)
            except Exception:
                log.exception("Error loading mod URLs")
        return {}

    @staticmethod
    def set_mod_urls(urls):
        try:
            with open(folder_setup.mod_urls_file, "w") as f:
                json.dump(urls, f, indent=2)
        except Exception:
            log.exception("Error saving mod URLs")

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Type
from uuid import UUID

from packaging.version import Version

from core.constants import Sourcemods
from core.profile import Profile
from core.util import as_base_class, update_dataclass

# https://github.com/python/typing/issues/182#issuecomment-1320974824
type JSON = dict[str, 'JSON'] | list['JSON'] | str | int | float | bool | None


class NoActiveProfile(AttributeError):
    pass


class ProfileNotFound(KeyError):
    pass


@dataclass(frozen=True)
class SerializationSpec[T: Type]:
    type: T
    """The type to encode"""

    encode: Callable[[T], JSON]
    """Function used to encode value to JSON"""


class SerializationSpecs(SerializationSpec, Enum):
    PATH = Path, str
    VERSION = Version, str
    UUID = UUID, str


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            for spec in SerializationSpecs: # we can't just do a mapping lookup because we also want to match subclasses
                if isinstance(o, spec.type):
                    return spec.encode(o)
            raise


@dataclass
class Settings:
    active_profile: Profile | None = None
    details_collapsed: bool = False
    done_initial_setup: bool = False
    profiles: list[Profile] = field(default_factory=list)
    skip_launch_options_popup: bool = False
    skipped_update_version: Version | None = None
    suppress_update_notifications: bool = False

    def __post_init__(self) -> None:
        self._load_settings()

    def __getattr__(self, attr):
        if self.active_profile is None:
            raise NoActiveProfile(attr)

        return getattr(self.active_profile, attr)

    def __setattr__(self, attr, value, /):
        if attr == 'active_profile':
            if value not in self.profiles:
                for profile in self.profiles:
                    if profile.id == value:
                        value = profile
                        break
                else:
                    raise ValueError(f'{value} is not a known profile ID')
        elif attr == 'profiles':
            raise AttributeError('profiles may not be set manually, use `create_profile()`/`delete_profile()`')

        if attr in self.__dict__:
            super().__setattr__(attr, value)
        else:
            if self.active_profile is None:
                raise NoActiveProfile(attr)

            setattr(self.active_profile, attr, value)

        self.save_settings()

    def _load_settings(self, input_settings_file: Path | None = None) -> None:
        """
        Loads settings from an optional file (defaults to default settings location).

        Args:
            input_settings_file: Optional File to read settings from.
        """

        from core.config import config

        if input_settings_file is None and not config.app_settings_file.is_file():
            return

        input_settings_file = input_settings_file or config.app_settings_file
        try:
            with input_settings_file.open('r') as fd:
                data = json.load(fd)
            logging.info(f'Loaded settings from {input_settings_file}')
        except Exception:
            logging.exception("Error loading settings")
            raise

        if 'skipped_update_version' in data and data['skipped_update_version'] is not None: # deserialize Version objects
            data['skipped_update_version'] = Version(data['skipped_update_version'])

        if 'profiles' in data:
            if 'active_profile_id' in data: # migrate to new field
                data['active_profile'] = data['active_profile_id']
                del data['active_profile_id']

            for i, profile in enumerate(data['profiles']):
                data['profiles'][i] = Profile.from_dict(profile)

                if data['active_profile'] == profile['id']:
                    data['active_profile'] = data['profiles'][i]

            update_dataclass(self, data)

            if not self.profiles:
                self.active_profile = None
                self.done_initial_setup = False
            elif self.active_profile is None:
                self.active_profile = self.profiles[0]
        elif 'tf_directory' in data: # migrate old flat format to profile format
            update_dataclass(self, {
                k: data[k] for
                k in (
                    'skip_launch_options_popup',
                    'suppress_update_notifications',
                    'skipped_update_version',
                )
                if k in data
            })

            self.profiles.append(Profile( # create TF2 profile from existing settings
                name='TF2',
                game_path=Path(data['tf_directory']),
                sourcemod = Sourcemods.TF2,
                addon_selections=data.get('addon_selections', []),
                matrix_selections=data.get('matrix_selections', {}),
                matrix_selections_simple=data.get('matrix_selections_simple', {}),
                simple_particle_mode=data.get('simple_particle_mode', True),
                show_console_on_startup=data.get('show_console_on_startup', True),
                disable_paint_colors=data.get('disable_paint_colors', False),
            ))

            if (goldrush_dir := data.get('goldrush_directory')) is not None: # create Gold Rush profile if configured
                self.profiles.append(Profile(
                    name='Gold Rush',
                    game_path=Path(goldrush_dir),
                    sourcemod = Sourcemods.TF2GR
                ))

            self.active_profile = self.profiles[0]

            logging.info(f'Migrated old settings to profile format ({len(self.profiles)} profile(s))')

    def save_settings(self):
        data = asdict(self)
        if self.active_profile is not None:
            data['active_profile'] = self.active_profile.id # Only save the id of the active profile (it is included in`profiles`)

        for i, profile in enumerate(self.profiles): # only save the profiles' sourcemods' names
            data['profiles'][i]['sourcemod'] = profile.sourcemod.name

        from core.config import config

        try:
            config.app_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with config.app_settings_file.open('w') as fd:
                json.dump(data, fd, indent=2, cls=JSONEncoder)
            logging.info(f'Saved settings to {config.app_settings_file}')
        except Exception:
            logging.exception('Error saving settings')
            raise

    def create_profile(self, name: str, game_path: Path, sourcemod: Sourcemods, activate: bool = False) -> Profile:
        profile = Profile(name=name, game_path=game_path, sourcemod=sourcemod)
        self.profiles.append(profile)

        if activate:
            self.active_profile = profile

        return profile

    def delete_profile(self, id: UUID):
        for i, profile in enumerate(self.profiles):
            if profile.id == id:
                self.profiles.pop(i)
                if self.active_profile == profile:
                    if i != 0:
                        self.active_profile = self.profiles[i-1]
                    elif profile:
                        self.active_profile = self.profiles[0]
                    else:
                        self.active_profile = None
                break
        else:
            raise ProfileNotFound(id)

    def update_profile(self, profile_id: UUID, *args, **kwargs):
        for i, profile in enumerate(self.profiles):
            if profile.id == profile_id:
                update_dataclass(profile, *args, **kwargs)
                break

    def should_show_update_dialog(self, version: Version) -> bool:
        return not (self.suppress_update_notifications or version == self.skipped_update_version)


class _Settings(Settings):
    """
    This is a nasty hack to ensure the dataclass' generated `__init__()` uses `object.__setattr__()` and `object.__getattr__()`.
    """

    def __init__(self):
        pass

    def __getattr__(obj, attr) -> None:
        raise AttributeError(attr)

    __setattr__ = object.__setattr__


# TODO: figure out if we can make type chekers actually happy here
Settings.__init__ = as_base_class(Settings.__init__, pass_self=True, cls=_Settings) # ty:ignore error[invalid-assignment]:
Settings._load_settings = as_base_class(Settings._load_settings, pass_self=True, cls=_Settings) # ty:ignore error[invalid-assignment]:


class AddonMetadata(dict):
    def __init__(self):
        super().__init__()
        self.load()

    def load(self) -> None:
        from core.config import config

        if config.addon_metadata_file.is_file():
            try:
                with config.addon_metadata_file.open('r') as f:
                    data = f.read()
            except Exception:
                logging.exception("Error loading addon metadata from file `{config.addon_metadata_file}`")
                raise

            if data:
                data = json.loads(data)

                if 'addon_metadata' in data: # remove redundant nesting, technically a migration
                    data = data['addon_metadata']

                self.update(data)

    def save(self):
        from core.config import config

        try:
            config.addon_metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with config.addon_metadata_file.open('w') as fd:
                json.dump(self, fd, indent=2, cls=JSONEncoder)
        except Exception:
            logging.exception('Error saving addon metadata')
            raise


settings: Settings
addon_metadata: AddonMetadata


def __getattr__(attr):
    global settings, addon_metadata

    match attr:
        case 'settings':
            settings = Settings()
            return settings
        case 'addon_metadata':
            addon_metadata = AddonMetadata()
            return addon_metadata

    raise AttributeError(f"module '{__name__}' has no attribute '{attr}'")

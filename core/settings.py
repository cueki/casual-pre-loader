import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import cast

from packaging.version import Version

from core.constants import Sourcemods
from core.profile import Profile
from core.util import as_base_class, update_dataclass

log = logging.getLogger(__name__)

# https://github.com/python/typing/issues/182#issuecomment-1320974824
type JSON = dict[str, 'JSON'] | list['JSON'] | str | int | float | bool | None


class NoActiveProfile(AttributeError):
    pass


class ProfileNotFound(KeyError):
    pass


@dataclass(frozen=True)
class SerializationSpec[T: type]:
    type: T
    """The type to encode"""

    encode: Callable[[T], JSON]
    """Function used to encode value to JSON"""


class SerializationSpecs(SerializationSpec, Enum):
    PATH = Path, str
    VERSION = Version, str


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            for spec in SerializationSpecs: # we can't just do a mapping lookup because we also want to match subclasses
                if isinstance(o, spec.type):
                    return spec.encode(o)
            raise

type Profiles = Mapping[str, Profile]


def _get_profile_name(name: str, profiles: Profiles) -> str:
    renamed = False
    original_name = name

    while name in profiles:
        name += '_'
        renamed = True

    if renamed:
        log.warning(f'profile with name `{original_name}` already exists, using `{name}`')

    return name


def _get_first_profile(profiles: Profiles) -> Profile: # NOTE: may not be consistent, but this doesn't really matter
    return next(iter(profiles.values()))

@dataclass
class Settings:
    active_profile: Profile | None = None
    details_collapsed: bool = False
    done_initial_setup: bool = False
    profiles: Mapping[str, Profile] = field(default_factory=dict)
    skip_launch_options_cleanup_popup: bool = False
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
            if value is not None and value in self.profiles:
                value = self.profiles[value]
            else:
                raise ProfileNotFound(f'{value} is not a known profile name')
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
            log.info(f'Loaded settings from {input_settings_file}')
        except Exception:
            log.exception("Error loading settings")
            raise

        if 'skipped_update_version' in data and data['skipped_update_version'] is not None: # deserialize Version objects
            data['skipped_update_version'] = Version(data['skipped_update_version'])

        if 'profiles' in data:
            if 'active_profile_id' in data: # migrate to new field
                data['active_profile'] = data['active_profile_id']
                del data['active_profile_id']

            if not isinstance(data['profiles'], Mapping):
                _profiles = {}
                for i, profile in enumerate(data['profiles']):
                    profile['name'] = _get_profile_name(profile['name'], _profiles)

                    if profile.get('id') is not None:
                        if data['active_profile'] == profile['id']:
                            data['active_profile'] = profile['name']

                        del profile['id']

                    _profiles[profile['name']] =  Profile.from_dict(profile)
                data['profiles'] = _profiles
                if data['profiles']: # WARNING: assume that the user has completed initial setup if, and ONLY if, we are using this migration path from list[Profile] -> Mapping[str, Profile]
                    data['done_initial_setup'] = True
            else:
                for name, profile, in data['profiles'].items():
                    profile['name'] = name
                    data['profiles'][name] = Profile.from_dict(profile)

            for profile in data['profiles'].values():
                if data['active_profile'] == profile.name:
                    data['active_profile'] = profile
                    break

            update_dataclass(self, data)

            if not self.profiles:
                self.active_profile = None
                self.done_initial_setup = False
            elif self.active_profile is None:
                self.active_profile = _get_first_profile(self.profiles)
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

            cast(dict, self.profiles)['TF2'] = Profile( # create TF2 profile from existing settings
                name='TF2',
                game_path=Path(data['tf_directory']),
                sourcemod = Sourcemods.TF2,
                addon_selections=data.get('addon_selections', []),
                matrix_selections=data.get('matrix_selections', {}),
                matrix_selections_simple=data.get('matrix_selections_simple', {}),
                simple_particle_mode=data.get('simple_particle_mode', True),
                show_console_on_startup=data.get('show_console_on_startup', True),
                disable_paint_colors=data.get('disable_paint_colors', False),
            )

            if (goldrush_dir := data.get('goldrush_directory')) is not None: # create Gold Rush profile if configured
                cast(dict, self.profiles)['Gold Rush'] = Profile(
                    name='Gold Rush',
                    game_path=Path(goldrush_dir),
                    sourcemod = Sourcemods.TF2GR
                )

            self.active_profile = self.profiles['TF2']

            log.info(f'Migrated old settings to profile format ({len(self.profiles)} profile(s))')

    def save_settings(self):
        from core.config import config

        data = asdict(self)
        if self.active_profile is not None:
            data['active_profile'] = self.active_profile.name # Only save the name of the active profile (it is included in`profiles`)

        for name, profile in data['profiles'].items(): # only save the profiles' sourcemods' names
            profile['sourcemod'] = self.profiles[name].sourcemod.name
            del profile['name']

        try:
            config.app_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with config.app_settings_file.open('w') as fd:
                json.dump(data, fd, indent=2, cls=JSONEncoder)
            log.info(f'Saved settings to {config.app_settings_file}')
        except Exception:
            log.exception('Error saving settings')
            raise

    def create_profile(self, name: str, game_path: Path, sourcemod: Sourcemods, activate: bool = False) -> Profile:
        name = _get_profile_name(name, self.profiles)

        profile = Profile(name=name, game_path=game_path, sourcemod=sourcemod)
        cast(dict, self.profiles)[name] = profile

        if activate:
            self.active_profile = profile.name
        else:
            self.save_settings()

        return profile

    def delete_profile(self, name: str):
        if name in self.profiles:
            _profiles = list(self.profiles)
            i = _profiles.index(name) # NOTE: may not be consistent, but this doesn't really matter
            _profiles.pop(i)
            profile = cast(dict, self.profiles).pop(name)

            if self.active_profile == profile:
                if i != 0:
                    self.active_profile = self.profiles[_profiles[i-1]]
                elif self.profiles:
                    self.active_profile = self.profiles[_profiles[0]]
                else:
                    self.active_profile = None
            else:
                self.save_settings()
        else:
            raise ProfileNotFound(name)

    def update_profile(self, profile_name: str, **kwargs):
        if profile_name in self.profiles:
            update_dataclass(self.profiles[profile_name], **kwargs)

            if 'name' in kwargs:
                self.profiles[kwargs['name']] = self.profiles[profile_name]
                del self.profiles[profile_name]

            self.save_settings()
        else:
            raise ProfileNotFound(profile_name)

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


# TODO: figure out if we can make type checkers actually happy here
Settings.__init__ = as_base_class(Settings.__init__, pass_self=True, cls=_Settings) # ty: ignore error[invalid-assignment]:
Settings._load_settings = as_base_class(Settings._load_settings, pass_self=True, cls=_Settings) # ty: ignore error[invalid-assignment]:


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
                log.exception(f'Error loading addon metadata from file `{config.addon_metadata_file}`')
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
            log.exception('Error saving addon metadata')
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

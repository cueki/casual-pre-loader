import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.constants import PROGRAM_AUTHOR, PROGRAM_NAME

log = logging.getLogger()


@dataclass
class FolderConfig:
    # configuration class for managing folder paths

    # INFO: This file just allows package maintainers to set whether this application should act as if it is a portable installation.
    # They can easily modify this file and set these values, e.g.
    # `printf '%s\n' 'portable = False' >core/are_we_portable.py`
    # This will make the application use paths outside the installation location.
    import core.are_we_portable

    portable = core.are_we_portable.portable
    del core.are_we_portable

    install_dir = Path(__file__).resolve().parent.parent
    data_dir =   install_dir / 'data'

    mod_urls_file = data_dir / 'mod_urls.json'
    particle_system_map_file = data_dir / 'particle_system_map.json'

    if portable:
        # default portable values
        project_dir =  install_dir / 'userdata' / 'data'
        settings_dir = install_dir / 'userdata' / 'config'
        temp_dir =     install_dir / 'userdata' / 'temp'
    else:
        import platformdirs

        # default non-portable values
        project_dir =  platformdirs.user_data_path(PROGRAM_NAME, PROGRAM_AUTHOR)
        settings_dir = platformdirs.user_config_path(PROGRAM_NAME, PROGRAM_AUTHOR)
        temp_dir =     platformdirs.user_cache_path(PROGRAM_NAME, PROGRAM_AUTHOR)

    __deps = {
        'project_dir': {
            'backup_dir': lambda self: self.project_dir / 'backup',
            'mods_dir':   lambda self: self.project_dir / 'mods',

            'log_file':      lambda self: self.project_dir / 'casual-pre-loader.log',
            'modsinfo_file': lambda self: self.project_dir / 'modsinfo.json',
        },
        'mods_dir': {
            'particles_dir': lambda self: self.mods_dir / 'particles',
            'addons_dir':    lambda self: self.mods_dir / 'addons',
        },
        'settings_dir': {
            'app_settings_file':   lambda self: self.settings_dir / 'app_settings.json',
            'addon_metadata_file': lambda self: self.settings_dir / 'addon_metadata.json',
        },
        'temp_dir': {
            'temp_to_be_processed_dir':  lambda self: self.temp_dir / 'to_be_processed',
            'temp_to_be_referenced_dir': lambda self: self.temp_dir / 'to_be_referenced',
            'temp_to_be_patched_dir':    lambda self: self.temp_dir / 'to_be_patched',
            'temp_to_be_vpk_dir':        lambda self: self.temp_dir / 'to_be_vpk',
        },
    }

    def __post_init__(self):
        for dep, props in self.__deps.items():
            for attr, setter in props.items():
                super().__setattr__(attr, setter(self))

    def update_deps(self, attr: str, deps: Optional[set] = None):
        log.debug(f'updating all attrs dependent on {attr}')

        deps = deps is None and {attr} or deps
        if attr in self.__deps:
            for _attr, setter in self.__deps[attr].items():
                _value = setter(self)
                super().__setattr__(_attr, _value)
                log.debug(f'set dependency {_attr} of {attr} to {_value}')

                if _attr not in deps:
                    deps.add(_attr)
                    self.update_deps(_attr, deps)

    def __setattr__(self, attr, value):
        _super = super()
        _super.__setattr__(attr, value)
        log_str = f'set {attr} to {value}'

        # make attr independent
        is_dep = False
        for dep, props in tuple(self.__deps.items()):
            if attr in props:
                del props[attr]
                is_dep = True
        if is_dep:
            log_str += ', making it no longer dependant on other attrs'
        log.debug(log_str)

        if attr in self.__deps: # update any other dependent attrs
            self.update_deps(attr)


folder_setup = FolderConfig() # create a default instance for import

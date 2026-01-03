from dataclasses import dataclass
from pathlib import Path

# INFO: This file just allows package maintainers to set whether this application should act as if it is a portable installation.
# They can easily modify this file and set these values, e.g.
# `printf '%s\n' 'portable = False' >core/are_we_portable.py`
# This will make the application use paths outside the installation location.
from core.are_we_portable import portable
from core.constants import PROGRAM_AUTHOR, PROGRAM_NAME


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    install_dir = Path(__file__).resolve().parent.parent
    data_dir =   install_dir / 'data'

    portable = portable  # make sure it is accessible via self.portable

    if portable:
        # default portable values
        project_dir = install_dir
        settings_dir = project_dir
    else:
        import platformdirs

        # default non-portable values
        project_dir = Path(platformdirs.user_data_dir(PROGRAM_NAME, PROGRAM_AUTHOR))
        settings_dir = Path(platformdirs.user_config_dir(PROGRAM_NAME, PROGRAM_AUTHOR))

    __deps = {
        'project_dir': {
            'backup_dir' :    lambda self: self.project_dir / 'backup',
            'mods_dir' :      lambda self: self.project_dir / 'mods',
            'temp_dir' :      lambda self: self.project_dir / 'temp',
        },
        'mods_dir' : {
            'particles_dir' : lambda self: self.mods_dir / 'particles',
            'addons_dir' :    lambda self: self.mods_dir / 'addons',
        },
        'temp_dir' : {
            'temp_download_dir' :         lambda self: self.temp_dir / 'download',
            'temp_to_be_processed_dir' :  lambda self: self.temp_dir / 'to_be_processed',
            'temp_to_be_referenced_dir' : lambda self: self.temp_dir / 'to_be_referenced',
            'temp_to_be_patched_dir' :    lambda self: self.temp_dir / 'to_be_patched',
            'temp_to_be_vpk_dir' :        lambda self: self.temp_dir / 'to_be_vpk',
        },
    }

    def __post_init__(self):
        for dep, props in self.__deps.items():
            for attr, setter in props.items():
                super().__setattr__(attr, setter(self))

    def __setattr__(self, attr, value):
        _super = super()
        _super.__setattr__(attr, value)

        if attr in self.__deps:
            for _attr, setter in self.__deps[attr].items():
                _super.__setattr__(_attr, setter(self))
        else:
            for dep, props in tuple(self.__deps.items()):
                if attr in props:
                    del props[attr]


folder_setup = FolderConfig() # create a default instance for import

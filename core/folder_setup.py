import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from valve_parsers import PCFFile

# INFO: This file just allows package maintainers to set whether this application should act as if it is a portable installation.
# They can easily modify this file and set these values, e.g.
# `printf '%s\n' 'portable = False' >core/are_we_portable.py`
# This will make the application use paths outside the installation location.
from core.are_we_portable import portable
from core.constants import PROGRAM_AUTHOR, PROGRAM_NAME

log = logging.getLogger()


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    install_dir = Path(os.path.abspath(__file__)).parent.parent
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

        shutil.copytree(install_dir / "backup", project_dir / "backup", dirs_exist_ok=True)

    data_dir = install_dir / 'data'
    backup_dir = project_dir / 'backup'

    mods_dir = project_dir / 'mods'
    particles_dir = mods_dir / 'particles'
    addons_dir = mods_dir / 'addons'

    temp_dir = project_dir / 'temp'
    temp_download_dir = temp_dir  / 'download'
    temp_to_be_processed_dir = temp_dir / 'to_be_processed'
    temp_to_be_referenced_dir = temp_dir /  'to_be_referenced'
    temp_to_be_patched_dir = temp_dir /  'to_be_patched'
    temp_to_be_vpk_dir = temp_dir /  'to_be_vpk'

    modsinfo_file = project_dir / 'modsinfo.json'

    def cleanup_temp_folders(self) -> None:
        # anything put in temp/ will be gone !!!!!
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


# create a default instance for import
folder_setup = FolderConfig()

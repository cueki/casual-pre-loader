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
from core.handlers.pcf_handler import get_parent_elements

log = logging.getLogger()


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    install_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent  # INFO: I'm not too sure if this can break or not, oh well
    portable = portable  # make sure it is accessible via self.portable

    # TODO: allow windows users to use non-portable installs (would allow us to remove this entire platform check)
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

    base_default_pcf: Optional[PCFFile] = field(default=None)
    base_default_parents: Optional[set[str]] = field(default=None)

    # main folder names
    _backup_folder = "backup"
    _mods_folder = "mods"

    # mods subdir
    _mods_particles_folder = "particles"
    _mods_addons_folder = "addons"

    # temp and it's nested folders (to be cleared every run)
    _temp_folder = "temp"
    _temp_to_be_processed_folder = "to_be_processed"
    _temp_to_be_referenced_folder = "to_be_referenced"
    _temp_to_be_patched_folder = "to_be_patched"
    _temp_to_be_vpk_folder = "to_be_vpk"

    def __post_init__(self):
        self.backup_dir = self.project_dir / self._backup_folder
        self.data_dir = self.install_dir / "data"

        self.mods_dir = self.project_dir / self._mods_folder
        self.particles_dir = self.mods_dir / self._mods_particles_folder
        self.addons_dir = self.mods_dir / self._mods_addons_folder

        self.temp_dir = self.project_dir / self._temp_folder
        self.temp_to_be_processed_dir = self.temp_dir / self._temp_to_be_processed_folder
        self.temp_to_be_referenced_dir = self.temp_dir / self._temp_to_be_referenced_folder
        self.temp_to_be_patched_dir = self.temp_dir / self._temp_to_be_patched_folder
        self.temp_to_be_vpk_dir = self.temp_dir / self._temp_to_be_vpk_folder

        self.modsinfo_file = self.project_dir / "modsinfo.json"

    def create_required_folders(self) -> None:
        folders = [
            self.mods_dir,
            self.addons_dir,
            self.particles_dir,

            self.temp_dir,
            self.temp_to_be_processed_dir,
            self.temp_to_be_referenced_dir,
            self.temp_to_be_patched_dir,
            self.temp_to_be_vpk_dir
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def initialize_pcf(self):
        if self.temp_to_be_referenced_dir.exists():
            default_base_path = self.temp_to_be_referenced_dir / "disguise.pcf"
            if default_base_path.exists():
                self.base_default_pcf = PCFFile(default_base_path).decode()
                self.base_default_parents = get_parent_elements(self.base_default_pcf)

    def cleanup_temp_folders(self) -> None:
        # anything put in temp/ will be gone !!!!!
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.base_default_pcf = None
            self.base_default_parents = None

    def cleanup_old_updater(self) -> None:
        core_dir = self.install_dir / "core"
        updater_old = core_dir / "updater_old.exe"
        if not updater_old.exists():
            return

        updater_old.unlink()
        log.debug(f"Removed old updater: {updater_old.name}")

    def cleanup_old_structure(self) -> None:
        # cleanup old files/folders after reorganization during auto update
        old_files = [
            self.install_dir / "particle_system_map.json",
            self.install_dir / "mod_urls.json"
        ]

        old_folders = [
            self.install_dir / "operations",
            self.install_dir / "quickprecache",
        ]

        for old_file in old_files:
            if old_file.exists():
                old_file.unlink()
                log.debug(f"Removed old file: {old_file.name}")

        for old_folder in old_folders:
            if old_folder.exists():
                shutil.rmtree(old_folder)
                log.debug(f"Removed old folder: {old_folder.name}")

    def get_temp_path(self, filename: str) -> Path:
        return self.temp_dir / filename

    def get_output_path(self, filename: str) -> Path:
        return self.temp_to_be_processed_dir / filename

    def get_backup_path(self, filename: str) -> Path:
        return self.backup_dir / filename

    def get_game_files_path(self, filename: str) -> Path:
        return self.temp_to_be_referenced_dir / filename


# create a default instance for import
folder_setup = FolderConfig()

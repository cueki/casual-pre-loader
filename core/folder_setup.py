import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# INFO: This file just allows package maintainers to set whether this application should act as if it is a portable installation.
# They can easily modify this file and set these values, e.g.
# `printf '%s\n' 'portable = False' >core/are_we_portable.py`
# This will make the application use paths outside the installation location.
from core.are_we_portable import portable
from core.handlers.pcf_handler import get_parent_elements
from valve_parsers import PCFFile


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    install_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent  # INFO: I'm not too sure if this can break or not, oh well
    portable = portable  # make sure it is accessible via self.portable

    program_name = 'casual-pre-loader'
    program_author = 'cueki'

    # TODO: allow windows users to use non-portable installs (would allow us to remove this entire platform check)
    if portable:
        # default portable values
        project_dir = install_dir
        settings_dir = project_dir
    else:
        import platformdirs

        # default non-portable values
        project_dir = Path(platformdirs.user_data_dir(program_name, program_author))
        settings_dir = Path(platformdirs.user_config_dir(program_name, program_author))

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

        self.mods_dir = self.project_dir / self._mods_folder
        self.particles_dir = self.mods_dir / self._mods_particles_folder
        self.addons_dir = self.mods_dir / self._mods_addons_folder

        self.temp_dir = self.project_dir / self._temp_folder
        self.temp_to_be_processed_dir = self.temp_dir / self._temp_to_be_processed_folder
        self.temp_to_be_referenced_dir = self.temp_dir / self._temp_to_be_referenced_folder
        self.temp_to_be_patched_dir = self.temp_dir / self._temp_to_be_patched_folder
        self.temp_to_be_vpk_dir = self.temp_dir / self._temp_to_be_vpk_folder

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
        print(f"Removed old updater: {updater_old.name}")

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

# logging
print(
    f'We{" ARE " if folder_setup.portable else " are NOT "}running a portable install',
    f'Application files are located in {folder_setup.install_dir}',
    f'Project files are written to {folder_setup.project_dir}',
    f'Settings files are in {folder_setup.settings_dir}',
    sep='\n'
)

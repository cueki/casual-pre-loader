from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from core.handlers.pcf_handler import get_parent_elements
from core.parsers.pcf_file import PCFFile


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    project_dir = Path.cwd()
    base_default_pcf: Optional[PCFFile] = field(default=None)
    base_default_parents: Optional[set[str]] = field(default=None)

    # main folder names
    backup_folder = "backup"
    temp_folder = "temp"
    mods_folder = "mods"

    # temp nested folders (to be cleared every run)
    working_folder = "working"
    output_folder = "output"
    temp_mods_folder = "mods"
    game_files_folder = "game_files"

    # mods subfolders
    mods_particles_folder = "particles"
    mods_addons_folder = "addons"

    def __post_init__(self):
        self.backup_dir = self.project_dir / self.backup_folder
        self.temp_dir = self.project_dir / self.temp_folder
        self.mods_dir = self.project_dir / self.mods_folder

        self.working_dir = self.temp_dir / self.working_folder
        self.output_dir = self.temp_dir / self.output_folder
        self.temp_mods_dir = self.temp_dir / self.temp_mods_folder
        self.game_files_dir = self.temp_dir / self.game_files_folder

        self.particles_dir = self.mods_dir / self.mods_particles_folder
        self.addons_dir = self.mods_dir / self.mods_addons_folder

    def create_required_folders(self) -> None:
        folders = [
            self.backup_dir,
            self.temp_dir,
            self.mods_dir,
            self.particles_dir,
            self.addons_dir,
            self.working_dir,
            self.output_dir,
            self.temp_mods_dir,
            self.game_files_dir
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def initialize_pcf(self):
        if self.game_files_dir.exists():
            default_base_path = self.game_files_dir / "disguise.pcf"
            if default_base_path.exists():
                self.base_default_pcf = PCFFile(default_base_path).decode()
                self.base_default_parents = get_parent_elements(self.base_default_pcf)

    def cleanup_temp_folders(self) -> None:
        if self.temp_dir.exists():
            for file in self.temp_dir.glob('**/*'):
                if file.is_file():
                    file.unlink()
            for subfolder in reversed(list(self.temp_dir.glob('**/*'))):
                if subfolder.is_dir():
                    subfolder.rmdir()
            self.temp_dir.rmdir()
            self.base_default_pcf = None
            self.base_default_parents = None

    def get_temp_path(self, filename: str) -> Path:
        return self.temp_dir / filename

    def get_working_path(self, filename: str) -> Path:
        return self.working_dir / filename

    def get_output_path(self, filename: str) -> Path:
        return self.output_dir / filename

    def get_backup_path(self, filename: str) -> Path:
        return self.backup_dir / filename

    def get_temp_mods_path(self, filename: str) -> Path:
        return self.temp_mods_dir / filename

    def get_game_files_path(self, filename: str) -> Path:
        return self.game_files_dir / filename

    def get_particles_path(self, filename: str) -> Path:
        return self.particles_dir / filename

    def get_addons_path(self, filename: str) -> Path:
        return self.addons_dir / filename


# create a default instance for import
folder_setup = FolderConfig()
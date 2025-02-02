from pathlib import Path
from dataclasses import dataclass


@dataclass
class FolderConfig:
    # configuration class for managing folder paths
    project_dir = Path.cwd()

    # main folder names
    backup_folder = "backup"
    temp_folder = "temp"
    presets_folder = "presets"
    addons_folder = "addons"
    user_mods_folder = "user_mods"

    # temp nested folder (to be cleared every run)
    working_folder = "working"
    output_folder = "output"
    mods_folder = "mods"
    game_files_folder = "game_files"

    # two folders nested in mods
    # mods_particle_folder = "particles"
    # mods_everything_else_folder = "everything_else"

    def __post_init__(self):
        self.backup_dir = self.project_dir /  self.backup_folder
        self.temp_dir = self.project_dir / self.temp_folder
        self.presets_dir = self.project_dir / self.presets_folder
        self.addons_dir = self.project_dir / self.addons_folder
        self.user_mods_dir = self.project_dir / self.user_mods_folder

        self.working_dir = self.temp_dir / self.working_folder
        self.output_dir = self.temp_dir / self.output_folder
        self.mods_dir = self.temp_dir / self.mods_folder
        self.game_files_dir = self.temp_dir / self.game_files_folder

        # self.mods_particle_dir = self.mods_dir / self.mods_particle_folder
        # self.mods_everything_else_dir = self.mods_dir / self.mods_everything_else_folder

    def create_required_folders(self) -> None:
        folders = [
            self.backup_dir,
            self.temp_dir,
            self.presets_dir,
            self.addons_dir,
            self.user_mods_dir,
            self.working_dir,
            self.output_dir,
            self.mods_dir,
            self.game_files_dir
            # self.mods_particle_dir,
            # self.mods_everything_else_dir
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    def cleanup_temp_folders(self) -> None:
        if self.temp_dir.exists():
            for file in self.temp_dir.glob('**/*'):
                if file.is_file():
                    file.unlink()
            for subfolder in reversed(list(self.temp_dir.glob('**/*'))):
                if subfolder.is_dir():
                    subfolder.rmdir()
            self.temp_dir.rmdir()

    def get_temp_path(self, filename: str) -> Path:
        return self.temp_dir / filename

    def get_working_path(self, filename: str) -> Path:
        return self.working_dir / filename

    def get_output_path(self, filename: str) -> Path:
        return self.output_dir / filename

    def get_backup_path(self, filename: str) -> Path:
        return self.backup_dir / filename

    def get_mods_path(self, filename: str) -> Path:
        return self.mods_dir / filename

    def get_game_files_path(self, filename: str) -> Path:
        return self.game_files_dir / filename


# create a default instance for import
folder_setup = FolderConfig()
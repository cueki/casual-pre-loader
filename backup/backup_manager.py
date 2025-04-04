import shutil
from pathlib import Path
from core.folder_setup import folder_setup
from core.parsers.vpk_file import VPKFile
from core.handlers.file_handler import FileHandler


def prepare_working_copy() -> bool:
    try:
        folder_setup.cleanup_temp_folders()
        folder_setup.create_required_folders()
        # print("Preparing working copy from backup...")
        required_vpks = [
            "tf2_misc_000.vpk",
            "tf2_misc_017.vpk",
            "tf2_misc_dir.vpk"
        ]

        # copy VPK files from backup to working directory
        for vpk_name in required_vpks:
            backup_file = folder_setup.get_backup_path(vpk_name)
            shutil.copy2(backup_file, folder_setup.temp_working_dir / vpk_name)

        # setup VPK handler for file extraction
        working_vpk_path = folder_setup.get_working_path("tf2_misc_dir.vpk")
        vpk_file = VPKFile(str(working_vpk_path))
        vpk_file.parse_directory()
        file_handler = FileHandler(working_vpk_path)

        # extract PCF files, excluding unusual particles
        excluded_patterns = ['unusual']
        pcf_files = [f for f in file_handler.list_pcf_files()
                    if not any(pattern in f.lower() for pattern in excluded_patterns)]

        for file in pcf_files:
            base_name = Path(file).name
            output_path = folder_setup.temp_game_files_dir / base_name
            vpk_file.extract_file(file, str(output_path))

        return True

    except Exception as e:
        print(f"Error preparing working copy: {e}")
        return False


def get_working_vpk_path() -> Path:
    return folder_setup.get_working_path("tf2_misc_dir.vpk")


class BackupManager:
    def __init__(self, tf_dir: str):
        self.tf_dir = Path(tf_dir)
        self.game_vpk_path = self.tf_dir / "tf2_misc_dir.vpk"

        # the files we need
        base_name = "tf2_misc"
        self.required_vpks = [
            f"{base_name}_000.vpk",
            f"{base_name}_017.vpk",
            f"{base_name}_dir.vpk"
        ]

    def deploy_to_game(self) -> bool:
        try:
            for vpk_name in self.required_vpks:
                working_file = folder_setup.get_working_path(vpk_name)
                shutil.copy2(working_file, self.tf_dir / vpk_name)

            folder_setup.cleanup_temp_folders()
            return True

        except Exception as e:
            print(f"Error deploying to game: {e}")
            return False

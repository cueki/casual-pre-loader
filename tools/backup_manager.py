import os
import shutil
from datetime import datetime
from pathlib import Path
from core.folder_setup import folder_setup


class BackupManager:
    def __init__(self, tf_dir: str):
        self.tf_dir = Path(tf_dir)
        self.game_vpk_path = self.tf_dir / "tf2_misc_dir.vpk"
        self.game_dir = self.tf_dir

        # the files we need
        base_name = "tf2_misc"
        self.required_vpks = [
            f"{base_name}_000.vpk",
            f"{base_name}_017.vpk",
            f"{base_name}_dir.vpk"
        ]

    def check_game_update(self) -> bool:
        # _dir.vpk files
        game_dir_vpk = self.game_dir / self.required_vpks[-1]
        backup_dir_vpk = folder_setup.get_backup_path(self.required_vpks[-1])

        if not backup_dir_vpk.exists():
            return True  # no backup exists, need to create one

        game_time = datetime.fromtimestamp(game_dir_vpk.stat().st_mtime)
        backup_time = datetime.fromtimestamp(backup_dir_vpk.stat().st_mtime)

        if game_time > backup_time:
            print(f"Game update detected!")
            print(f"Game VPK timestamp: {game_time}")
            print(f"Backup timestamp: {backup_time}")
            return True

        return False

    def create_initial_backup(self) -> bool:
        try:
            # check if we need new backups
            needs_backup = False
            if not all((folder_setup.get_backup_path(vpk)).exists() for vpk in self.required_vpks):
                needs_backup = True
                print("Missing backup files, creating new backups...")
            elif self.check_game_update():
                needs_backup = True
                print("Game files have been updated, creating new backups...")

            if needs_backup:
                # remove any existing backups
                for vpk in self.required_vpks:
                    backup_file = folder_setup.get_backup_path(vpk)
                    if backup_file.exists():
                        backup_file.unlink()

                # create new backups
                for vpk_name in self.required_vpks:
                    source_file = self.game_dir / vpk_name
                    backup_file = folder_setup.backup_dir / vpk_name

                    if not source_file.exists():
                        print(f"ERROR: Required game file not found: {vpk_name}")
                        return False

                    print(f"Backing up {vpk_name}...")
                    shutil.copy2(source_file, backup_file)

                print("Backup created successfully")
            else:
                print("Using existing backups")

            return True

        except Exception as e:
            print(f"Error creating backup: {e}")
            return False

    def prepare_working_copy(self) -> bool:
        try:
            print("Preparing working copy from backup...")
            for vpk_name in self.required_vpks:
                backup_file = folder_setup.get_backup_path(vpk_name)
                if not backup_file.exists():
                    print(f"ERROR: Backup file missing: {vpk_name}")
                    return False
                shutil.copy2(backup_file, folder_setup.working_dir / vpk_name)

            return True

        except Exception as e:
            print(f"Error preparing working copy: {e}")
            return False

    def deploy_to_game(self) -> bool:
        try:
            print("Deploying modified files to game directory...")
            for vpk_name in self.required_vpks:
                working_file = folder_setup.get_working_path(vpk_name)
                if not working_file.exists():
                    print(f"ERROR: Working file missing: {vpk_name}")
                    return False
                shutil.copy2(working_file, self.game_dir / vpk_name)
                os.remove(working_file)

            return True

        except Exception as e:
            print(f"Error deploying to game: {e}")
            return False

    def get_working_vpk_path(self) -> Path:
        return folder_setup.get_working_path(self.game_vpk_path.name)
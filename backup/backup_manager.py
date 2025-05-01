import shutil
from pathlib import Path
from core.folder_setup import folder_setup


def prepare_working_copy() -> bool:
    # I should probably just move this elsewhere
    try:
        folder_setup.cleanup_temp_folders()
        folder_setup.create_required_folders()

        backup_particles_dir = Path("backup/particles")
        particle_dest_dir = folder_setup.temp_game_files_dir

        for pcf_file in backup_particles_dir.glob("*.pcf"):
            shutil.copy2(pcf_file, particle_dest_dir / pcf_file.name)

        return True

    except Exception as e:
        print(f"Error preparing working copy: {e}")
        return False

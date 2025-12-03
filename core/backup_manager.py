import logging
import shutil

from core.folder_setup import folder_setup

log = logging.getLogger()


def prepare_working_copy() -> bool:
    try:
        folder_setup.cleanup_temp_folders()
        folder_setup.create_required_folders()

        backup_particles_dir = folder_setup.backup_dir / "particles"
        particle_dest_dir = folder_setup.temp_to_be_referenced_dir

        for pcf_file in backup_particles_dir.glob("*.pcf"):
            shutil.copy2(pcf_file, particle_dest_dir / pcf_file.name)

        return True

    except Exception:
        log.exception("Error preparing working copy")
        return False

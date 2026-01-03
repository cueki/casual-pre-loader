import logging
import shutil

from core.folder_setup import folder_setup
from core.util.file import delete

log = logging.getLogger()


def prepare_working_copy() -> bool:
    try:
        delete(folder_setup.temp_dir, not_exist_ok=True)

        backup_particles_dir = folder_setup.backup_dir / "particles"
        particle_dest_dir = folder_setup.temp_to_be_referenced_dir
        backup_particles_dir.mkdir(parents=True, exist_ok=True)
        particle_dest_dir.mkdir(parents=True, exist_ok=True)

        for pcf_file in backup_particles_dir.glob("*.pcf"):
            shutil.copy2(pcf_file, particle_dest_dir / pcf_file.name)

        return True

    except Exception:
        log.exception("Error preparing working copy")
        return False

import logging
import shutil
from pathlib import Path

from core.config import config
from core.operations.pcf_rebuild import load_particle_system_map
from core.util.file import copy, delete

log = logging.getLogger()


def prepare_working_copy() -> str | None:
    """Populate the temp staging folder with vanilla PCFs from backup_dir/particles,
    then verify all expected files landed. Returns a user-facing error message on
    failure, or None if the staging folder is ready."""

    try:
        delete(config.temp_dir, not_exist_ok=True)

        backup_particles_dir = config.backup_dir / "particles"
        particle_dest_dir = config.temp_to_be_referenced_dir
        backup_particles_dir.mkdir(parents=True, exist_ok=True)
        particle_dest_dir.mkdir(parents=True, exist_ok=True)

        for pcf_file in backup_particles_dir.glob("*.pcf"):
            shutil.copy2(pcf_file, particle_dest_dir / pcf_file.name)
    except Exception as e:
        log.exception("Error preparing working copy")
        return (
            f"Failed to populate the temp staging folder.\n\n"
            f"{e}\n\n"
            f"See the log for details:\n{config.log_file}"
        )

    map_path = config.particle_system_map_file
    try:
        particle_map = load_particle_system_map(map_path)
    except Exception as e:
        log.exception("Failed to load particle_system_map.json")
        return (
            f"Could not read the bundled particle_system_map.json:\n{map_path}\n\n"
            f"{e}\n\n"
            "The preloader install appears to be incomplete or corrupted, "
            "try re-extracting the preloader to a local folder."
        )

    expected = {Path(key).name for key in particle_map.keys()}
    dest = config.temp_to_be_referenced_dir
    missing = sorted(name for name in expected if not (dest / name).exists())

    if not missing:
        return None

    if len(missing) == len(expected):
        return (
            f"Vanilla particle staging folder is empty:\n{dest}\n\n"
            "None of the vanilla .pcf files that ship with the preloader were "
            "copied into this folder. Try restarting the preloader. If the "
            "problem persists, the install may be incomplete or corrupted "
            "(antivirus, OneDrive sync, or a bad download can cause this), "
            "try re-extracting the preloader to a local folder."
        )

    preview = ', '.join(missing[:5])
    if len(missing) > 5:
        preview += f', and {len(missing) - 5} more'
    return (
        f"Vanilla particle staging folder is missing {len(missing)} of "
        f"{len(expected)} expected files:\n{dest}\n\n"
        f"Missing: {preview}\n\n"
        "The bundled backup/ folder may be incomplete, or some files were "
        "blocked by antivirus or filesystem issues. Try re-extracting the "
        "preloader to a local folder."
    )


def prepare_runtime_environment() -> str | None:
    """Run all startup setup steps that populate the staging folder. Returns a
    user-facing error message on failure, or None if everything is ready."""

    bundled_backup = config.install_dir / "backup"
    project_backup = config.project_dir / "backup"
    try:
        copy(bundled_backup, project_backup, noclobber=False)
    except Exception as e:
        log.exception("Failed to copy bundled backup/ to project dir")
        return (
            f"Failed to copy the bundled backup/ folder.\n\n"
            f"Source: {bundled_backup}\n"
            f"Destination: {project_backup}\n\n"
            f"{e}\n\n"
            "This usually means the application can't read its bundled files or "
            "can't write to its data folder. Try running the preloader from a "
            "local folder (not OneDrive/cloud-synced) and check that antivirus "
            "software isn't interfering."
        )

    return prepare_working_copy()

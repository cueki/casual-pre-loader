import logging

from core.constants import PARTICLE_SPLITS
from core.folder_setup import folder_setup

log = logging.getLogger()


def migrate_old_particle_files():
    from valve_parsers import PCFFile

    from core.operations.advanced_particle_merger import AdvancedParticleMerger, save_split_files

    mods_to_migrate = []
    mods_missing_source = []

    folder_setup.particles_dir.mkdir(parents=True, exist_ok=True)

    # check each mod for old format files
    for mod_dir in folder_setup.particles_dir.iterdir():
        if not mod_dir.is_dir():
            continue

        actual_particles = mod_dir / "actual_particles"
        if not actual_particles.exists():
            continue

        for original_file in PARTICLE_SPLITS.keys():
            old_file = actual_particles / original_file

            # If old full file exists, check if splits also exist
            if old_file.exists():
                splits_exist = any(
                    (actual_particles / split_name).exists()
                    for split_name in PARTICLE_SPLITS[original_file].keys()
                )

                # need to migrate if splits don't exist
                if not splits_exist:
                    original_source = mod_dir / "particles"

                    if original_source.exists() and any(original_source.glob("*.pcf")):
                        if mod_dir not in mods_to_migrate:
                            mods_to_migrate.append(mod_dir)
                    else:
                        if mod_dir.name not in mods_missing_source:
                            mods_missing_source.append(mod_dir.name)

    # migrate mods that have their source particles/ dir
    if mods_to_migrate:
        log.info(f"\nMigrating {len(mods_to_migrate)} mod(s) to new particle split format...")

        for mod_dir in mods_to_migrate:
            log.info(f"Processing {mod_dir.name}...")

            try:
                for original_file in PARTICLE_SPLITS.keys():
                    old_file = mod_dir / "actual_particles" / original_file
                    if old_file.exists():
                        old_file.unlink()

                # re-run AdvancedParticleMerger to regenerate with splits
                merger = AdvancedParticleMerger()
                merger.preprocess_vpk(mod_dir)

            except Exception:
                log.exception(f"Failed to migrate {mod_dir.name}")

        log.info("Migration complete!")

    # migrate mods without source (fallback cringe lazy method)
    if mods_missing_source:
        log.info("Migrating the following mods using fallback method (missing particles/ directory):")
        for mod_name in mods_missing_source:
            log.info(f"{mod_name}")

        for mod_name in mods_missing_source:
            mod_dir = folder_setup.particles_dir / mod_name

            try:
                actual_particles = mod_dir / "actual_particles"

                for original_file, split_defs in PARTICLE_SPLITS.items():
                    old_file = actual_particles / original_file

                    if old_file.exists():
                        pcf = PCFFile(old_file).decode()
                        save_split_files(pcf, mod_dir, split_defs)
                        old_file.unlink()

            except Exception:
                log.exception(f"Failed to migrate {mod_name}")

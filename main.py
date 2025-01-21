import os
import zipfile
from pathlib import Path
import random
import vpk
import yaml
from core.constants import CUSTOM_VPK_NAMES
from core.folder_setup import folder_setup
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from tools.backup_manager import BackupManager
from tools.pcf_squish import ParticleMerger
from tools.vpk_unpack import VPKExtractor


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    # init + clean folders we need
    folder_setup.cleanup_temp_folders()
    folder_setup.create_required_folders()

    # initialize backup manager with tf directory path
    backup_manager = BackupManager(config['tf_dir'])

    # create initial backup if it doesn't exist
    if not backup_manager.create_initial_backup():
        print("Failed to create/verify backup")
        return

    # prepare fresh working copy from backup
    if not backup_manager.prepare_working_copy():
        print("Failed to prepare working copy")
        return

    output_dir = folder_setup.mods_dir
    with zipfile.ZipFile("presets/minecraft_preset.zip", 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    working_vpk_path = backup_manager.get_working_vpk_path()

    # initialize handlers
    vpk_handler = VPKHandler(str(working_vpk_path))
    file_handler = FileHandler(vpk_handler)

    ParticleMerger(file_handler, vpk_handler).process()

    excluded_patterns = ['dx80', 'default', 'unusual', 'test']
    for file in file_handler.list_pcf_files():
        if not any(pattern in file.lower() for pattern in excluded_patterns):
            base_name = Path(file).name
            file_handler.process_file(
                base_name,
                pcf_empty_root_processor(),
                create_backup=False
            )

    # compress the mod files and put them in the game
    squished_files = folder_setup.output_dir.glob('*.pcf')
    for squished_pcf in squished_files:
        base_name = squished_pcf.name
        print(f"Processing mod: {base_name}")
        file_handler.process_file(
            base_name,
            pcf_mod_processor(str(squished_pcf)),
            create_backup=False
        )

    if not backup_manager.deploy_to_game():
        print("Failed to deploy to game directory")
        return

    # custom folder shenanigans
    if folder_setup.mods_everything_else_dir.exists():
        custom_dir = Path(config['tf_dir']) / 'custom'
        custom_dir.mkdir(exist_ok=True)
        new_pak = vpk.new(str(folder_setup.mods_everything_else_dir))
        new_pak.save(custom_dir / random.choice(CUSTOM_VPK_NAMES))

    folder_setup.cleanup_temp_folders()

    print("Processing complete!")

if __name__ == "__main__":
    main()
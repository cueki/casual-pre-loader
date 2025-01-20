import os
from pathlib import Path
import yaml
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from tools.backup_manager import BackupManager
from tools.pcf_squish import ParticleMerger
from tools.vpk_unpack import VPKExtractor


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # initialize backup manager with game VPK path
    backup_manager = BackupManager(config['vpk_file'])

    # create initial backup if it doesn't exist
    if not backup_manager.create_initial_backup():
        print("Failed to create/verify backup")
        return

    # prepare fresh working copy from backup
    if not backup_manager.prepare_working_copy():
        print("Failed to prepare working copy")
        return

    working_vpk_path = backup_manager.get_working_vpk_path()

    output_dir = 'mods'
    user_vpk = VPKHandler('20241223.vpk')
    VPKExtractor(user_vpk, output_dir).extract_files()

    # initialize handlers
    vpk_handler = VPKHandler(str(working_vpk_path))
    file_handler = FileHandler(vpk_handler)

    ParticleMerger(file_handler, vpk_handler, "mods/particles/").process()

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
    mod_files = Path("output/").glob('*.pcf')

    for mod_file in mod_files:
        base_name = mod_file.name
        print(f"Processing mod: {base_name}")
        file_handler.process_file(
            base_name,
            pcf_mod_processor(str(mod_file)),
            create_backup=False
        )
        os.remove(mod_file)

    if not backup_manager.deploy_to_game():
        print("Failed to deploy to game directory")
        return

    if Path('output/').exists():
        Path('output/').rmdir()

    print("Processing complete!")

if __name__ == "__main__":
    main()
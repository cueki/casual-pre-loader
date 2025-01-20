import os
from pathlib import Path
import yaml
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor
from tools.pcf_squish import ParticleMerger


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    vpk_file = config['vpk_file']
    if not os.path.exists(vpk_file):
        print("vpk_file does not exist")
        return

    # initialize handlers
    vpk_handler = VPKHandler(vpk_file)
    file_handler = FileHandler(vpk_handler)

    ParticleMerger(file_handler, vpk_handler, "mods/").process()

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


if __name__ == "__main__":
    main()
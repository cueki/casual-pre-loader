import os
from pathlib import Path
import yaml
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from models.pcf_file import PCFFile
from operations.file_processors import pcf_mod_processor, pcf_empty_root_processor, pcf_color_processor
from operations.pcf_compress import remove_duplicate_elements
from operations.pcf_merge import merge_pcf_files
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

    # # pre-process the pcf files that are too large
    # merge_files = Path("bugged2/").glob('*.pcf')
    # target_pcf = PCFFile(Path("bigboom.pcf")).decode()
    # output_path = Path("fat.pcf")
    #
    # for merge_file in merge_files:
    #     base_name = merge_file.name
    #     print(f"Merging mod: {base_name} into {output_path.name}")
    #
    #     current_pcf = PCFFile(merge_file).decode()
    #     target_pcf = merge_pcf_files(target_pcf, current_pcf)
    #
    #     file_handler.process_file(
    #         base_name,
    #         pcf_empty_root_processor(),
    #         create_backup=False
    #     )
    #
    # # item_fx.pcf now contains 10 pcf files worth of data because its so large it can fit it all
    # target_pcf.encode(output_path)

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
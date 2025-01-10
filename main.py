import os
from pathlib import Path
import yaml
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import *


def pcf_mod_processor(mod_path: str):
    def process_pcf(game_pcf: PCFFile) -> PCFFile:
        # Load the mod PCF
        mod_pcf = PCFFile(mod_path)
        mod_pcf.decode()
        return compress_duplicate_elements(mod_pcf)

    return process_pcf


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    vpk_file = config['vpk_file']
    if not os.path.exists(vpk_file):
        print("vpk_file does not exist")
        return

    # Initialize handlers
    vpk_handler = VPKHandler(vpk_file)
    file_handler = FileHandler(vpk_handler)

    # Define color targets
    targets = {
        'red': {
            'color1': (255, 128, 128),
            'color2': (255, 128, 128),
            'color_fade': (255, 128, 255)
        },
        'blue': {
            'color1': (128, 128, 255),
            'color2': (128, 128, 255),
            'color_fade': (128, 255, 255)
        },
        'neutral': {
            'color1': (255, 192, 128),
            'color2': (255, 192, 128),
            'color_fade': (192, 128, 255)
        }
    }

    # Process specific PCF files from config
    # for pcf_entry in config['pcf_files']:
    #     success = pcf_handler.process_pcf(pcf_entry['file'], processor)
    #     print(f"Processed {pcf_entry['file']}: {'Success' if success else 'Failed'}")

    # Process all PCF files
    # for k in file_handler.list_pcf_files():
    #     # success = file_handler.process_file(k, pcf_color_processor(targets))
    #     success = file_handler.process_file(k, pcf_duplicate_index_processor())
    #     print(f"Processed {k}: {'Success' if success else 'Failed'}")

    # Process all VMT files
    # for k in file_handler.list_vmt_files():
    #     success = file_handler.process_file(k, vmt_space_processor())
    #     print(f"Processed {k}: {'Success' if success else 'Failed'}")

    # file_handler.process_file("softglow.vmt", vmt_space_processor())
    # file_handler.process_file(
    #     "softglow.vmt",
    #     vmt_texture_replace_processor("Effects/softglow", "Effects/tp_floorglow")
    # )

    mods_path = Path("mods/")
    mod_files = list(mods_path.glob('*.pcf'))

    for mod_file in mod_files:
        # Get the base filename to match against VPK files
        base_name = mod_file.name
        print(f"Processing mod: {base_name}")

        # Process the file
        success = file_handler.process_file(
            base_name,
            pcf_mod_processor(str(mod_file)),
            create_backup=True
        )
        print(f"Processed {base_name}: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    main()
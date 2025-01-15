import os
from pathlib import Path
import yaml
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import *
from operations.pcf_merge import merge_pcf_files


def merge_pcf_directory(directory, output_path, file_handler, base_pcf_path):
    try:
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            print(f"Directory does not exist: {directory}")
            return False

        pcf_files = list(directory.glob('*.pcf'))
        if not pcf_files:
            print(f"No PCF files found in {directory}")
            return False

        base_pcf = PCFFile(base_pcf_path).decode()

        for pcf_path in pcf_files:
            print(f"Processing {pcf_path.name}...")

            current_pcf = PCFFile(str(pcf_path))
            current_pcf.decode()
            base_pcf = merge_pcf_files(base_pcf, current_pcf)

            file_handler.process_file(
                pcf_path.name,
                pcf_empty_root_processor(),
                create_backup=False
            )

        # Save the merged PCF
        base_pcf.encode(str(output_path))
        print(f"Successfully created merged PCF at {output_path}")
        return True

    except Exception as e:
        print(f"Error merging PCF files: {str(e)}")
        return False


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

    large_mods_path = Path("bugged/")
    output_path = Path("mods/item_fx.pcf")
    base_pcf_path=Path("item_fx.pcf")

    merge_pcf_directory(
        directory=large_mods_path,
        output_path=output_path,
        file_handler=file_handler,
        base_pcf_path=base_pcf_path
    )

    mods_path = Path("mods/")
    mod_files = list(mods_path.glob('*.pcf'))

    for mod_file in mod_files:
        # Get the base filename to match against VPK files
        base_name = mod_file.name
        print(f"Processing mod: {base_name}")

        # Process the file
        file_handler.process_file(
            base_name,
            pcf_mod_processor(str(mod_file)),
            create_backup=False
        )



if __name__ == "__main__":
    main()
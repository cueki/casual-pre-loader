import os
import yaml
from typing import Dict
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from models.pcf_file import PCFFile
from operations.color import analyze_pcf_colors, transform_team_colors, RGB
from operations.vmt_wasted_space import VMTSpaceAnalyzer


def color_processor(targets: Dict[str, Dict[str, RGB]]):
    def process(pcf: PCFFile) -> PCFFile:
        colors = analyze_pcf_colors(pcf)
        return transform_team_colors(pcf, colors, targets)

    return process


def create_vmt_space_processor():
    analyzer = VMTSpaceAnalyzer()

    def process_vmt(content: bytes) -> bytes:
        return analyzer.consolidate_spaces(content)

    return process_vmt


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
    for k in file_handler.list_pcf_files():
        success = file_handler.process_file(k, color_processor(targets))
        print(f"Processed {k}: {'Success' if success else 'Failed'}")

    # Process all VMT files
    for k in file_handler.list_vmt_files():
        success = file_handler.process_file(k, create_vmt_space_processor())
        print(f"Processed {k}: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    main()
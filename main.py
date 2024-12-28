import os
import yaml
from typing import Dict
from handlers.pcf_handler import PCFHandler
from handlers.vpk_handler import VPKHandler
from models.pcf_file import PCFFile
from operations.color import analyze_pcf_colors, transform_team_colors, RGB
from core.constants import PCF_OFFSETS

def color_processor(targets: Dict[str, Dict[str, RGB]]):
    def process(pcf: PCFFile) -> PCFFile:
        colors = analyze_pcf_colors(pcf)
        return transform_team_colors(pcf, colors, targets)

    return process


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    vpk_file = config['vpk_file']
    if not os.path.exists(vpk_file):
        print("vpk_file does not exist")
        return

    # Initialize handlers
    vpk_handler = VPKHandler(vpk_file)
    pcf_handler = PCFHandler(vpk_handler)

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

    # Create processor function
    processor = color_processor(targets)

    # Process specific PCF files from config
    # for pcf_entry in config['pcf_files']:
    #     success = pcf_handler.process_pcf(pcf_entry['file'], processor)
    #     print(f"Processed {pcf_entry['file']}: {'Success' if success else 'Failed'}")

    # Process all PCF files
    for k in PCF_OFFSETS.keys():
        success = pcf_handler.process_pcf(k, processor)
        print(f"Processed {k}: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    main()
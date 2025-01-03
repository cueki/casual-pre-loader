import os
import yaml
import re
from typing import Dict
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from models.pcf_file import PCFFile
from operations.color import analyze_pcf_colors, transform_team_colors, RGB
from operations.vmt_wasted_space import VMTSpaceAnalyzer, find_closing_bracket
from operations.detectors import comment_detector, quote_detector


def vmt_texture_replacer(old_texture: str, new_texture: str):
    def process_vmt(content: bytes) -> bytes:
        try:
            text = content.decode('utf-8')
            original_size = len(content)

            pattern = f'\\$basetexture\\s+{re.escape(old_texture)}'
            modified = re.sub(pattern, f'$basetexture {new_texture}', text)
            size_diff = len(modified.encode('utf-8')) - original_size

            closing_pos = find_closing_bracket(modified)
            if closing_pos == -1:
                return content

            # Find the last whitespace line before the closing bracket
            lines = modified[:closing_pos].splitlines(keepends=True)
            if not lines:
                return content

            # Get the last line which should be our whitespace line
            whitespace_line = lines[-1]
            available_space = len(whitespace_line.rstrip('\n'))  # Don't count the newline in available space

            if size_diff < -1:
                # Adding space, keep the newline
                modified = (modified[:closing_pos] +
                            ' ' * (-size_diff - 1) + '\n' +
                            modified[closing_pos:])
            elif size_diff > -1:
                if available_space < size_diff:
                    return content

                # Find where the whitespace line begins
                whitespace_start = closing_pos - len(whitespace_line)
                # Remove characters from the whitespace but preserve the newline
                modified = (modified[:whitespace_start] +
                            whitespace_line[:-1][:-size_diff] + '\n' +
                            modified[closing_pos:])

            return modified.encode('utf-8')

        except UnicodeDecodeError:
            return content

    return process_vmt


def color_processor(targets: Dict[str, Dict[str, RGB]]):
    def process_pcf(pcf: PCFFile) -> PCFFile:
        colors = analyze_pcf_colors(pcf)
        return transform_team_colors(pcf, colors, targets)

    return process_pcf


def vmt_space_processor():
    analyzer = VMTSpaceAnalyzer()
    analyzer.add_detector(comment_detector)
    analyzer.add_detector(quote_detector)

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
    # for k in file_handler.list_vmt_files():
    #     success = file_handler.process_file(k, vmt_space_processor())
    #     print(f"Processed {k}: {'Success' if success else 'Failed'}")

    file_handler.process_file("softglow.vmt", vmt_space_processor())
    file_handler.process_file(
        "softglow.vmt",
        vmt_texture_replacer("Effects/softglow", "Effects/tp_floorglow")
    )


if __name__ == "__main__":
    main()
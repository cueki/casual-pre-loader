import os
import yaml
import random
from typing import Dict
from core.constants import PCF_OFFSETS
from models.pcf_file import PCFFile
from operations.color import analyze_pcf_colors, transform_team_colors, RGB
from operations.vpk import VPKOperations
from tools.color_wheel import animate_color_shift


def generate_random_rgb():
    return (
        random.randint(1, 254),
        random.randint(1, 254), # 1-254 to avoid my filter of 0, 0, 0 and 255, 255, 255
        random.randint(1, 254)
    )


def generate_random_targets():
    return {
        'red': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        },
        'blue': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        },
        'neutral': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        }
    }


def process_pcf(vpk_file: str, pcf_file: str, targets: Dict[str, Dict[str, RGB]]) -> None:
    # temp particle file for reading and writing - get it from the vpk with the offsets in constants using vpk_ops
    temp_pcf = f"temp_{pcf_file}"
    pcf = PCFFile(temp_pcf)
    offset, size = PCF_OFFSETS.get(pcf_file)
    vpk_ops = VPKOperations
    vpk_ops.extract_pcf(
        vpk_path=vpk_file,
        offset=offset,
        size=size,
        output_path=temp_pcf
    )

    # "decode" and extract color info from the file
    pcf.decode()
    colors = analyze_pcf_colors(pcf)
    result = transform_team_colors(pcf, colors, targets)

    animate_color_shift(colors, targets, save_video=False) # this is the color wheel animation, is broken rn

    # patch the changes back into the vpk with the new particle file using the same offset
    result = vpk_ops.patch_pcf(
        vpk_path=vpk_file,
        offset=offset,
        size=size,
        pcf=result,
        create_backup=True
    )
    print(f"Processed {pcf_file}: {result}")

    # cleanup temp
    os.remove(temp_pcf)


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    vpk_file = config['vpk_file']
    pcf_files = config['pcf_files']

    if not os.path.exists(vpk_file):
        print("vpk_file does not exist")

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
    # peek_file_header("temp_medicgun_beam.pcf")
    # DO ONLY WHAT IS IN CONFIG.YAML
    for pcf_name in pcf_files:
        # targets = generate_random_targets() # if u want random
        process_pcf(vpk_file, pcf_name['file'], targets)

    # DO ALL PARTICLE FILES !!!
    # for pcf_name in PCF_OFFSETS:
    #     # targets = generate_random_targets() # if u want random
    #     process_pcf(vpk_file, pcf_name, targets)


if __name__ == '__main__':
    main()
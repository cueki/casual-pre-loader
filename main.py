import os
import json
from idlelib.pyshell import restart_line
from pathlib import Path
from typing import Tuple, List, Dict
import matplotlib.pyplot as plt
import yaml
import argparse
from dataclasses import dataclass
from core.constants import PCF_OFFSETS, AttributeType
from core.errors import PCFError
from core.traversal import PCFTraversal
from models.pcf_file import PCFFile
from operations.color import color_shift, transform_with_shift, analyze_pcf_colors, transform_team_colors, RGB
from operations.vpk import VPKOperations, VPKSearchResult
from tools.color_wheel import plot_rgb_vector, animate_color_shift
import random

@dataclass
class ColorConfig:
    red: [int, int, int]
    blue: [int, int, int]


@dataclass
class PCFConfig:
    vpk_file: str
    pcf_file: str
    colors: ColorConfig


def load_config(config_path: str) -> PCFConfig:
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
        return PCFConfig(
            vpk_file=data['vpk_file'],
            pcf_file=data['pcf_file'],
            colors=ColorConfig(
                tuple(data['colors']['red']),
                tuple(data['colors']['blue'])
            )
        )


def generate_random_rgb():
    return (
        random.randint(100, 255),
        random.randint(50, 255),
        random.randint(50, 255)
    )


def generate_random_targets():
    return {
        'red': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'tint_clamp': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        },
        'blue': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'tint_clamp': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        },
        'neutral': {
            'color1': generate_random_rgb(),
            'color2': generate_random_rgb(),
            'tint_clamp': generate_random_rgb(),
            'color_fade': generate_random_rgb()
        }
    }


def process_pcf(vpk_file: str, pcf_file: str, targets: Dict[str, Dict[str, RGB]]) -> None:

    temp_pcf = f"temp_{pcf_file}"
    pcf = PCFFile(temp_pcf)

    offset, size = PCF_OFFSETS.get(pcf_file)

    vpk_ops = VPKOperations
    extracted_pcf = vpk_ops.extract_pcf(
        vpk_path=vpk_file,
        offset=offset,
        size=size,
        output_path=temp_pcf
    )

    pcf.decode()
    colors = analyze_pcf_colors(pcf, debug=True)
    result = transform_team_colors(pcf, colors, targets, debug=True)

    # animate_color_shift(colors, targets, save_video=False)

    result = vpk_ops.patch_pcf(
        vpk_path=vpk_file,
        offset=offset,
        size=size,
        pcf=result,
        create_backup=True
    )
    print(f"Processed {pcf_file}: {result}")

    os.remove(temp_pcf)


def analyze_pcf_elements(pcf_path: Path):
    pcf = PCFFile(pcf_path)
    pcf.decode()
    elements_info = []

    for idx, element in enumerate(pcf.elements):
        element_info = {
            'index': idx,
            'element_name': element.element_name,
            'type_name_index': element.type_name_index,
            'data_signature': element.data_signature.hex(),
            'attributes': {}
        }

        for attr_name, (attr_type, value) in element.attributes.items():
            element_info['attributes'][attr_name] = {
                'type': attr_type.name,
                'value': value
            }

        elements_info.append(element_info)

    return elements_info


def print_pcf_analysis(elements_info):
    def convert_bytes(data):
        if isinstance(data, bytes):
            return data.decode('ascii', errors='replace')
        if isinstance(data, dict):
            return {convert_bytes(k): convert_bytes(v) for k, v in data.items()}
        if isinstance(data, list):
            return [convert_bytes(i) for i in data]
        return data

    cleaned_data = convert_bytes(elements_info)
    json_object = json.dumps(cleaned_data, indent=2, default=str)
    with open("sample.json", "w") as outfile:
        outfile.write(json_object)


def main():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # red_target = 0, 255, 127
    # blue_target = 255, 127, 0
    # neutral_target = 127, 0, 255
    # red_target = 0, 255, 0
    # blue_target = 0, 255, 0
    # neutral_target = 0, 255, 0
    vpk_file = config['vpk_file']
    #
    # targets = {
    #     'red': {
    #         'color1': (255, 105, 180),
    #         'color2': (144, 238, 144),
    #         'tint_clamp': (255, 0, 255),
    #         'color_fade': (255, 105, 180)
    #     },
    #     'blue': {
    #         'color1': (255, 105, 180),
    #         'color2': (144, 238, 144),
    #         'tint_clamp': (255, 0, 255),
    #         'color_fade': (255, 105, 180)
    #     },
    #     'neutral': {
    #         'color1': (255, 105, 180),
    #         'color2': (144, 238, 144),
    #         'tint_clamp': (255, 0, 255),
    #         'color_fade': (255, 105, 180)
    #     }
    # }

    for pcf_name in PCF_OFFSETS:
        print(f"Processing {pcf_name}")
        targets = generate_random_targets()
        print(f"Generated targets for {pcf_name}:", targets)
        process_pcf(vpk_file, pcf_name, targets)

    # tracer = Path("rockettrail.pcf")
    # tracer_pcf = PCFFile(tracer)
    # tracer_pcf.decode()
    # colors = analyze_pcf_colors(tracer_pcf, debug=True)
    # result = transform_team_colors(tracer_pcf, colors, targets, debug=)
    # print(f"Processed {tracer_pcf}: {result}")


if __name__ == '__main__':
    main()
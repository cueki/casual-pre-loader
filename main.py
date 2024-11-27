import os
import json
from idlelib.pyshell import restart_line
from pathlib import Path
from typing import Tuple, List
import matplotlib.pyplot as plt
import yaml
import argparse
from dataclasses import dataclass
from core.constants import PCF_OFFSETS, AttributeType
from core.errors import PCFError
from core.traversal import PCFTraversal
from models.pcf_file import PCFFile
from operations.color import color_shift, transform_with_shift, analyze_pcf_colors, RGB, is_color_attribute
from operations.vpk import VPKOperations, VPKSearchResult
from tools.color_wheel import plot_rgb_vector, animate_color_shift


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


def process_pcf(vpk_file: str, pcf_file: str, red_target: Tuple[int, int, int],
                blue_target: Tuple[int, int, int], neutral_target: Tuple[int, int, int]) -> None:

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
    red_list, blue_list, neutral_list = analyze_pcf_colors(pcf)

    result = pcf
    if red_list and blue_list:
        red_shift = color_shift(red_list, red_target)
        result = transform_with_shift(result, red_list, red_shift)
        blue_shift = color_shift(blue_list, blue_target)
        result = transform_with_shift(result, blue_list, blue_shift)
        if neutral_list:  # Only process neutral if it exists
            neutral_shift = color_shift(neutral_list, neutral_target)
            result = transform_with_shift(result, neutral_list, neutral_shift)
    elif not red_list or not blue_list:
        all_colors = red_list + blue_list + neutral_list
        if all_colors:
            neutral_shift = color_shift(all_colors, neutral_target)
            result = transform_with_shift(result, all_colors, neutral_shift)

    animate_color_shift(red_list, red_target, blue_list, blue_target, neutral_list, neutral_target, save_video=False)

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

    red_target = 0, 255, 127
    blue_target = 255, 127, 0
    neutral_target = 127, 0, 255
    vpk_file = config['vpk_file']
    # for pcf_entry in config['pcf_files']:
    #     pcf_file = pcf_entry['file']
    #     red_target = pcf_entry['colors']['red']
    #     blue_target = pcf_entry['colors']['blue']
    #     process_pcf(vpk_file, pcf_file, red_target, blue_target, neutral_target)

    for pcf_name in PCF_OFFSETS:
        print(pcf_name)
        process_pcf(vpk_file, pcf_name, red_target, blue_target, neutral_target)

    # tracer = Path("disguise.pcf")
    # tracer_pcf = PCFFile(tracer)
    # tracer_pcf.decode()
    # red_c, blue_c, neut_c = analyze_pcf_colors(tracer_pcf)
    # print(red_c)
    # print(blue_c)
    # print(neut_c)

if __name__ == '__main__':
    main()
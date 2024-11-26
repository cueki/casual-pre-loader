import os

import matplotlib.pyplot as plt
import yaml
import argparse
from dataclasses import dataclass
from core.constants import PCF_OFFSETS
from models.pcf_file import PCFFile
from operations.color import color_shift, transform_with_shift, analyze_pcf_colors
from operations.vpk import VPKOperations
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


def main():
    parser = argparse.ArgumentParser(description='PCF Color Transform Tool')
    parser.add_argument('--plot', action='store_true', help='Plot color vectors')
    args = parser.parse_args()

    config = load_config("config.yaml")
    temp_pcf = "temp.pcf"

    offset, size = PCF_OFFSETS.get(config.pcf_file)
    vpk_ops = VPKOperations
    pcf = PCFFile(temp_pcf)

    vpk_ops.extract_pcf(
        vpk_path=config.vpk_file,
        offset=offset,
        size=size,
        output_path=temp_pcf
    )

    pcf.decode()
    color_list = analyze_pcf_colors(pcf)
    red_list, blue_list = color_list

    red_shift = color_shift(red_list, config.colors.red)
    blue_shift = color_shift(blue_list, config.colors.blue)

    stage_1 = transform_with_shift(pcf, red_list, red_shift)
    stage_2 = transform_with_shift(stage_1, blue_list, blue_shift)

    # if args.plot:
    #     shifted_colors_list = []
    #     colors = analyze_pcf_colors(stage_2)
    #     for c in colors[0]: shifted_colors_list.append(c)
    #     for c in colors[1]: shifted_colors_list.append(c)
    #     plot_rgb_vector(shifted_colors_list)

    unshifted_colors_list = []
    stage_0_colors = color_list
    for c in stage_0_colors[0]: unshifted_colors_list.append(c)
    for c in stage_0_colors[1]: unshifted_colors_list.append(c)

    shifted_colors_list = []
    stage_2_colors = analyze_pcf_colors(stage_2)
    for c in stage_2_colors[0]: shifted_colors_list.append(c)
    for c in stage_2_colors[1]: shifted_colors_list.append(c)

    animate_color_shift(red_list, config.colors.red, blue_list, config.colors.blue)
    plt.show()
    # result = vpk_ops.patch_pcf(
    #     vpk_path=config.vpk_file,
    #     offset=offset,
    #     size=size,
    #     pcf=stage_2,
    #     create_backup=True
    # )

    os.remove(temp_pcf)
    # print(result)


if __name__ == '__main__':
    main()
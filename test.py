import copy
import os
from typing import Tuple, List
from core.constants import AttributeType, PCF_OFFSETS
from models.pcf_file import PCFFile
from operations.color import get_color_dominance
from codec.codec import decode_pcf_file
from tools.color_wheel import plot_rgb_vector
from operations.color import color_shift
from operations.vpk import VPKOperations

temp_pcf = "temp.pcf"
vpk_file = "tf2_misc_000.vpk"
pcf_file = "medicgun_beam.pcf"

mint = 66, 245, 153
yellow = 233, 245, 66
pink = 255, 79, 164
purple = 212, 102, 255
green = 173, 255, 47

offset, size = PCF_OFFSETS.get(f"{pcf_file}")
vpk_ops = VPKOperations
hsv_list = []

def analyze_pcf_colors(pcf_input):
    red_colors = []
    blue_colors = []

    for element in pcf_input.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue

            r, g, b, a = value
            team = get_color_dominance((r, g, b, a))
            if team == 'red':
                red_colors.append((r, g, b))
            if team == 'blue':
                blue_colors.append((r, g, b))
            else:
                continue

    return red_colors, blue_colors

def transform_with_shift(pcf: PCFFile, original_colors: List[Tuple[int, int, int]],
                         shifted_colors: List[Tuple[int, int, int]]) -> PCFFile:

    color_map = {orig: shifted for orig, shifted in zip(original_colors, shifted_colors)}
    result_pcf = copy.deepcopy(pcf)

    for element in result_pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue

            r, g, b, a = value
            rgb = (r, g, b)

            if rgb in color_map:
                new_r, new_g, new_b = color_map[rgb]
                element.attributes[attr_name] = (attr_type, (new_r, new_g, new_b, a))

    return result_pcf

extracted_pcf = vpk_ops.extract_pcf(
    vpk_path=vpk_file,
    offset=offset,
    size=size,
    output_path=temp_pcf
)

temp_pcf_decode = decode_pcf_file(temp_pcf)
color_list = analyze_pcf_colors(temp_pcf_decode)
red_list, blue_list = color_list

red_shift = color_shift(red_list, purple)
blue_shift = color_shift(blue_list, pink)

stage_1 = transform_with_shift(temp_pcf_decode, red_list, red_shift)
stage_2 = transform_with_shift(stage_1, blue_list, blue_shift)

shifted_colors_list = []
colors = analyze_pcf_colors(stage_2)
for c in colors[0]:
    shifted_colors_list.append(c)
for c in colors[1]:
    shifted_colors_list.append(c)
plot_rgb_vector(shifted_colors_list)

result = vpk_ops.patch_pcf(
    vpk_path=vpk_file,
    offset=offset,
    pcf=stage_2,
    create_backup=True
)
os.remove(temp_pcf)
print(result)
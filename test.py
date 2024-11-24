import copy
from typing import Tuple, List
import numpy as np
from core.constants import AttributeType
from core.utils import find_in_vpk, extract_pcf_signature
from models.pcf_file import PCFFile
from operations.color import get_color_dominance, average_rgb, RGB, ColorTransform
from codec.codec import decode_pcf_file, encode_pcf_file
from models.color_wheel import plot_rgb_colors, plot_rgb_vector, rgb_to_hsv
from operations.color import color_shift
from operations.vpk import VPKOperations

vpk_file = "tf2_misc_000.vpk"
pcf_file = "medicgun_beam.pcf"
output_pcf = "modified_beam.pcf"
pink_output_pcf = "stage1.pcf"
purple_output_pcf = "stage2.pcf"

mint = 66, 245, 153
yellow = 233, 245, 66
pink = 255, 79, 164
purple = 212, 102, 255
green = 173, 255, 47

red = tuple(pink)
blue = tuple(purple)

# Find PCFs in VPK
# all_pcfs = VPKOperations.find_pcfs(vpk_file)
# for result in all_pcfs:
#     print(f"Found PCF at offset {result.offset}, version {result.pcf_version}")
# print(extract_pcf_signature(pcf_file))

pcf = decode_pcf_file(pcf_file)
print(pcf)
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


color_list = analyze_pcf_colors(pcf)
red_list = color_list[0]
blue_list = color_list[1]
red_shift = color_shift(red_list, pink)
blue_shift = color_shift(blue_list, purple)

# print("number of red particles:", len(colors[0]))
# print("number of blue particles:", len(colors[1]))
stage1 = transform_with_shift(pcf, red_list, red_shift)
# encode_pcf_file(stage1, "stage1.pcf")
# stage1_pcf = decode_pcf_file("stage1.pcf")
stage2 = transform_with_shift(stage1, blue_list, blue_shift)
encode_pcf_file(stage2, "stage2.pcf")

# shifted_colors = []

# for c in pink_shift:
#     shifted_colors.append(c)
# for c in purple_shift:
#     shifted_colors.append(c)
# plot_rgb_vector(shifted_colors)
unshifted_colors = []
colors = analyze_pcf_colors(decode_pcf_file("stage2.pcf"))
for c in colors[0]:
    unshifted_colors.append(c)
for c in colors[1]:
    unshifted_colors.append(c)
plot_rgb_vector(unshifted_colors)

with open(vpk_file, 'rb') as vpk_bytes:
    offset = find_in_vpk(vpk_bytes.read(), extract_pcf_signature(pcf_file))
    offset = offset[0][0]

vpk_ops = VPKOperations()
result = vpk_ops.patch_pcf(
    vpk_path="tf2_misc_000.vpk",
    offset=offset,  # Byte offset where PCF starts in VPK
    pcf=stage2,
    create_backup=True  # Creates .backup file
)
print(result)
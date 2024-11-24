import numpy as np
from core.constants import AttributeType
from operations.color import get_color_dominance, average_rgb
from codec.codec import decode_pcf_file
from models.color_wheel import plot_rgb_colors, plot_rgb_vector, rgb_to_hsv
from operations.color import color_shift


vpk_file = "tf2_misc_000.vpk"
pcf_file = "medicgun_beam.pcf"
output_pcf = "modified_beam.pcf"

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
# with open(vpk_file, 'rb') as vpk_bytes:
#     offset = find_in_vpk(vpk_bytes.read(), extract_pcf_signature(pcf_file))
#     offset = offset[0][0]

pcf = decode_pcf_file(pcf_file)
hsv_list = []


def analyze_pcf_colors():
    red_colors = []
    blue_colors = []

    for element in pcf.elements:
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


colors = analyze_pcf_colors()

shifted_colors = []
pink_shift = color_shift(colors[0], pink)
purple_shift = color_shift(colors[1], green)
for c in pink_shift:
    shifted_colors.append(c)
for c in purple_shift:
    shifted_colors.append(c)

unshifted_colors = []
for c in colors[0]:
    unshifted_colors.append(c)
for c in colors[1]:
    unshifted_colors.append(c)

plot_rgb_vector(unshifted_colors)
plot_rgb_vector(shifted_colors)


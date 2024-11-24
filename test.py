import copy
import os
from core.constants import AttributeType, PCF_OFFSETS
from codec.codec import decode_pcf_file
from tools.color_wheel import plot_rgb_vector
from operations.color import color_shift, transform_with_shift, analyze_pcf_colors
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
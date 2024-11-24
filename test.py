from core.constants import AttributeType
from operations.color import get_color_dominance
from codec.codec import decode_pcf_file
from models.color_wheel import plot_rgb_colors, plot_specific_colors

vpk_file = "tf2_misc_000.vpk"
pcf_file = "summer2024_unusuals.pcf"
output_pcf = "modified_beam.pcf"

pink = 255, 79, 164
purple = 212, 102, 255

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
def analyze_pcf_colors(file):
    colors = []

    for element in pcf.elements:
        for attr_name, (attr_type, value) in element.attributes.items():
            if attr_type != AttributeType.COLOR:
                continue

            r, g, b, a = value
            team = get_color_dominance((r, g, b, a))
            if not team:
                continue

            colors.append((r, g, b))

    return colors

colors = analyze_pcf_colors(pcf)

plot_specific_colors(colors)
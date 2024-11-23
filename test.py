from operations.vpk import VPKOperations
from core.utils import find_in_vpk, extract_pcf_signature, get_file_size
from operations.color import transform_team_colors, print_color_changes
from codec.codec import decode_pcf_file, encode_pcf_file

vpk_file = "tf2_misc_000.vpk"
pcf_file = "medicgun_beam.pcf"
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
with open(vpk_file, 'rb') as vpk_bytes:
    offset = find_in_vpk(vpk_bytes.read(), extract_pcf_signature(pcf_file))
    offset = offset[0][0]

pcf = decode_pcf_file(pcf_file)
modified_pcf, result = transform_team_colors(pcf, red, blue)
print_color_changes(result)
if result.has_changes:
    encode_pcf_file(modified_pcf, output_pcf)

# Extract specific PCF
# VPKOperations.extract_pcf(z
#     "tf2_misc_000.vpk",
#     offset=offset,
#     size=get_file_size(pcf_file),
#     output_path="extracted.pcf"
# )

# Modify and patch PCF
# pcf = PCFCodec.decode("modified.pcf")
# result = VPKOperations.patch_pcf(
#     "tf2_misc_000.vpk",
#     offset=1234,
#     pcf=pcf
# )
#
# if result.success:
#     print(f"Patched PCF: {result.new_size} bytes written")
#     print(f"Backup created at: {result.backup_path}")
# else:
#     print(f"Patch failed: {result.error_message}")
#
# # Batch process VPKs
# def process_vpk(vpk_path: str) -> bool:
#     vpks = VPKOperations.find_pcfs(vpk_path)
#     return len(vpks) > 0
#
# results = VPKOperations.batch_process_vpks(
#     "game_misc_*.vpk",
#     process_vpk
# )
import json
from pathlib import Path
from core.utils import find_in_vpk, extract_pcf_signature, get_file_size

vpk_file = "../tf2_misc_000.vpk"

def scan_pcf_offsets(folder_path: str, output_path: str = "pcf_offsets.json"):
    offsets = {}

    for file_path in Path(folder_path).glob("*.pcf"):
        try:
            with open(vpk_file, 'rb') as vpk_bytes:
                offset = find_in_vpk(vpk_bytes.read(), extract_pcf_signature(file_path))
                offset = offset[0][0]
                if offset:
                    offsets[file_path.name] = {
                        "offset": offset,
                        "size": get_file_size(file_path)
                        }


        except Exception as e:
            print(f"Error processing {file_path}: PCF is not in this VPK")

    # Write offsets to JSON file
    with open(output_path, "w") as f:
        json.dump(offsets, f, indent=4)
    # Generate constants.py content
    constants = ["from typing import Dict, Tuple\n\n", "PCF_OFFSETS: Dict[str, Tuple[int, int]] = {"]
    for filename, data in offsets.items():
        constants.append(f'    "{filename}": ({data["offset"]}, {data["size"]}),')
    constants.append("}")

    with open("../core/constants.py", "a") as f:
        f.write("\n\n" + "\n".join(constants))


if __name__ == "__main__":
    scan_pcf_offsets("../pcf_files")
import struct
from models.pcf_file import PCFFile
from core.traversal import PCFTraversal
from core.constants import PCF_OFFSETS, AttributeType
from operations.vpk import VPKOperations
import os
from models.vpk_file import VPKParser
import hashlib
from typing import Dict


def analyze_pcf_materials(vpk_file: str, pcf_file: str) -> None:
    """
    Analyze a PCF file for elements with material attributes

    Args:
        vpk_file: Path to VPK file
        pcf_file: Name of PCF file to analyze
    """
    # Get PCF offset and size from constants
    offset, size = PCF_OFFSETS.get(pcf_file)
    if not offset:
        print(f"Error: Could not find offset for {pcf_file}")
        return

    # Create temporary file for PCF extraction
    temp_pcf = f"temp_{pcf_file}"

    try:
        # Extract PCF from VPK
        print(f"\nAnalyzing {pcf_file}...")
        extracted = VPKOperations.extract_pcf(
            vpk_path=vpk_file,
            offset=offset,
            size=size,
            output_path=temp_pcf
        )

        if not extracted:
            print(f"Error: Failed to extract {pcf_file}")
            return

        # Load and decode PCF
        pcf = PCFFile(temp_pcf)
        pcf.decode()

        # Create traversal object
        traversal = PCFTraversal(pcf)

        # Find all attributes containing "material"
        material_attrs = traversal.find_attributes(
            attr_name_pattern="material",
            max_depth=-1  # Search all depths
        )

        # Print results
        found_materials = False
        for element, attr_name, (attr_type, value), depth in material_attrs:
            found_materials = True
            print(f"\nElement: {element.element_name.decode('ascii', errors='replace')}")
            print(f"Depth: {depth}")
            print(f"Attribute: {attr_name}")
            if attr_type == AttributeType.STRING:
                try:
                    print(f"Material: {value.decode('ascii', errors='replace')}")
                except:
                    print(f"Material: {value}")
            else:
                print(f"Value: {value} (Type: {attr_type.name})")

        if not found_materials:
            print("No material attributes found")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_pcf):
            os.remove(temp_pcf)


def display_vpk_structure(vpk_dir_path: str, filter_path: str = None):
    parser = VPKParser(vpk_dir_path)
    parser.parse_directory()

    # Get all files and filter if needed
    files = sorted(parser.list_files())
    if filter_path:
        files = [f for f in files if f.startswith(filter_path)]

    # Create a tree structure
    current_path = ""
    indent = "  "

    print(f"\nDisplaying files in: {filter_path or 'root'}")
    print("-" * 50)

    for file in files:
        path_parts = file.split('/')

        # Handle root files
        if len(path_parts) == 1:
            print(f"└── {path_parts[0]}")
            continue

        # Handle files in directories
        directory = '/'.join(path_parts[:-1])
        filename = path_parts[-1]

        if directory != current_path:
            print(f"├── {directory}/")
            current_path = directory

        print(f"{indent}└── {filename}")

    print(f"\nTotal files: {len(files)}")


def patch_vpk_file(vpk_path: str):
    with open(vpk_path, 'rb') as f:
        data = bytearray(f.read())

    # Known offsets for materials/effects/softglow.vmt
    filename_offset = None
    offset = 28  # Skip header

    # Now look for materials/effects
    while offset < len(data):
        # print(data[offset:offset + len("materials/effects/softglow.vmt")])
        if data[offset:offset + len("softglow")] == b'softglow':
            filename_offset = offset
            offset = offset - 40
            print(data[offset:offset + 80])
            print("Found materials/effects/softglow path")

        offset += 1

    if filename_offset is None:
        print("Could not locate filename offset")
        return False

    print(f"Found filename at offset: {filename_offset}")

    # Replace "softglow" with "a\0\0\0\0\0\0" (maintain same length)
    data[filename_offset:filename_offset + 8] = b'a\0\0\0\0\0\0\0'

    # Calculate new MD5s
    header = struct.unpack('<7I', data[:28])
    tree_size = header[2]
    md5_section_size = header[3]
    other_md5_size = header[4]

    # Calculate offsets for MD5 sections
    tree_offset = 28
    md5_section_offset = tree_offset + tree_size
    other_md5_offset = md5_section_offset + md5_section_size

    # Calculate new checksums
    tree_md5 = hashlib.md5(data[tree_offset:tree_offset + tree_size]).digest()
    archive_md5 = hashlib.md5(data[md5_section_offset:md5_section_offset + md5_section_size]).digest()

    # Update checksums in VPK_OtherMD5Section
    data[other_md5_offset:other_md5_offset + 16] = tree_md5
    data[other_md5_offset + 16:other_md5_offset + 32] = archive_md5

    # Calculate and update whole file checksum last
    # Zero out the whole file checksum section first
    data[other_md5_offset + 32:other_md5_offset + 48] = b'\0' * 16
    whole_file_md5 = hashlib.md5(data).digest()
    data[other_md5_offset + 32:other_md5_offset + 48] = whole_file_md5

    # Write modified VPK
    output_path = f"{vpk_path}.modified"
    with open(output_path, 'wb') as f:
        f.write(data)

    print(f"Modified VPK written to {output_path}")
    print(f"New checksums:")
    print(f"Tree MD5: {tree_md5.hex()}")
    print(f"Archive MD5: {archive_md5.hex()}")
    print(f"Whole File MD5: {whole_file_md5.hex()}")

    return True


def modify_vpk():
    vpk_path = "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf/tf2_misc_dir.vpk"
    vpk = VPKParser(vpk_path)
    vpk.parse_directory()

    if 'materials/effects' in vpk.directory['vmt']:
        entry = vpk.directory['vmt']['materials/effects'].get('softglow')
        if entry:
            with open(vpk_path, 'r+b') as f:
                f.seek(entry.directory_offset)
                f.write(b'noobglow')
            print(f"CRC: {hex(entry.crc)}")
            print(f"Archive Index: {entry.archive_index}")
            print(f"Entry Offset: {entry.entry_offset}")
            print(f"Entry Length: {entry.entry_length}")
            print(f"Preload Bytes: {entry.preload_bytes}")
            print(f"Directory Offset: {entry.directory_offset}")
            return True
    return False


def process_vmt_comments(vpk_parser: VPKParser) -> Dict[str, int]:
    results = {}

    # Find all VMT files
    if 'vmt' not in vpk_parser.directory:
        return results

    for path in vpk_parser.directory['vmt']:
        for filename in vpk_parser.directory['vmt'][path]:
            entry = vpk_parser.directory['vmt'][path][filename]

            # Get VMT content
            vmt_data = vpk_parser.get_file_data('vmt', path, filename)
            if not vmt_data:
                continue

            try:
                # Decode VMT content
                vmt_text = vmt_data.decode('utf-8')

                # Find comment positions
                comment_positions = []
                i = 0
                while i < len(vmt_text):
                    if vmt_text[i:i + 2] == '//':
                        # Find start of comment line
                        start = vmt_text.rfind('\n', 0, i)
                        start = start + 1 if start != -1 else 0

                        # Find end of comment line
                        end = vmt_text.find('\n', i)
                        if end == -1:
                            end = len(vmt_text)

                        comment_positions.append((start, end))
                        i = end + 1
                    else:
                        i += 1

                if comment_positions:
                    # Convert to bytearray for modification
                    vmt_bytes = bytearray(vmt_data)

                    # Replace comments with null bytes
                    for start, end in reversed(comment_positions):
                        comment_length = end - start
                        vmt_bytes[start:end] = b' ' * comment_length

                    # Write back to VPK
                    archive_path = f"{vpk_parser.base_path}_{entry.archive_index:03d}.vpk"
                    with open(archive_path, 'r+b') as f:
                        f.seek(entry.entry_offset)
                        f.write(vmt_bytes)

                    full_path = f"{path}/{filename}.vmt" if path else f"{filename}.vmt"
                    results[full_path] = len(comment_positions)

            except (UnicodeDecodeError, IOError) as e:
                print(f"Error processing {filename}.vmt: {e}")

    return results


def count_whitespace(vpk_parser: VPKParser) -> Dict[str, Dict[str, int]]:
    results = {}
    total_whitespace = 0

    if 'vmt' not in vpk_parser.directory:
        return results

    for path in vpk_parser.directory['vmt']:
        for filename in vpk_parser.directory['vmt'][path]:
            vmt_data = vpk_parser.get_file_data('vmt', path, filename)
            if not vmt_data:
                continue

            try:
                whitespace_count = sum(1 for b in vmt_data if b == 0x20 or b == 0x09)
                full_path = f"{path}/{filename}.vmt" if path else f"{filename}.vmt"

                results[full_path] = {
                    'whitespace_bytes': whitespace_count,
                    'total_size': len(vmt_data),
                    'whitespace_percentage': round((whitespace_count / len(vmt_data)) * 100, 2)
                }

                total_whitespace += whitespace_count

            except (UnicodeDecodeError, IOError) as e:
                print(f"Error processing {filename}.vmt: {e}")

    results['__summary__'] = {
        'total_whitespace_bytes': total_whitespace,
        'total_files': len(results) - 1  # Subtract 1 for summary entry
    }

    return results


def main():
    # modify_vpk()
    # print_vpk_checksums('tf2_misc_dir.vpk')
    # print_vpk_checksums('tf2_misc_dir_mod.vpk')
    # text = read_vpk_context("tf2_misc_dir.vpk", 4833327)
    # print(text)
    # patch_vpk_file("tf2_misc_dir.vpk")
    # display_vpk_structure("tf2_misc_dir.vpk.modified", "materials/effects/")
    # search_vmts()
    #
    # comparator = VMTComparator("C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf/tf2_misc_dir.vpk", "uwu.vpk")
    # results = comparator.compare_vmts()
    # for filename, comparisons in results.items():
    #     print_vmt_comparison(filename, comparisons)

    local_dir = "uwu"
    vpk_path = "tf2_misc_dir.vpk"
    vpk = VPKParser(vpk_path)
    vpk.parse_directory()
    modified_files = process_vmt_comments(vpk)
    for path, num_comments in modified_files.items():
        print(f"Modified {path}: replaced {num_comments} comments with whitespace bytes")

    stats = count_whitespace(vpk)

    print(f"\nTotal whitespace bytes across all files: {stats['__summary__']['total_whitespace_bytes']:,}")
    print(f"Total VMT files analyzed: {stats['__summary__']['total_files']}")

    print("\nTop 10 files by whitespace percentage:")
    sorted_files = sorted(
        [(k, v) for k, v in stats.items() if k != '__summary__'],
        key=lambda x: x[1]['whitespace_percentage'],
        reverse=True
    )[:10]

    for path, data in sorted_files:
        print(f"\n{path}")
        print(f"Whitespace: {data['whitespace_bytes']:,} bytes ({data['whitespace_percentage']}%)")
        print(f"Total size: {data['total_size']:,} bytes")

    # comparator = VMTDirComparator(local_dir, vpk_path)
    # results = comparator.compare_files()
    # print_comparison_results(results)
if __name__ == "__main__":
    main()
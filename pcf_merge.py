import os
from typing import Dict, Tuple, Optional, Set
from pcfcodec import PCFCodec, AttributeType, PCFElement
import copy

def read_binary_file(filename: str) -> bytes:
    """Read entire file as bytes."""
    with open(filename, 'rb') as f:
        return f.read()

def get_pcf_signature(pcf_path: str) -> bytes:
    """Extract a unique binary signature from PCF file."""
    pcf_data = read_binary_file(pcf_path)
    header_end = pcf_data.index(b'\x00')
    header = pcf_data[:header_end]
    signature_chunk_size = 256
    signature = pcf_data[header_end:header_end + signature_chunk_size]
    return header + signature

def extract_pcf_from_vpk(vpk_data: bytes, offset: int, size: int) -> bytes:
    """Extract PCF data from VPK."""
    return vpk_data[offset:offset + size]

def selective_merge_pcf(original_pcf: PCFCodec, new_pcf: PCFCodec) -> PCFCodec:
    """
    Selectively merge attributes from new PCF into original PCF,
    preserving original structure and extra attributes.
    """
    # Create a deep copy of original to modify
    merged = copy.deepcopy(original_pcf)
    changes_made = []

    # Track which elements we've processed
    processed_elements = set()

    # Process each element in the new PCF
    for new_idx, new_element in enumerate(new_pcf.pcf.elements):
        # Try to find matching element in original
        for orig_idx, orig_element in enumerate(merged.pcf.elements):
            if (orig_idx not in processed_elements and 
                orig_element.type_name_index == new_element.type_name_index and
                orig_element.element_name == new_element.element_name):
                
                # Found matching element, update its attributes
                for attr_name, (attr_type, attr_value) in new_element.attributes.items():
                    if attr_name in orig_element.attributes:
                        # Only update if values are different
                        orig_value = orig_element.attributes[attr_name][1]
                        if orig_value != attr_value:
                            changes_made.append({
                                'element': orig_idx,
                                'attribute': attr_name.decode('ascii', errors='replace'),
                                'old': orig_value,
                                'new': attr_value
                            })
                            orig_element.attributes[attr_name] = (attr_type, attr_value)
                
                processed_elements.add(orig_idx)
                break

    # Report changes
    if changes_made:
        print("\nChanges made:")
        for change in changes_made:
            print(f"\nElement {change['element']}: {change['attribute']}")
            print(f"  Old: {change['old']}")
            print(f"  New: {change['new']}")
    else:
        print("\nNo changes were necessary")

    return merged

def merge_pcf_into_vpk(vpk_path: str, pattern_pcf_path: str, replacement_pcf_path: str, offset_hint: int = None) -> bool:
    """
    Selectively merge replacement PCF into VPK at location matching pattern PCF.
    """
    try:
        # Read files
        pattern_data = read_binary_file(pattern_pcf_path)
        pattern_signature = get_pcf_signature(pattern_pcf_path)
        vpk_data = read_binary_file(vpk_path)

        # Find pattern in VPK
        print(f"\nSearching for pattern PCF in VPK...")
        try:
            if offset_hint is not None:
                search_window = 1000
                start_pos = max(0, offset_hint - search_window)
                end_pos = min(len(vpk_data), offset_hint + search_window)
                chunk = vpk_data[start_pos:end_pos]
                relative_offset = chunk.index(pattern_signature)
                offset = start_pos + relative_offset
            else:
                offset = vpk_data.index(pattern_signature)
            
            print(f"Found PCF at offset: {offset} (0x{offset:X})")
        except ValueError:
            print("Error: Could not find pattern PCF in VPK")
            return False

        # Extract PCF from VPK
        vpk_pcf_data = extract_pcf_from_vpk(vpk_data, offset, len(pattern_data))
        
        # Create temporary file for VPK's PCF
        temp_vpk_pcf = "temp_vpk_pcf.pcf"
        with open(temp_vpk_pcf, 'wb') as f:
            f.write(vpk_pcf_data)

        # Load PCFs
        original_pcf = PCFCodec()
        original_pcf.decode(temp_vpk_pcf)

        replacement_pcf = PCFCodec()
        replacement_pcf.decode(replacement_pcf_path)

        # Perform selective merge
        print("\nPerforming selective merge...")
        merged_pcf = selective_merge_pcf(original_pcf, replacement_pcf)

        # Save merged PCF temporarily
        temp_merged = "temp_merged.pcf"
        merged_pcf.encode(temp_merged)

        # Read merged data
        with open(temp_merged, 'rb') as f:
            merged_data = f.read()

        # Verify size
        if len(merged_data) > len(pattern_data):
            print(f"\nError: Merged PCF ({len(merged_data)} bytes) is larger than original space ({len(pattern_data)} bytes)")
            return False

        # Write back to VPK
        print("\nWriting merged PCF back to VPK...")
        with open(vpk_path, 'rb+') as f:
            f.seek(offset)
            f.write(merged_data)
            # Pad with original data if needed
            if len(merged_data) < len(pattern_data):
                padding = vpk_pcf_data[len(merged_data):]
                f.write(padding)

        # Clean up temp files
        for temp_file in [temp_vpk_pcf, temp_merged]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        print("\nMerge completed successfully")
        return True

    except Exception as e:
        print(f"Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Selectively merge PCF file into VPK')
    parser.add_argument('vpk_path', help='Path to target VPK file')
    parser.add_argument('pattern_pcf', help='Path to PCF file to use as search pattern')
    parser.add_argument('replacement_pcf', help='Path to PCF file with desired changes')
    parser.add_argument('--offset', type=int, help='Offset hint to speed up search (optional)')
    parser.add_argument('--backup', action='store_true', help='Create backup of VPK before modifying')
    
    args = parser.parse_args()
    
    if args.backup:
        backup_path = args.vpk_path + '.backup'
        print(f"Creating backup at: {backup_path}")
        with open(args.vpk_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
    
    success = merge_pcf_into_vpk(
        args.vpk_path,
        args.pattern_pcf,
        args.replacement_pcf,
        args.offset
    )
    
    if success:
        print("\nSelective merge completed successfully!")
    else:
        print("\nMerge failed!")
        if args.backup:
            print("You can restore from the backup file if needed")

if __name__ == "__main__":
    main()
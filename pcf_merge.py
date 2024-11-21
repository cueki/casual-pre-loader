from dataclasses import dataclass
import os
from typing import Dict, Tuple, Optional, Set, List
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

@dataclass
class ReclaimableSpace:
    """Information about space that can be reclaimed."""
    index: int
    size: int
    type: str
    risk: str
    data: bytes  # Store the original data

def find_reclaimable_space(pcf: PCFCodec) -> List[ReclaimableSpace]:
    """Identify spaces that can be reclaimed in the PCF file."""
    reclaimable = []
    
    # Find unused strings
    used_strings: Set[int] = set()
    
    # Track string usage
    for element in pcf.pcf.elements:
        used_strings.add(element.type_name_index)
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Track attribute names
            if isinstance(attr_name, bytes):
                try:
                    idx = pcf.pcf.string_dictionary.index(attr_name)
                    used_strings.add(idx)
                except ValueError:
                    pass
            
            # Track string values
            if attr_type == AttributeType.STRING:
                if isinstance(attr_value, bytes):
                    try:
                        idx = pcf.pcf.string_dictionary.index(attr_value)
                        used_strings.add(idx)
                    except ValueError:
                        pass
    
    # Add unused strings to reclaimable space
    for idx, string in enumerate(pcf.pcf.string_dictionary):
        if idx not in used_strings:
            original_data = string if isinstance(string, bytes) else string.encode('ascii')
            size = len(original_data) + 1  # Include null terminator
            reclaimable.append(ReclaimableSpace(
                index=idx,
                size=size,
                type='string',
                risk='safe',
                data=original_data
            ))
    
    return reclaimable

def remove_unused_strings(pcf: PCFCodec, unused_indices: Set[int]) -> None:
    """Remove unused strings from the dictionary and update indices."""
    # Create new string dictionary without unused strings
    new_dictionary = []
    index_map = {}  # Maps old indices to new indices
    
    for old_idx, string in enumerate(pcf.pcf.string_dictionary):
        if old_idx not in unused_indices:
            index_map[old_idx] = len(new_dictionary)
            new_dictionary.append(string)
    
    # Update all references to string indices
    for element in pcf.pcf.elements:
        # Update type name index
        if element.type_name_index in index_map:
            element.type_name_index = index_map[element.type_name_index]
            
        # Update attribute name indices if needed
        new_attributes = {}
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            if isinstance(attr_name, bytes):
                try:
                    old_idx = pcf.pcf.string_dictionary.index(attr_name)
                    if old_idx in index_map:
                        new_attr_name = pcf.pcf.string_dictionary[old_idx]
                    else:
                        new_attr_name = attr_name
                except ValueError:
                    new_attr_name = attr_name
            else:
                new_attr_name = attr_name
            new_attributes[new_attr_name] = (attr_type, attr_value)
        element.attributes = new_attributes
    
    # Update the string dictionary
    pcf.pcf.string_dictionary = new_dictionary

def pad_file_to_size(filename: str, target_size: int) -> bool:
    """Pad a file with null bytes to reach the target size."""
    try:
        current_size = os.path.getsize(filename)
        if current_size > target_size:
            print(f"Error: Current size {current_size} exceeds target size {target_size}")
            return False
            
        if current_size < target_size:
            padding_needed = target_size - current_size
            print(f"\nPadding file with {padding_needed} null bytes to maintain original size")
            
            with open(filename, 'ab') as f:
                f.write(b'\x00' * padding_needed)
                
            final_size = os.path.getsize(filename)
            if final_size != target_size:
                print(f"Error: Final size {final_size} doesn't match target {target_size}")
                return False
                
        return True
        
    except Exception as e:
        print(f"Error padding file: {e}")
        return False

def selective_merge_pcf(original_pcf: PCFCodec, new_pcf: PCFCodec, optimize_strings: bool = True) -> Tuple[PCFCodec, List[dict]]:
    """
    Selectively merge attributes from new PCF into original PCF,
    preserving original structure and extra attributes.
    Now with optional string optimization.
    
    Returns:
        Tuple of (merged PCFCodec, list of changes made)
    """
    # Create a deep copy of original to modify
    merged = copy.deepcopy(original_pcf)
    changes_made = []

    # Track which elements we've processed
    processed_elements = set()
    
    # Find reclaimable space if optimization is enabled
    if optimize_strings:
        available_space = find_reclaimable_space(merged)
        if available_space:
            print("\nFound reclaimable space:")
            total_space = sum(space.size for space in available_space)
            print(f"Total reclaimable bytes: {total_space}")
            
            # Collect indices of unused strings
            unused_string_indices = {space.index for space in available_space if space.type == 'string'}
            if unused_string_indices:
                print("Removing unused strings to optimize file size...")
                remove_unused_strings(merged, unused_string_indices)

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
                                'attribute': attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name,
                                'old': orig_value,
                                'new': attr_value
                            })
                            orig_element.attributes[attr_name] = (attr_type, attr_value)
                
                processed_elements.add(orig_idx)
                break

    return merged, changes_made

def merge_pcf_into_vpk(
    vpk_path: str, 
    pattern_pcf_path: str, 
    replacement_pcf_path: str, 
    offset_hint: Optional[int] = None,
    optimize_strings: bool = True
) -> bool:
    """
    Selectively merge replacement PCF into VPK at location matching pattern PCF.
    Now with string optimization support.
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

        # Perform selective merge with optimization
        print("\nPerforming selective merge...")
        merged_pcf, changes = selective_merge_pcf(original_pcf, replacement_pcf, optimize_strings)

        # Report changes
        if changes:
            print("\nChanges made:")
            for change in changes:
                print(f"\nElement {change['element']}: {change['attribute']}")
                print(f"  Old: {change['old']}")
                print(f"  New: {change['new']}")
        else:
            print("\nNo changes were necessary")

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
    
    parser = argparse.ArgumentParser(description='Selectively merge PCF file into VPK with optimization')
    parser.add_argument('vpk_path', help='Path to target VPK file')
    parser.add_argument('pattern_pcf', help='Path to PCF file to use as search pattern')
    parser.add_argument('replacement_pcf', help='Path to PCF file with desired changes')
    parser.add_argument('--offset', type=int, help='Offset hint to speed up search (optional)')
    parser.add_argument('--no-optimize', action='store_true', help='Disable string optimization')
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
        args.offset,
        not args.no_optimize
    )
    
    if success:
        print("\nSelective merge completed successfully!")
    else:
        print("\nMerge failed!")
        if args.backup:
            print("You can restore from the backup file if needed")

if __name__ == "__main__":
    main()
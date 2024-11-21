from pcfcodec import PCFCodec, AttributeType
import copy
import os
from typing import Dict, List, Optional, Union, Tuple, Set
from dataclasses import dataclass

@dataclass
class ReclaimableSpace:
    """Information about space that can be reclaimed."""
    index: int
    size: int
    type: str
    risk: str
    data: bytes  # Store the original data

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
                # Write null bytes for padding
                f.write(b'\x00' * padding_needed)
                
            # Verify final size
            final_size = os.path.getsize(filename)
            if final_size != target_size:
                print(f"Error: Final size {final_size} doesn't match target {target_size}")
                return False
                
        return True
        
    except Exception as e:
        print(f"Error padding file: {e}")
        return False

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
            # Store the original string data for later removal
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
                        # Get the string from the old dictionary and update
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

def modify_pcf_filepath_with_reclamation(
    input_path: str, 
    output_path: str, 
    path_mappings: dict,
    element_ids: Optional[List[int]] = None,
    allow_reclamation: bool = True,
    dry_run: bool = False
) -> bool:
    """Modified version that maintains exact original file size."""
    try:
        # Get original file size
        original_size = os.path.getsize(input_path)
        input_pcf = PCFCodec()
        input_pcf.decode(input_path)
        
        # Create working copy
        modified_pcf = copy.deepcopy(input_pcf)
        changes_made = []
        
        # Find reclaimable space
        available_space = []
        if allow_reclamation:
            available_space = find_reclaimable_space(modified_pcf)
            
            if available_space:
                print("\nFound reclaimable space:")
                total_space = sum(space.size for space in available_space)
                print(f"Total reclaimable bytes: {total_space}")
                for space in available_space:
                    if isinstance(space.data, bytes):
                        data_preview = space.data.decode('ascii', errors='replace')
                    else:
                        data_preview = str(space.data)
                    print(f"• {space.size} bytes at {space.type} index {space.index} (risk: {space.risk})")
                    print(f"  Unused string: \"{data_preview}\"")
        
        # Convert path mappings to bytes
        byte_mappings = {
            old_path.encode('ascii'): new_path.encode('ascii')
            for old_path, new_path in path_mappings.items()
        }
        
        # Calculate space needed
        total_extra_space_needed = 0
        total_space_available = sum(space.size for space in available_space)
        
        # First pass: Calculate space needed
        for elem_idx, element in enumerate(modified_pcf.pcf.elements):
            if element_ids is not None and elem_idx not in element_ids:
                continue
                
            type_name = modified_pcf.pcf.string_dictionary[element.type_name_index]
            print(f"\nChecking element {elem_idx}: Type={type_name.decode('ascii', errors='replace')}")
            
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                if attr_type == AttributeType.STRING:
                    current_path = attr_value if isinstance(attr_value, bytes) else attr_value.encode('ascii')
                    attr_name_str = attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name
                    
                    print(f"  Checking attribute: {attr_name_str}")
                    print(f"    Current value: {current_path.decode('ascii', errors='replace')}")
                    
                    for old_path_bytes, new_path_bytes in byte_mappings.items():
                        if old_path_bytes in current_path:
                            size_difference = len(new_path_bytes) - len(old_path_bytes)
                            if size_difference > 0:
                                total_extra_space_needed += size_difference
        
        print(f"\nExtra space needed: {total_extra_space_needed} bytes")
        print(f"Space available through reclamation: {total_space_available} bytes")
        
        if total_extra_space_needed > total_space_available:
            print("\nError: Not enough reclaimable space available")
            return False
        
        # Second pass: Apply modifications
        space_used = 0
        unused_string_indices = set()
        
        # Mark strings for removal
        for space in available_space:
            if space.type == 'string':
                unused_string_indices.add(space.index)
        
        # Apply path modifications
        for elem_idx, element in enumerate(modified_pcf.pcf.elements):
            if element_ids is not None and elem_idx not in element_ids:
                continue
                
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                if attr_type == AttributeType.STRING:
                    current_path = attr_value if isinstance(attr_value, bytes) else attr_value.encode('ascii')
                    
                    for old_path_bytes, new_path_bytes in byte_mappings.items():
                        if old_path_bytes in current_path:
                            new_value = current_path.replace(old_path_bytes, new_path_bytes)
                            size_difference = len(new_value) - len(current_path)
                            
                            if size_difference > 0:
                                space_used += size_difference
                            
                            changes_made.append({
                                'element': elem_idx,
                                'attribute': attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name,
                                'old': current_path.decode('ascii', errors='replace'),
                                'new': new_value.decode('ascii', errors='replace'),
                                'space_needed': size_difference
                            })
                            
                            element.attributes[attr_name] = (attr_type, new_value)
        
        # Remove unused strings and update indices
        if unused_string_indices:
            remove_unused_strings(modified_pcf, unused_string_indices)
        
        # Report changes
        if changes_made:
            print("\nPath modifications to make:")
            for change in changes_made:
                print(f"\nElement {change['element']}")
                print(f"  Attribute: {change['attribute']}")
                print(f"  Old: {change['old']}")
                print(f"  New: {change['new']}")
                if change['space_needed'] > 0:
                    print(f"  Extra space needed: {change['space_needed']} bytes")
            
            print(f"\nTotal extra space needed: {total_extra_space_needed} bytes")
            print(f"Space reclaimed and used: {space_used} bytes")
        
        if dry_run:
            return True
        
        # Save modified PCF
        modified_pcf.encode(output_path)
        if not dry_run:
            modified_size = os.path.getsize(output_path)
            print(f"\nFile size check:")
            print(f"Original: {original_size} bytes")
            print(f"Modified: {modified_size} bytes")
            print(f"Difference: {modified_size - original_size} bytes")
            
            if modified_size > original_size:
                print("\nError: Modified file is larger than original!")
                os.remove(output_path)
                return False
            
            if modified_size < original_size:
                if not pad_file_to_size(output_path, original_size):
                    print("Error: Failed to pad file to original size")
                    os.remove(output_path)
                    return False
                    
                final_size = os.path.getsize(output_path)
                print(f"Final size after padding: {final_size} bytes")
                if final_size != original_size:
                    print("Error: Final size doesn't match original")
                    os.remove(output_path)
                    return False
            
        return True
          
    except Exception as e:
        print(f"Error during modification: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Modify PCF filepaths utilizing reclaimable space')
    parser.add_argument('input_pcf', help='Path to input PCF file')
    parser.add_argument('output_pcf', help='Path to save modified PCF file')
    parser.add_argument('--mapping', action='append', nargs=2, metavar=('OLD', 'NEW'),
                       help='Path mapping in format: OLD_PATH NEW_PATH')
    parser.add_argument('--element', type=int, action='append',
                       help='Element ID to modify (can be specified multiple times)')
    parser.add_argument('--no-reclamation', action='store_true',
                       help='Disable use of reclaimable space')
    parser.add_argument('--dry-run', action='store_true',
                       help='Check if modifications are possible without writing')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup of input PCF before modifying')
    
    args = parser.parse_args()
    
    if not args.mapping:
        parser.error("At least one --mapping OLD_PATH NEW_PATH is required")
    
    path_mappings = dict(args.mapping)
    
    if args.backup and os.path.exists(args.input_pcf):
        backup_path = args.input_pcf + '.backup'
        print(f"Creating backup at: {backup_path}")
        with open(args.input_pcf, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
    
    success = modify_pcf_filepath_with_reclamation(
        args.input_pcf,
        args.output_pcf,
        path_mappings,
        args.element,
        not args.no_reclamation,
        args.dry_run
    )
    
    if success:
        if args.dry_run:
            print("\nDry run successful - modifications are possible!")
        else:
            print("\nPath modifications completed successfully!")
    else:
        print("\nModification failed!")
        if args.backup:
            print("You can restore from the backup file if needed")
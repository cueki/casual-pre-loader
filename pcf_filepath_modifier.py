from pcfcodec import PCFCodec, AttributeType
import copy
import os
from typing import Dict, List, Optional, Union, Tuple

def pad_path(path: bytes, target_length: int) -> bytes:
    """Pad a path with spaces to reach target length while maintaining extension."""
    if len(path) >= target_length:
        return path
        
    # Find the last occurrence of a dot for the extension
    try:
        dot_index = path.rindex(b'.')
        base = path[:dot_index]
        ext = path[dot_index:]
        
        # Calculate padding needed
        padding_size = target_length - len(path)
        
        # Insert padding before the extension
        return base  + ext + b' ' * padding_size
        
    except ValueError:
        # No extension found, just pad at the end
        return path + b' ' * (target_length - len(path))

def modify_pcf_filepath(
    input_path: str, 
    output_path: str, 
    path_mappings: dict, 
    element_ids: Optional[List[int]] = None,
    allow_padding: bool = True,
    dry_run: bool = False
) -> bool:
    """
    Modify filepaths in a PCF file while maintaining the exact same file size.
    
    Args:
        input_path: Path to input PCF file
        output_path: Path for modified PCF file
        path_mappings: Dictionary of old_path: new_path mappings (strings)
        element_ids: Optional list of element IDs to modify. If None, checks all elements.
        allow_padding: If True, allows padding shorter paths with spaces
        dry_run: If True, only check if modifications are possible without writing
    
    Returns:
        bool: True if modification was successful or possible (in dry_run mode)
    """
    try:
        # Load input PCF
        input_pcf = PCFCodec()
        input_pcf.decode(input_path)
        
        # Create working copy
        modified_pcf = copy.deepcopy(input_pcf)
        changes_made = []
        
        # Convert path mappings to bytes
        byte_mappings = {
            old_path.encode('ascii'): new_path.encode('ascii')
            for old_path, new_path in path_mappings.items()
        }
        
        # Track string replacements to ensure consistent length
        for elem_idx, element in enumerate(modified_pcf.pcf.elements):
            # Skip if element_ids is specified and this element isn't in the list
            if element_ids is not None and elem_idx not in element_ids:
                continue
                
            # Print element info for debugging
            type_name = modified_pcf.pcf.string_dictionary[element.type_name_index]
            elem_name = element.element_name
            print(f"\nChecking element {elem_idx}: Type={type_name.decode('ascii', errors='replace')}, "
                  f"Name={elem_name.decode('ascii', errors='replace') if isinstance(elem_name, bytes) else elem_name}")
            
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                # Check if this is a string attribute that might contain a path
                if attr_type == AttributeType.STRING:
                    # Ensure we're working with bytes
                    current_path = attr_value if isinstance(attr_value, bytes) else attr_value.encode('ascii')
                    
                    # Print attribute info for debugging
                    print(f"  Checking attribute: {attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name}")
                    print(f"    Current value: {current_path.decode('ascii', errors='replace')}")
                    
                    # Check if this path needs replacement
                    for old_path_bytes, new_path_bytes in byte_mappings.items():
                        if old_path_bytes in current_path:
                            new_value = current_path.replace(old_path_bytes, new_path_bytes)
                            
                            # Handle size differences with padding if allowed
                            if len(new_value) < len(current_path) and allow_padding:
                                new_value = pad_path(new_value, len(current_path))
                            elif len(new_value) != len(current_path):
                                print(f"Error: New path length ({len(new_value)}) doesn't match original ({len(current_path)})")
                                print("Use --allow-padding to enable automatic space padding")
                                return False
                            
                            # Store the change for reporting
                            changes_made.append({
                                'element': elem_idx,
                                'type': type_name.decode('ascii', errors='replace'),
                                'name': elem_name.decode('ascii', errors='replace') if isinstance(elem_name, bytes) else elem_name,
                                'attribute': attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name,
                                'old': current_path.decode('ascii', errors='replace'),
                                'new': new_value.decode('ascii', errors='replace'),
                                'padded': len(new_value) > len(new_path_bytes)
                            })
                            
                            # Update the attribute
                            element.attributes[attr_name] = (attr_type, new_value)
        
        # Report changes
        if changes_made:
            print("\nPath modifications to make:")
            for change in changes_made:
                print(f"\nElement {change['element']} ({change['type']}: {change['name']})")
                print(f"  Attribute: {change['attribute']}")
                print(f"  Old: {change['old']}")
                print(f"  New: {change['new']}")
                if change['padded']:
                    print("  (Padded with spaces to maintain size)")
        else:
            print("\nNo path modifications needed")
            return True
        
        if dry_run:
            return True
            
        # Save modified PCF
        modified_pcf.encode(output_path)
        
        # Verify file sizes match
        original_size = os.path.getsize(input_path)
        modified_size = os.path.getsize(output_path)
        
        if original_size != modified_size:
            print(f"Error: Size mismatch - Original: {original_size}, Modified: {modified_size}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
        print(f"\nSuccessfully saved modified PCF to: {output_path}")
        print(f"File size maintained at {original_size} bytes")
        return True
        
    except Exception as e:
        print(f"Error during modification: {e}")
        import traceback
        traceback.print_exc()
        return False

def list_pcf_elements(input_path: str) -> None:
    """List all elements in a PCF file with their IDs and paths."""
    try:
        input_pcf = PCFCodec()
        input_pcf.decode(input_path)
        
        print(f"\nElements in {input_path}:")
        print("-" * 60)
        
        for elem_idx, element in enumerate(input_pcf.pcf.elements):
            type_name = input_pcf.pcf.string_dictionary[element.type_name_index]
            elem_name = element.element_name
            
            print(f"\nElement {elem_idx}:")
            print(f"  Type: {type_name.decode('ascii', errors='replace')}")
            print(f"  Name: {elem_name.decode('ascii', errors='replace') if isinstance(elem_name, bytes) else elem_name}")
            
            # Print string attributes that might be paths
            for attr_name, (attr_type, attr_value) in element.attributes.items():
                if attr_type == AttributeType.STRING:
                    attr_name_str = attr_name.decode('ascii', errors='replace') if isinstance(attr_name, bytes) else attr_name
                    attr_value_str = attr_value.decode('ascii', errors='replace') if isinstance(attr_value, bytes) else attr_value
                    print(f"    {attr_name_str}: {attr_value_str}")
                    
    except Exception as e:
        print(f"Error listing elements: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Modify PCF filepaths while maintaining file size')
    parser.add_argument('input_pcf', help='Path to input PCF file')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List elements command
    list_parser = subparsers.add_parser('list', help='List elements in PCF file')
    
    # Modify elements command
    modify_parser = subparsers.add_parser('modify', help='Modify filepaths in PCF file')
    modify_parser.add_argument('output_pcf', help='Path to save modified PCF file')
    modify_parser.add_argument('--mapping', action='append', nargs=2, metavar=('OLD', 'NEW'),
                           help='Path mapping in the format: OLD_PATH NEW_PATH')
    modify_parser.add_argument('--element', type=int, action='append',
                           help='Element ID to modify (can be specified multiple times)')
    modify_parser.add_argument('--no-padding', action='store_true',
                           help='Disable automatic space padding of paths')
    modify_parser.add_argument('--dry-run', action='store_true', 
                           help='Check if modifications are possible without writing')
    modify_parser.add_argument('--backup', action='store_true',
                           help='Create backup of input PCF before modifying')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_pcf_elements(args.input_pcf)
    
    elif args.command == 'modify':
        if not args.mapping:
            parser.error("At least one --mapping OLD_PATH NEW_PATH is required")
        
        path_mappings = dict(args.mapping)
        
        if args.backup and os.path.exists(args.input_pcf):
            backup_path = args.input_pcf + '.backup'
            print(f"Creating backup at: {backup_path}")
            with open(args.input_pcf, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
        
        success = modify_pcf_filepath(
            args.input_pcf,
            args.output_pcf,
            path_mappings,
            args.element,
            not args.no_padding,
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
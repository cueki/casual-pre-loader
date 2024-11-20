import os
from typing import Dict, Tuple, List, Any
from pcfcodec import PCFCodec, AttributeType, PCFElement
import copy
import argparse

def get_color_type(color_value: Tuple[int, int, int, int]) -> str:
    """
    Determine if a color is red-dominant or blue-dominant based on RGB values.
    
    Args:
        color_value: RGBA tuple (r,g,b,a)
        
    Returns:
        str: 'red' if red channel > blue channel, 'blue' if blue channel > red channel, None if equal
    """
    r, g, b, a = color_value
    if r > b:
        return 'red'
    elif b > r:
        return 'blue'
    return None

def transform_color_value(value: Any, red_color: Tuple[int, int, int], blue_color: Tuple[int, int, int]) -> Any:
    """
    Transform a color value based on its red/blue dominance.
    
    Args:
        value: Original color value
        red_color: Target color for red-dominant colors
        blue_color: Target color for blue-dominant colors
    
    Returns:
        Transformed color value or original value if not applicable
    """
    if isinstance(value, tuple) and len(value) == 4:  # RGBA tuple
        color_type = get_color_type(value)
        if color_type:
            target_color = red_color if color_type == 'red' else blue_color
            return target_color + (value[3],)  # Preserve original alpha
    return value

def transform_pcf_colors(pcf: PCFCodec, red_color: Tuple[int, int, int], blue_color: Tuple[int, int, int]) -> PCFCodec:
    """
    Transform colors in a PCF file based on their RGB values.
    
    Args:
        pcf: Original PCFCodec object
        red_color: Target color for red-dominant colors as RGB tuple
        blue_color: Target color for blue-dominant colors as RGB tuple
    
    Returns:
        New PCFCodec object with transformed colors
    """
    # Create a deep copy to modify
    transformed = copy.deepcopy(pcf)
    changes_made = []
    
    # Color-related attribute names to look for
    color_attributes = {'color', 'color1', 'color2', 'color_fade'}
    
    # Process each element
    for elem_idx, element in enumerate(transformed.pcf.elements):
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Decode attribute name if it's bytes
            attr_name_str = attr_name.decode('ascii') if isinstance(attr_name, bytes) else attr_name
            
            # Check if this is a color attribute
            if attr_name_str.lower() in color_attributes:
                # Skip if not a valid color value
                if not (isinstance(attr_value, tuple) and len(attr_value) == 4):
                    continue
                    
                color_type = get_color_type(attr_value)
                if not color_type:
                    continue
                
                original_value = attr_value
                new_value = transform_color_value(
                    attr_value,
                    red_color,
                    blue_color
                )
                
                if new_value != original_value:
                    element.attributes[attr_name] = (attr_type, new_value)
                    changes_made.append({
                        'element': elem_idx,
                        'attribute': attr_name_str,
                        'old': original_value,
                        'new': new_value,
                        'color_type': color_type,
                        'element_type': transformed.pcf.string_dictionary[element.type_name_index].decode('ascii') 
                            if isinstance(transformed.pcf.string_dictionary[element.type_name_index], bytes) 
                            else transformed.pcf.string_dictionary[element.type_name_index]
                    })
    
    # Report changes with RGB values
    if changes_made:
        print("\nColor transformations made:")
        for change in changes_made:
            old_r, old_g, old_b, old_a = change['old']
            new_r, new_g, new_b, new_a = change['new']
            print(f"\nElement {change['element']} ({change['element_type']}) - {change['color_type'].upper()}")
            print(f"  Attribute: {change['attribute']}")
            print(f"  Old: R:{old_r} G:{old_g} B:{old_b} A:{old_a}")
            print(f"  New: R:{new_r} G:{new_g} B:{new_b} A:{new_a}")
            
        # Summary by color type
        red_changes = sum(1 for c in changes_made if c['color_type'] == 'red')
        blue_changes = sum(1 for c in changes_made if c['color_type'] == 'blue')
        print(f"\nSummary:")
        print(f"  Red-dominant colors modified: {red_changes}")
        print(f"  Blue-dominant colors modified: {blue_changes}")
    else:
        print("\nNo color transformations were necessary")
    
    return transformed

def transform_pcf_file(input_path: str, output_path: str, red_color: Tuple[int, int, int], blue_color: Tuple[int, int, int]) -> bool:
    """
    Transform colors in a PCF file and save to a new file.
    
    Args:
        input_path: Path to input PCF file
        output_path: Path to save transformed PCF file
        red_color: Target color for red-dominant colors as RGB tuple
        blue_color: Target color for blue-dominant colors as RGB tuple
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load input PCF
        input_pcf = PCFCodec()
        input_pcf.decode(input_path)
        
        # Transform colors
        print(f"\nTransforming colors:")
        print(f"  Red-dominant colors -> RGB{red_color}")
        print(f"  Blue-dominant colors -> RGB{blue_color}")
        transformed_pcf = transform_pcf_colors(input_pcf, red_color, blue_color)
        
        # Save transformed PCF
        transformed_pcf.encode(output_path)
        print(f"\nTransformed PCF saved to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        import traceback
        traceback.print_exc()
        return False

def parse_rgb(rgb_str: str) -> Tuple[int, int, int]:
    """Parse RGB string in format 'r,g,b' into tuple."""
    try:
        r, g, b = map(int, rgb_str.split(','))
        if not all(0 <= x <= 255 for x in (r, g, b)):
            raise ValueError("RGB values must be between 0 and 255")
        return (r, g, b)
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid RGB format. Use 'r,g,b' with values 0-255: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Transform colors in PCF file based on RGB values. '
        'Colors with R>B are considered red, colors with B>R are considered blue.'
    )
    parser.add_argument('input_pcf', help='Path to input PCF file')
    parser.add_argument('output_pcf', help='Path to save transformed PCF file')
    parser.add_argument('red_color', type=parse_rgb, 
                       help='Target color for red-dominant colors (R>B) in format "r,g,b"')
    parser.add_argument('blue_color', type=parse_rgb,
                       help='Target color for blue-dominant colors (B>R) in format "r,g,b"')
    parser.add_argument('--backup', action='store_true', help='Create backup of input PCF before modifying')
    
    args = parser.parse_args()
    
    if args.backup and os.path.exists(args.input_pcf):
        backup_path = args.input_pcf + '.backup'
        print(f"Creating backup at: {backup_path}")
        with open(args.input_pcf, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
    
    success = transform_pcf_file(args.input_pcf, args.output_pcf, args.red_color, args.blue_color)
    
    if success:
        print("\nColor transformation completed successfully!")
    else:
        print("\nTransformation failed!")
        if args.backup:
            print("You can restore from the backup file if needed")

if __name__ == "__main__":
    main()
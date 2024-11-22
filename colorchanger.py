import os
from typing import Dict, Tuple, List, Any
from pcfcodec import PCFCodec, AttributeType, PCFElement
import copy
import argparse

def should_preserve_color(rgba: Tuple[int, int, int, int]) -> bool:
    """
    Determine if a color should be preserved (pure white or pure black/transparent).
    
    Args:
        rgba: RGBA tuple to check
        
    Returns:
        bool: True if color should be preserved, False if it should be transformed
    """
    # Preserve pure white
    if rgba == (255, 255, 255, 255):
        return False
    
    # Preserve pure black or fully transparent
    if rgba == (0, 0, 0, 0):
        return False
        
    return False

def rgb_to_target_color(original_rgb: Tuple[int, int, int], base_color: Tuple[int, int, int]) -> tuple[int, ...]:
    """
    Transform RGB values based on target base color while preserving relative intensities.
    
    Args:
        original_rgb: Original RGB tuple
        base_color: Target base color RGB tuple
    
    Returns:
        Transformed RGB tuple
    """
    # Find the dominant channel in the original color
    max_channel = max(original_rgb)
    if max_channel == 0:
        return original_rgb  # Can't transform a black color
    
    # Find the dominant channel in the target base color
    target_max_channel = max(base_color)
    target_max_index = base_color.index(target_max_channel)
    
    # Calculate scaling factors for each channel
    scaling = []
    for i in range(3):
        if base_color[i] == 0:
            scaling.append(0)
        else:
            scaling.append(base_color[i] / target_max_channel)
    
    # Transform the color while preserving relative intensity
    transformed = [0, 0, 0]
    for i in range(3):
        transformed[i] = min(255, int(original_rgb[i] * scaling[i]))
    
    return tuple(transformed)

def transform_color_value(value: Any, base_color: Tuple[int, int, int]) -> Any:
    """Transform a color value if it's in the expected format and not preserved."""
    if isinstance(value, tuple) and len(value) == 4:  # RGBA tuple
        # Check if this color should be preserved
        if should_preserve_color(value):
            return value
            
        rgb = value[:3]
        alpha = value[3]
        new_rgb = rgb_to_target_color(rgb, base_color)
        return new_rgb + (alpha,)
    return value

def transform_pcf_colors(pcf: PCFCodec, base_color: Tuple[int, int, int]) -> PCFCodec:
    """
    Transform all color values in a PCF file based on a target base color.
    
    Args:
        pcf: Original PCFCodec object
        base_color: Target base color as RGB tuple
    
    Returns:
        New PCFCodec object with transformed colors
    """
    # Create a deep copy to modify
    transformed = copy.deepcopy(pcf)
    changes_made = []
    preserved = []
    
    # Color-related attribute names to look for
    color_attributes = {'color', 'color1', 'color2', 'color_fade'}
    
    # Process each element
    for elem_idx, element in enumerate(transformed.pcf.elements):
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Decode attribute name if it's bytes
            attr_name_str = attr_name.decode('ascii') if isinstance(attr_name, bytes) else attr_name
            
            # Check if this is a color attribute
            if attr_name_str.lower() in color_attributes:
                original_value = attr_value
                new_value = transform_color_value(attr_value, base_color)
                
                if new_value != original_value:
                    if isinstance(original_value, tuple) and len(original_value) == 4 and should_preserve_color(original_value):
                        preserved.append({
                            'element': elem_idx,
                            'attribute': attr_name_str,
                            'value': original_value
                        })
                    else:
                        element.attributes[attr_name] = (attr_type, new_value)
                        changes_made.append({
                            'element': elem_idx,
                            'attribute': attr_name_str,
                            'old': original_value,
                            'new': new_value
                        })
    
    # Report changes and preserved values
    if preserved:
        print("\nPreserved colors (pure white/black/transparent):")
        for p in preserved:
            print(f"Element {p['element']}: {p['attribute']} = {p['value']}")
            
    if changes_made:
        print("\nColor transformations made:")
        for change in changes_made:
            print(f"\nElement {change['element']}: {change['attribute']}")
            print(f"  Old: {change['old']}")
            print(f"  New: {change['new']}")
    else:
        print("\nNo color transformations were necessary")
    
    return transformed

def transform_pcf_file(input_path: str, output_path: str, base_color: Tuple[int, int, int]) -> bool:
    """
    Transform colors in a PCF file and save to a new file.
    
    Args:
        input_path: Path to input PCF file
        output_path: Path to save transformed PCF file
        base_color: Target base color as RGB tuple
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load input PCF
        input_pcf = PCFCodec()
        input_pcf.decode(input_path)
        
        # Transform colors
        print(f"\nTransforming colors using base color RGB{base_color}...")
        transformed_pcf = transform_pcf_colors(input_pcf, base_color)
        
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
    parser = argparse.ArgumentParser(description='Transform colors in PCF file based on target base color')
    parser.add_argument('input_pcf', help='Path to input PCF file')
    parser.add_argument('output_pcf', help='Path to save transformed PCF file')
    parser.add_argument('base_color', type=parse_rgb, help='Target base color in format "r,g,b" (e.g. "0,255,0" for green)')
    parser.add_argument('--backup', action='store_true', help='Create backup of input PCF before modifying')
    
    args = parser.parse_args()
    
    if args.backup and os.path.exists(args.input_pcf):
        backup_path = args.input_pcf + '.backup'
        print(f"Creating backup at: {backup_path}")
        with open(args.input_pcf, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
    
    success = transform_pcf_file(args.input_pcf, args.output_pcf, args.base_color)
    
    if success:
        print("\nColor transformation completed successfully!")
    else:
        print("\nTransformation failed!")
        if args.backup:
            print("You can restore from the backup file if needed")

if __name__ == "__main__":
    main()
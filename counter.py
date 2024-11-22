from pcfcodec import PCFCodec, AttributeType
from typing import Set, Tuple
from collections import defaultdict

def is_color_attribute(name: bytes) -> bool:
    """Check if attribute name is color-related."""
    color_prefixes = (b"color", b"Color")
    return any(name.startswith(prefix) for prefix in color_prefixes)

def scan_pcf_colors(pcf_path: str) -> None:
    """Scan PCF file for non-white color values."""
    codec = PCFCodec()
    codec.decode(pcf_path)
    
    # Store unique colors and their locations
    color_locations = defaultdict(list)
    
    # Scan all elements
    for elem_idx, element in enumerate(codec.pcf.elements):
        for attr_name, (attr_type, attr_value) in element.attributes.items():
            if is_color_attribute(attr_name):
                if isinstance(attr_value, (tuple, list)) and len(attr_value) >= 3:
                    # Convert to tuple for hashability
                    color = tuple(attr_value)
                    # Check if it's not white (ignoring alpha if present)
                    if color[:3] != (255, 255, 255):
                        location = {
                            'element': elem_idx,
                            'attribute': attr_name.decode('ascii', errors='replace'),
                            'value': color
                        }
                        # Use first 3 components (RGB) as key
                        color_key = color[:3]
                        color_locations[color_key].append(location)
    
    # Report findings
    print(f"\nFound {len(color_locations)} unique non-white colors in {pcf_path}:")
    print("-" * 60)
    
    for color, locations in sorted(color_locations.items()):
        print(f"\nColor RGB{color}:")
        for loc in locations:
            print(f"  Element {loc['element']}: {loc['attribute']}")
            if len(loc['value']) > 3:  # If has alpha
                print(f"    Full value (with alpha): {loc['value']}")
        print(f"  Used {len(locations)} times")
    
    # Summary statistics
    total_uses = sum(len(locations) for locations in color_locations.values())
    print("\nSummary:")
    print(f"Total unique colors: {len(color_locations)}")
    print(f"Total color attributes: {total_uses}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan PCF file for non-white color values')
    parser.add_argument('pcf_path', help='Path to PCF file to scan')
    
    args = parser.parse_args()
    scan_pcf_colors(args.pcf_path)

if __name__ == "__main__":
    main()

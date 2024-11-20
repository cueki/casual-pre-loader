import os

def modify_color_value(filename: str, base_position: int, search_range: int = 200, new_color: tuple = (1.0, 1.0, 1.0)) -> None:
    """
    Modify a color value in a VPK file while maintaining file size and format.
    
    Args:
        filename (str): Path to the VPK file
        base_position (int): Starting position for searching the color pattern
        search_range (int, optional): Range to search for the pattern. Defaults to 200.
        new_color (tuple, optional): New RGB color values as floats. Defaults to (1.0, 1.0, 1.0).
    """
    try:
        # Validate color input
        if len(new_color) != 3:
            raise ValueError("Color must be a tuple of 3 float values")
        
        # Convert color to string representation
        new_color_str = f".4 .8 1"
        
        # Open file in read+write binary mode
        with open(filename, 'rb+') as f:
            # Read chunk of data around the target position
            f.seek(base_position)
            data = f.read(search_range)
            
            try:
                # Convert search pattern to bytes
                search_pattern = b'$color2'
                pattern_pos = data.index(search_pattern)
                
                # Find the start and end of the color value
                start_pos = data.index(b'[', pattern_pos) + 1
                end_pos = data.index(b']', start_pos)
                
                # Calculate absolute file positions
                abs_start = base_position + start_pos
                abs_end = base_position + end_pos
                
                # Get current color value
                f.seek(abs_start)
                current_color = f.read(abs_end - abs_start).decode('ascii').strip()
                
                print(f"Found current color: {current_color}")
                print(f"Color position starts at: {abs_start}")
                
                # Prepare new color value (ensure same total length)
                original_length = abs_end - abs_start
                print(original_length)
                new_color_padded = new_color_str.ljust(original_length)
                
                # Write the new color value
                f.seek(abs_start)
                f.write(new_color_padded.encode('ascii'))
                
                print(f"Successfully modified color to: {new_color_padded}")
                
                # Verify the change (optional)
                f.seek(abs_start)
                verification = f.read(len(new_color_padded)).decode('ascii')
                print(f"Verification reads: {verification}")
                
            except ValueError as ve:
                print(f"Could not find the color pattern: {ve}")
                
    except FileNotFoundError:
        print(f"File {filename} not found")
    except Exception as e:
        print(f"Error processing file: {e}")

def main():
    # Example usage
    filename = "tf2_misc_013.vpk"
    base_position = 71825399  # Position where we start searching
    new_color = (.8, .4, 1)  # New RGB color values
    
    print(f"Attempting to modify color value in {filename}")
    print(f"Starting search from position: {base_position}")
    print(f"New color to write: {new_color}")
    print("-" * 50)
    
    modify_color_value(filename, base_position, new_color=new_color)

if __name__ == "__main__":
    main()
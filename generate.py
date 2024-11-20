def modify_parameter_value(filename: str, base_position: int, search_range: int = 200, new_value: str = "1.0") -> None:
    """
    Modify a parameter value while maintaining file size.
    """
    try:
        # Open file in read+write binary mode
        with open(filename, 'rb+') as f:
            # Read chunk of data around the target position
            f.seek(base_position)
            data = f.read(search_range)
            
            # Search for '$maxsize' and the following '"0.4"'
            try:
                # Convert search pattern to bytes
                search_pattern = b'$maxsize'
                pattern_pos = data.index(search_pattern)
                
                # Find the next quote after $maxsize
                start_pos = data.index(b'"', pattern_pos)
                end_pos = data.index(b'"', start_pos + 1)
                
                # Calculate absolute file positions
                abs_start = base_position + start_pos
                abs_end = base_position + end_pos
                
                # Get current value
                f.seek(abs_start)
                current_value = f.read(abs_end - abs_start + 1).decode('ascii')
                
                print(f"Found value: {current_value}")
                print(f"At position: {abs_start}")
                
                # Prepare new value (must be same length as original)
                original_length = end_pos - start_pos - 1
                new_padded_value = f'"{new_value.ljust(original_length)}"'
                
                # Write the new value
                f.seek(abs_start)
                f.write(new_padded_value.encode('ascii'))
                
                print(f"Successfully modified value to: {new_padded_value}")
                
                # Verify the change
                f.seek(abs_start)
                verification = f.read(len(new_padded_value)).decode('ascii')
                print(f"Verification reads: {verification}")
                
            except ValueError as ve:
                print(f"Could not find the pattern: {ve}")
                
    except FileNotFoundError:
        print(f"File {filename} not found")
    except Exception as e:
        print(f"Error processing file: {e}")

def main():
    filename = "tf2_misc_000.vpk"
    base_position = 7019103  # Position where we start searching
    new_value = "0.01"  # New value to write
    
    print(f"Attempting to modify parameter value in {filename}")
    print(f"Starting search from position: {base_position}")
    print(f"New value to write: {new_value}")
    print("-" * 50)
    
    modify_parameter_value(filename, base_position, new_value=new_value)

if __name__ == "__main__":
    main()
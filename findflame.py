def inspect_vpk_at_position(filename: str, position: int, context_size: int = 1000) -> None:
    """
    Inspect VPK file content at a specific position.
    Shows both hex dump and ASCII representation of the surrounding data.
    """
    try:
        with open(filename, 'rb') as f:
            # Seek to the start of our desired context
            f.seek(max(0, position - context_size))
            
            # Read the context around our position
            total_read_size = context_size * 2  # Read context_size before and after
            data = f.read(total_read_size)
            
            # Calculate where our target position is within the read data
            target_offset = min(context_size, position)
            
            print(f"\nInspecting {filename} at position {position}")
            print("=" * 60)
            
            # Print ASCII representation
            print("\nASCII representation:")
            print("-" * 60)
            try:
                ascii_text = data.decode('ascii', errors='replace')
                
                # Split into before, target, and after
                before = ascii_text[:target_offset]
                after = ascii_text[target_offset:]
                
                print("Before target position:")
                print(before)
                print("\n>>> Target position", position, "<<<")
                print("\nAfter target position:")
                print(after)
                
            except Exception as e:
                print(f"Error decoding ASCII: {e}")
            
            # Print hex dump with highlighting
            print("\nHex dump:")
            print("-" * 60)
            print("Offset    | 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F | ASCII")
            print("-" * 75)
            
            start_offset = max(0, position - context_size)
            
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                # Current absolute position
                current_pos = start_offset + i
                
                # Hex representation
                hex_values = ' '.join([f'{b:02X}' for b in chunk])
                hex_values = hex_values.ljust(48)  # Pad to align ASCII representation
                
                # ASCII representation
                ascii_values = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in chunk])
                
                # Highlight if this row contains our target position
                if current_pos <= position < current_pos + 16:
                    print(f"{current_pos:08X} | {hex_values} | {ascii_values} <- TARGET")
                else:
                    print(f"{current_pos:08X} | {hex_values} | {ascii_values}")
                
    except FileNotFoundError:
        print(f"File {filename} not found")
    except Exception as e:
        print(f"Error processing file: {e}")

def main():
    """Main entry point."""
    filename = "tf2_misc_013.vpk"
    position = 71825399  # The position you found
    
    inspect_vpk_at_position(filename, position)

if __name__ == "__main__":
    main()
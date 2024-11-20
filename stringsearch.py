def search_vpk_for_flamethrower(vpk: int) -> None:
    """Search a specific VPK file for flamethrower references."""
    filename = f"tf2_misc_{str(vpk).zfill(3)}.vpk"
    
    try:
        # Read the entire file as bytes
        with open(filename, 'rb') as f:
            buffer = bytearray(f.read())
        
        search_term = b"medicbeam"
        start = 0
        found_any = False
        
        while True:
            try:
                # Find next occurrence
                index = buffer.index(search_term, start)
                found_any = True
                
                print(f"\n=== Found in {filename} at position {index} ===")
                
                # Show context around the match (100 chars before and after)
                context_start = max(0, index - 100)
                context_end = min(len(buffer), index + len(search_term) + 100)
                context = buffer[context_start:context_end]
                
                try:
                    # Decode and display the context
                    decoded = context.decode('ascii', errors='replace')
                    print("Context:")
                    print("-" * 50)
                    print(decoded)
                    print("-" * 50)
                except Exception as e:
                    print(f"Decoding error: {e}")
                
                # Move start position for next search
                start = index + len(search_term)
                
            except ValueError:
                if not found_any:
                    print(f"No matches in {filename}")
                break
            
    except FileNotFoundError:
        print(f"[{filename}] File not found")
    except Exception as e:
        print(f"[{filename}] Error processing file: {str(e)}")

def main():
    """Main entry point."""
    print(f"Searching for string in tf2_misc_000.vpk through tf2_misc_026.vpk")
    print("=" * 70)
    
    total_files_searched = 0
    
    # Search through specified range (000-026)
    for vpk_num in range(0, 27):  # 0 to 26 inclusive
        search_vpk_for_flamethrower(vpk_num)
        total_files_searched += 1
    
    print(f"\nSearch complete. Processed {total_files_searched} files.")

if __name__ == "__main__":
    main()

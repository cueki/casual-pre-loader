import sys
from pathlib import Path

def hex_dump(data: bytes, start: int, length: int = 16) -> str:
    """
    Create a hex dump of binary data with both hex and ASCII representation.
    
    Args:
        data: Binary data to dump
        start: Starting offset for the dump
        length: Number of bytes to show per line
    """
    hex_str = ""
    ascii_str = ""
    
    # Ensure we don't go beyond the data length
    end = min(start + length, len(data))
    
    # Create hex and ASCII representations
    for i in range(start, end):
        byte = data[i]
        hex_str += f"{byte:02X} "
        # Show printable characters in ASCII view, dots for others
        ascii_str += chr(byte) if 32 <= byte <= 126 else '.'
    
    # Pad hex view if needed
    padding = length - (end - start)
    hex_str += "   " * padding
    
    return f"{hex_str}  |  {ascii_str}"

def find_first_difference(data1: bytes, data2: bytes) -> int:
    """Find the first position where two byte sequences differ."""
    for i, (b1, b2) in enumerate(zip(data1, data2)):
        if b1 != b2:
            return i
    return min(len(data1), len(data2))

def compare_binaries(file1_path: str, file2_path: str, context_bytes: int = 8) -> None:
    """
    Compare two binary files and show detailed context around differences,
    including cases where one file is missing bytes.
    
    Args:
        file1_path: Path to the first file
        file2_path: Path to the second file
        context_bytes: Number of bytes to show before and after the difference
    """
    # Check if files exist
    if not Path(file1_path).is_file():
        print(f"Error: File not found - {file1_path}")
        return
    if not Path(file2_path).is_file():
        print(f"Error: File not found - {file2_path}")
        return
    
    try:
        with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
            data1 = f1.read()
            data2 = f2.read()
            
            # Find the first difference position
            first_diff = find_first_difference(data1, data2)
            
            if len(data1) != len(data2):
                shorter = min(len(data1), len(data2))
                size_diff = abs(len(data1) - len(data2))
                
                if len(data1) < len(data2):
                    print(f"\nFile 1 is missing {size_diff} byte{'s' if size_diff > 1 else ''}")
                    print(f"First difference at offset {first_diff:X}")
                else:
                    print(f"\nFile 2 is missing {size_diff} byte{'s' if size_diff > 1 else ''}")
                    print(f"First difference at offset {first_diff:X}")
                
                # Calculate range to show context
                start = max(0, first_diff - context_bytes)
                end = min(max(len(data1), len(data2)), first_diff + context_bytes + size_diff)
                
                # Show context from both files
                print("\nFile 1:")
                print(f"Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  |  ASCII")
                print("─" * 71)
                for i in range(start, min(end, len(data1)), 16):
                    print(f"{i:08X}  {hex_dump(data1, i)}")
                if len(data1) < len(data2):
                    print("(end of file)")
                
                print("\nFile 2:")
                print(f"Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  |  ASCII")
                print("─" * 71)
                for i in range(start, min(end, len(data2)), 16):
                    print(f"{i:08X}  {hex_dump(data2, i)}")
                if len(data2) < len(data1):
                    print("(end of file)")
                
                # Show the actual bytes that differ
                print("\nBytes at difference point:")
                if first_diff < shorter:
                    print(f"First differing bytes at offset {first_diff:08X}:")
                    print(f"File 1: 0x{data1[first_diff]:02X} ({chr(data1[first_diff]) if 32 <= data1[first_diff] <= 126 else '?'})")
                    print(f"File 2: 0x{data2[first_diff]:02X} ({chr(data2[first_diff]) if 32 <= data2[first_diff] <= 126 else '?'})")
                
                # Show extra bytes
                if len(data1) > len(data2):
                    extra_bytes = data1[len(data2):min(len(data2) + 5, len(data1))]
                    print(f"\nExtra bytes in File 1 starting at offset {len(data2):08X}:")
                    print("Hex:", " ".join(f"{b:02X}" for b in extra_bytes) + 
                          ("..." if len(data1) > len(data2) + 5 else ""))
                    print("ASCII:", "".join(chr(b) if 32 <= b <= 126 else '.' for b in extra_bytes) +
                          ("..." if len(data1) > len(data2) + 5 else ""))
                else:
                    extra_bytes = data2[len(data1):min(len(data1) + 5, len(data2))]
                    print(f"\nExtra bytes in File 2 starting at offset {len(data1):08X}:")
                    print("Hex:", " ".join(f"{b:02X}" for b in extra_bytes) +
                          ("..." if len(data2) > len(data1) + 5 else ""))
                    print("ASCII:", "".join(chr(b) if 32 <= b <= 126 else '.' for b in extra_bytes) +
                          ("..." if len(data2) > len(data1) + 5 else ""))
                
            else:
                # Handle case where files are same size
                differences = []
                for i, (b1, b2) in enumerate(zip(data1, data2)):
                    if b1 != b2:
                        differences.append((i, b1, b2))
                
                if not differences:
                    print("Files are identical")
                    return
                elif len(differences) == 1:
                    offset, byte1, byte2 = differences[0]
                    print(f"\nFound one byte difference at offset {offset} (0x{offset:X}):")
                    
                    # Show context
                    start = max(0, offset - context_bytes)
                    end = min(len(data1), offset + context_bytes + 1)
                    
                    print("\nFile 1:")
                    print(f"Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  |  ASCII")
                    print("─" * 71)
                    for i in range(start, end, 16):
                        print(f"{i:08X}  {hex_dump(data1, i)}")
                    
                    print("\nFile 2:")
                    print(f"Offset    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  |  ASCII")
                    print("─" * 71)
                    for i in range(start, end, 16):
                        print(f"{i:08X}  {hex_dump(data2, i)}")
                    
                    print(f"\nDifference at offset {offset:08X}:")
                    print(f"File 1: 0x{byte1:02X} ({chr(byte1) if 32 <= byte1 <= 126 else '?'})")
                    print(f"File 2: 0x{byte2:02X} ({chr(byte2) if 32 <= byte2 <= 126 else '?'})")
                else:
                    print(f"\nFound {len(differences)} differences:")
                    for offset, byte1, byte2 in differences:
                        print(f"Offset {offset:08X}: 0x{byte1:02X} vs 0x{byte2:02X}")
                    
    except IOError as e:
        print(f"Error reading files: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py file1 file2")
        sys.exit(1)
    
    compare_binaries(sys.argv[1], sys.argv[2])
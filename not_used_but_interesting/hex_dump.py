import binascii


def hex_dump(file_path):
    # Generates the hex dump of a file.
    try:
        with open(file_path, 'rb') as file:
            content = file.read()
        return binascii.hexlify(content).decode('utf-8')
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None


def compare_hex_dumps(file1, file2):
    # Compares the hex dumps of two files and prints the differences.
    hex1 = hex_dump(file1)
    hex2 = hex_dump(file2)

    if hex1 is None or hex2 is None:
        return

    # Convert hex strings to lists of bytes
    bytes1 = [hex1[i:i + 2] for i in range(0, len(hex1), 2)]
    bytes2 = [hex2[i:i + 2] for i in range(0, len(hex2), 2)]

    max_length = max(len(bytes1), len(bytes2))
    print("Comparing files:")
    print(f"File 1: {file1}")
    print(f"File 2: {file2}")
    print("\nDifferences:")

    for i in range(max_length):
        byte1 = bytes1[i] if i < len(bytes1) else "None"
        byte2 = bytes2[i] if i < len(bytes2) else "None"
        if byte1 != byte2:
            print(f"Byte {i:08}: File 1 = {byte1}, File 2 = {byte2}")


if __name__ == "__main__":
    file1 = "tf2_misc_dir.vpk"
    file2 = "tf2_misc_dir_mod.vpk"
    compare_hex_dumps(file1, file2)

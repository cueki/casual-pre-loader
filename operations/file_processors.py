from pathlib import Path
from valve_parsers import VPKFile, PCFFile
from operations.pcf_compress import remove_duplicate_elements


def pcf_empty_root_processor():
    def process_pcf(pcf: PCFFile) -> PCFFile:
        root_element = pcf.elements[0]
        attr_type, _ = root_element.attributes[b'particleSystemDefinitions']
        root_element.attributes[b'particleSystemDefinitions'] = (attr_type, [])
        return pcf

    return process_pcf


def pcf_mod_processor(mod_path: str):
    def process_pcf(game_pcf) -> PCFFile:
        mod_pcf = PCFFile(mod_path)
        mod_pcf.decode()
        result = remove_duplicate_elements(mod_pcf)
        return result

    return process_pcf


def find_pos(data, val) -> int:
    count = 0
    val_len = len(val)
    pos = 0
    while True:
        pos = data.find(val, pos)
        if pos == -1:
            break
        data[pos:pos + val_len] = b' ' * val_len
        count += 1
        pos += val_len
    return count


def game_type(file_path, uninstall=False) -> bool:
    with open(file_path, 'r') as file:
        lines = file.readlines()

    found = False
    for i, line in enumerate(lines):
        if '\ttype multiplayer_only' in line:
            lines[i] = line.replace('type multiplayer_only', '//type multiplayer_only')
            found = True
        if 'singleplayer_only' in line:
            lines[i] = line.replace('type singleplayer_only', '//type multiplayer_only')
            found = True

    if uninstall:
        for i, line in enumerate(lines):
            if 'singleplayer_only' in line:
                lines[i] = line.replace('singleplayer_only', 'multiplayer_only')
                found = True
            if '\t//type multiplayer_only' in line:
                lines[i] = line.replace('//type multiplayer_only', 'type multiplayer_only')
                found = True

    if found:
        with open(file_path, 'w') as file:
            file.writelines(lines)
        return True
    else:
        return False


def check_game_type(file_path) -> bool:
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return '\t//type multiplayer_only' in content or '\ttype singleplayer_only' in content
    except Exception as e:
        print(f"Error checking game type in {file_path}: {str(e)}")
        return False


def should_process_file(file_path: str) -> bool:
    target_paths = [
        "materials/effects/",
        "materials/models/",
        "materials/particle/",
        "materials/particles/",
        "materials/prediction/",
        "materials/sprites/healbeam"
    ]

    path_lower = file_path.lower()
    return any(path in path_lower for path in target_paths) and path_lower.endswith('.vmt')


get_val = [
    [34, 36, 105, 103, 110, 111, 114, 101, 122, 34, 9, 34, 49, 34],
    [34, 36, 105, 103, 110, 111, 114, 101, 122, 34, 9, 49],
    [36, 105, 103, 110, 111, 114, 101, 122, 9, 34, 49, 34],
    [36, 105, 103, 110, 111, 114, 101, 122, 9, 49],
    [34, 36, 105, 103, 110, 111, 114, 101, 122, 34, 32, 34, 49, 34],
    [34, 36, 105, 103, 110, 111, 114, 101, 122, 34, 32, 49],
    [36, 105, 103, 110, 111, 114, 101, 122, 32, 34, 49, 34],
    [36, 105, 103, 110, 111, 114, 101, 122, 32, 49]]


def get_from_vpk(vpk_path: Path):
    try:
        # check if VPK contains target paths before processing
        vpk_handler = VPKFile(str(vpk_path))
        file_list = vpk_handler.list_files()
        should_process = any(should_process_file(file) for file in file_list)

        if should_process:
            # process entire VPK
            with open(vpk_path, 'rb') as vpk_f:
                data = bytearray(vpk_f.read())
                total = 0
                for val in get_val:
                    placements = find_pos(data, bytes(val))
                    if placements > 0:
                        total += placements
                if total > 0:
                    with open(vpk_path, 'wb') as f:
                        f.write(data)
    except Exception as e:
        print(f"Error processing VPK {vpk_path}: {e}")


def get_from_file(file_path: Path):
    # lol. lmao, even
    try:
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())
            total = 0
            for val in get_val:
                placements = find_pos(data, bytes(val))
                if placements > 0:
                    total += placements
            if total > 0:
                with open(file_path, 'wb') as f:
                    f.write(data)
            return total
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 0


def get_from_custom_dir(custom_dir: Path):
    if not custom_dir.exists():
        return 0

    # process VPK files
    for vpk_file in custom_dir.glob("*.vpk"):
        get_from_vpk(vpk_file)

    for directory in custom_dir.glob("*"):
        if directory.is_dir():
            for pattern in ["materials/effects/**/*", "materials/models/**/*", "materials/particle/**/*",
                            "materials/particles/", "materials/prediction/**/*", "materials/sprites/healbeam*"]:
                for file_path in directory.glob(pattern):
                    if file_path.is_file():
                        get_from_file(file_path)

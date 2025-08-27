from pathlib import Path
from typing import Set, List, Optional
from core.folder_setup import folder_setup
from valve_parsers import VPKFile


def find_all_vtf_files(directory: Path) -> List[Path]:
    vtf_files = []

    # target directories
    target_dirs = [
        directory / "materials" / "models" / "weapons",
        directory / "materials" / "patterns"
    ]

    for target_dir in target_dirs:
        if target_dir.exists():
            vtf_files.extend(target_dir.glob("**/*.vtf"))
            print(f"Scanning {target_dir} - found {len(list(target_dir.glob('**/*.vtf')))} VTF files")
        else:
            print(f"Directory {target_dir} does not exist, skipping")

    return vtf_files


def find_all_vmt_files(directory: Path) -> Set[str]:
    vmt_files = []

    # same as VTF search
    target_dirs = [
        directory / "materials" / "models" / "weapons",
        directory / "materials" / "patterns"
    ]

    for target_dir in target_dirs:
        if target_dir.exists():
            vmt_files.extend(target_dir.glob("**/*.vmt"))

    return {vmt.stem.lower() for vmt in vmt_files}


def get_texture_path(vtf_path: Path, base_dir: Path) -> str:
    # get the relative path from the base directory
    rel_path = vtf_path.relative_to(base_dir)

    # remove the .vtf extension and convert to forward slashes
    texture_path = str(rel_path.with_suffix('')).replace('\\', '/')

    # if the path starts with 'materials/', remove it since VMT paths are relative to materials/
    if texture_path.startswith('materials/'):
        texture_path = texture_path[10:]

    return texture_path


def generate_vmt_content(texture_path: str, game_vpk: Optional[VPKFile] = None) -> str:
    # try to find matching VMT in game VPK
    if game_vpk:
        vmt_path = f"materials/{texture_path}.vmt"
        entry_info = game_vpk.get_file_entry(vmt_path)
        
        if entry_info:
            try:
                extension, directory, entry = entry_info
                file_data = game_vpk.read_from_archive(entry.archive_index, entry.entry_offset, entry.entry_length)
                
                if file_data:
                    if entry.preload_bytes > 0 and entry.preload_data:
                        vmt_content = entry.preload_data + file_data
                    else:
                        vmt_content = file_data
                    
                    return vmt_content.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Error reading VMT from game VPK: {e}")
    
    # fallback to generic VMT
    return f'"LightmappedGeneric"\n{{\n\t"$basetexture" "{texture_path}"\n}}\n'


def generate_missing_vmt_files(temp_mods_dir: Path = None, tf_path: str = None) -> int:
    if temp_mods_dir is None:
        temp_mods_dir = folder_setup.temp_mods_dir

    if not temp_mods_dir.exists():
        print(f"Directory {temp_mods_dir} does not exist")
        return 0

    # initialize VPK
    game_vpk = None
    if tf_path:
        game_vpk_path = Path(tf_path) / "tf2_misc_dir.vpk"
        if game_vpk_path.exists():
            try:
                game_vpk = VPKFile(str(game_vpk_path))
                game_vpk.parse_directory()
                print(f"Loaded game VPK: {game_vpk_path}")
            except Exception as e:
                print(f"Error loading game VPK: {e}")
                game_vpk = None
        else:
            print(f"Game VPK not found at: {game_vpk_path}")

    # find all vtf and vmt files
    vtf_files = find_all_vtf_files(temp_mods_dir)
    existing_vmts = find_all_vmt_files(temp_mods_dir)

    if not vtf_files:
        print("No VTF files found")
        return 0

    print(f"Found {len(vtf_files)} VTF files and {len(existing_vmts)} existing VMT files")

    created_count = 0

    for vtf_file in vtf_files:
        # check if a matching vmt already exists
        vtf_stem = vtf_file.stem.lower()

        if vtf_stem not in existing_vmts:
            # generate vmt file in the same directory as the vtf
            vmt_path = vtf_file.with_suffix('.vmt')
            texture_path = get_texture_path(vtf_file, temp_mods_dir)
            vmt_content = generate_vmt_content(texture_path, game_vpk)

            try:
                # write the vmt
                with open(vmt_path, 'w', encoding='utf-8') as f:
                    f.write(vmt_content)

                if game_vpk:
                    print(f"Created VMT from game VPK: {vmt_path}")
                else:
                    print(f"Created generic VMT: {vmt_path}")

            except Exception as e:
                print(f"Error creating VMT file {vmt_path}: {e}")
                continue

            created_count += 1
        else:
            print(f"VMT already exists for: {vtf_file.name}")

    return created_count

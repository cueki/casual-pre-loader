import re
import shutil
from pathlib import Path
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler
from core.parsers.vpk_file import VPKFile


def is_skybox_vmt(file_path: Path) -> bool:
    return ('skybox' in str(file_path).lower() and
            file_path.suffix.lower() == '.vmt')


def modify_basetexture_path(content: bytes) -> bytes:
    content_str = content.decode('utf-8', errors='replace')
    pattern = r'("\$basetexture"\s+")(skybox\/[^"]+)(")'
    modified = re.sub(pattern, lambda m: m.group(1) + m.group(2) + "1" + m.group(3),
                      content_str, flags=re.IGNORECASE)
    result = modified.encode('utf-8')
    return result


def handle_skybox_mods(temp_dir: Path, tf_path) -> int:
    skybox_vmts = [vmt for vmt in temp_dir.glob('**/*.vmt') if is_skybox_vmt(vmt)]
    if not skybox_vmts:
        return 0

    print(f"Found {len(skybox_vmts)} skybox vmts in {temp_dir.name}")
    vpk_path = str(Path(tf_path) / "tf2_misc_dir.vpk")
    patched_count = 0
    file_handler = FileHandler(vpk_path)
    for vmt_path in skybox_vmts:
        try:
            # modify basetexture path
            with open(vmt_path, 'rb') as f:
                original_content = f.read()

            modified_content = modify_basetexture_path(original_content)
            # get the original texture path
            orig_texture_path = Path("skybox/" + Path(vmt_path).stem)
            new_texture_path = f"{orig_texture_path}1"
            modify_basetexture_path(original_content)

            # copy vtf with modified name
            orig_vtf_path = vmt_path.with_suffix('.vtf')
            if orig_vtf_path.exists():
                new_vtf_path = folder_setup.temp_mods_dir / 'materials' / f"{new_texture_path}.vtf"
                new_vtf_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(orig_vtf_path, new_vtf_path)

            # find the vmt file in the vpk
            vmt_filename = vmt_path.name
            target_path = "materials/skybox/" + vmt_filename

            if not target_path:
                print(f"Error: Could not find {vmt_filename} in VPK")
                continue

            def processor(content):
                return modified_content

            success = file_handler.process_file(target_path, processor, create_backup=False)
            vmt_path.unlink()

            if success:
                patched_count += 1

        except Exception as e:
            print(f"Error processing skybox VMT {vmt_path}: {e}")
            import traceback
            traceback.print_exc()

    return patched_count


def restore_skybox_files(tf_path: str) -> int:
    backup_skybox_dir = Path("backup/materials/skybox")
    if not backup_skybox_dir.exists():
        return 0

    vpk = VPKFile(tf_path + "/tf2_misc_dir.vpk")
    vpk.parse_directory()
    restored_count = 0

    for skybox_vmt in backup_skybox_dir.glob("*.vmt"):
        vmt_name = skybox_vmt.name

        try:
            file_path = f"materials/skybox/{vmt_name}"

            with open(skybox_vmt, 'rb') as f:
                original_content = f.read()

            if vpk.patch_file(file_path, original_content, create_backup=False):
                restored_count += 1

        except Exception as e:
            print(f"Error restoring skybox {vmt_name}: {e}")

    return restored_count
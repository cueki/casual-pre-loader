import re
import shutil
from pathlib import Path
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler


def is_skybox_vmt(file_path: Path) -> bool:
    return ('skybox' in str(file_path).lower() and
            file_path.suffix.lower() == '.vmt')


def modify_basetexture_path(content: bytes) -> bytes:
    content_str = content.decode('utf-8', errors='replace')
    pattern = r'("\$basetexture"\s+")(skybox\/[^"]+)(")'
    modified = re.sub(pattern, lambda m: m.group(1) + m.group(2) + "1" + m.group(3),
                     content_str, flags=re.IGNORECASE)
    return modified.encode('utf-8')


def handle_skybox_mods(temp_dir: Path, tf_path) -> int:
    skybox_vmts = [vmt for vmt in temp_dir.glob('**/*.vmt') if is_skybox_vmt(vmt)]
    if not skybox_vmts:
        return 0

    print(f"Found {len(skybox_vmts)} skybox vmts in {temp_dir.name}")
    vpk_path = str(Path(tf_path) / "tf2_misc_dir.vpk")
    patched_count = 0

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

            file_handler = FileHandler(vpk_path)
            # find the vmt file in the vpk
            vmt_filename = vmt_path.name
            target_path = None
            for file_path in file_handler.vpk.find_files(f"*{vmt_filename}"):
                if file_path.endswith(vmt_filename):
                    target_path = file_path
                    break

            if not target_path:
                print(f"Error: Could not find {vmt_filename} in VPK")
                continue

            def processor(content):
                return modified_content

            success = file_handler.process_file(target_path, processor, create_backup=False)
            vmt_path.unlink()

            if success:
                patched_count += 1
                print(f"Successfully replaced {vmt_filename} in VPK")
            else:
                print(f"Failed to replace {vmt_filename} in VPK")

        except Exception as e:
            print(f"Error processing skybox VMT {vmt_path}: {e}")
            import traceback
            traceback.print_exc()

    return patched_count
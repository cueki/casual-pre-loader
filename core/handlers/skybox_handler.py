import shutil
from pathlib import Path
from core.folder_setup import folder_setup
from core.handlers.file_handler import FileHandler
from valve_parsers import VPKFile


def is_skybox_vmt(file_path: Path) -> bool:
    return ('skybox' in str(file_path).lower() and
            file_path.suffix.lower() == '.vmt')


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
            with open(vmt_path, 'rb') as f:
                original_content = f.read()

            # get the original texture path
            texture_path = Path("skybox/" + Path(vmt_path).stem)

            # copy vtf with modified name
            orig_vtf_path = vmt_path.with_suffix('.vtf')
            if orig_vtf_path.exists():
                new_vtf_path = folder_setup.temp_mods_dir / 'materials' / f"{texture_path}.vtf"
                new_vtf_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(orig_vtf_path, new_vtf_path)

            # find the vmt file in the vpk
            vmt_filename = vmt_path.name
            target_path = "materials/skybox/" + vmt_filename

            if not target_path:
                print(f"Error: Could not find {vmt_filename} in VPK")
                continue

            def processor(content):
                return original_content

            # patch vmt into vpk
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
    backup_skybox_dir = folder_setup.install_dir / "backup/materials/skybox"
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
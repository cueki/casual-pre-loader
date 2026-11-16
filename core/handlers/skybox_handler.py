import logging
from pathlib import Path

from valve_parsers import VPKFile

from core.config import config
from core.handlers.file_handler import FileHandler
from core.util.vpk import get_vpk_name

log = logging.getLogger()


def is_skybox_vmt(file_path: Path) -> bool:
    return ('skybox' in str(file_path).lower() and
            file_path.suffix.lower() == '.vmt')


def handle_skybox_mods(temp_dir: Path, tf_path: Path) -> int:
    # use specific path for skybox VMTs for better performance
    skybox_dir = temp_dir / 'materials' / 'skybox'
    if not skybox_dir.exists():
        return 0

    skybox_vmts = list(skybox_dir.glob('*.vmt'))
    if not skybox_vmts:
        return 0

    log.info(f"Found {len(skybox_vmts)} skybox vmts in {temp_dir.name}")
    vpk_file = tf_path / get_vpk_name(tf_path)
    patched_count = 0
    file_handler = FileHandler(vpk_file)
    for vmt_file in skybox_vmts:
        try:
            with vmt_file.open('rb') as f:
                vmt_content = f.read()

            # the vtf next to it stays where it is and ships in the custom VPK,
            # the vmt is patched over the vanilla one in the game VPK
            target_path = 'materials/skybox/' + vmt_file.name

            # patch vmt into vpk
            success = file_handler.process_file(target_path, vmt_content)
            vmt_file.unlink()

            if success:
                patched_count += 1

        except Exception:
            log.exception(f"Error processing skybox VMT {vmt_file}")

    return patched_count


def restore_skybox_files(tf_path: Path) -> int:
    backup_skybox_dir = config.install_dir / "backup/materials/skybox"
    if not backup_skybox_dir.exists():
        return 0

    vpk = VPKFile(tf_path / get_vpk_name(tf_path))
    restored_count = 0

    for skybox_vmt in backup_skybox_dir.glob("*.vmt"):
        vmt_name = skybox_vmt.name

        try:
            file_path = f"materials/skybox/{vmt_name}"

            with open(skybox_vmt, 'rb') as f:
                original_content = f.read()

            if vpk.patch_file(file_path, original_content, create_backup=False):
                restored_count += 1

        except Exception:
            log.exception(f"Error restoring skybox {vmt_name}")

    return restored_count

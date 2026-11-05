import logging
from pathlib import Path

from valve_parsers import VPKFile

from core.config import config
from core.handlers.file_handler import FileHandler
from core.util.file import move
from core.util.vpk import get_vpk_name

log = logging.getLogger()


def is_skybox_vmt(file_path: Path) -> bool:
    return 'skybox' in str(file_path).lower() and file_path.suffix.lower() == '.vmt'


def handle_skybox_mods(temp_dir: Path, tf_path: Path) -> int:
    # use specific path for skybox VMTs for better performance
    skybox_dir = temp_dir / 'materials/skybox'
    if not skybox_dir.is_dir():
        return 0

    skybox_vmts = [file for file in skybox_dir.iterdir() if file.suffix == '.vmt']
    if not skybox_vmts:
        return 0

    log.info(f'Found {len(skybox_vmts)} skybox vmts in {temp_dir.name}')
    vpk_file = tf_path / get_vpk_name(tf_path)
    patched_count = 0
    file_handler = FileHandler(vpk_file)
    for vmt_file in skybox_vmts:
        try:
            with vmt_file.open('rb') as f:
                vmt_content = f.read()

            # copy vtf with modified name
            orig_vtf_path = vmt_file.with_suffix('.vtf')
            if orig_vtf_path.is_file():
                new_vtf_path = temp_dir / 'materials/skybox' / orig_vtf_path.name
                move(orig_vtf_path, new_vtf_path)

            try:
                file_handler.process_file('materials/skybox/' + vmt_file.name, vmt_content)
                patched_count += 1
            finally:
                vmt_file.unlink()
        except Exception:
            log.exception(f'Error processing skybox VMT {vmt_file}')

    return patched_count


def restore_skybox_files(tf_path: Path) -> int:
    backup_skybox_dir = config.install_dir / 'backup/materials/skybox'
    if not backup_skybox_dir.is_dir():
        return 0

    vpk = VPKFile(tf_path / get_vpk_name(tf_path))
    restored_count = 0

    for skybox_vmt in (file for file in backup_skybox_dir.iterdir() if file.suffix == '.vmt'):
        try:
            with skybox_vmt.open('rb') as fd:
                original_content = fd.read()

            if vpk.patch_file(f'materials/skybox/{skybox_vmt.name}', original_content, create_backup=False):
                restored_count += 1
        except Exception:
            log.exception(f'Error restoring skybox {skybox_vmt.name}')

    return restored_count

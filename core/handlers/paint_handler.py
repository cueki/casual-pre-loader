import logging
from pathlib import Path

from valve_parsers import VPKFile

from core.constants import COSMETIC_VMT_PATHS
from core.handlers.file_handler import FileHandler
from core.util.vpk import get_vpk_name

log = logging.getLogger()

def find_cosmetics(tf_path, proxy_name: bytes) -> list[tuple[str, bytes]]:
    vpk_path = str(Path(tf_path) / get_vpk_name(tf_path))
    vpk = VPKFile(vpk_path)
    file_handler = FileHandler(vpk_path)

    results = []
    for vmt_path in file_handler.list_vmt_files():
        vmt_path_normalized = vmt_path.replace('\\', '/')
        if not any(vmt_path_normalized.startswith(path) for path in COSMETIC_VMT_PATHS):
            continue

        try:
            content = vpk.get_file_data(vmt_path)
            if content and proxy_name in content:
                results.append((vmt_path, content))
        except Exception:
            log.exception(f"Error reading VMT: {vmt_path}")

    return results


def disable_paints(tf_path):
    file_handler = FileHandler(str(Path(tf_path) / get_vpk_name(tf_path)))
    painted = find_cosmetics(tf_path, b'"ItemTintColor"')

    patched = 0
    for vmt_path, content in painted:
        try:
            modified = content.replace(b'"ItemTintColor"', b'"XtemTintColor"')
            if file_handler.process_file(vmt_path, modified):
                patched += 1
        except Exception:
            log.exception(f"Error processing VMT: {vmt_path}")

    log.info(f"Patched {patched} cosmetic VMTs to disable paints")


def enable_paints(tf_path):
    file_handler = FileHandler(str(Path(tf_path) / get_vpk_name(tf_path)))

    disabled = find_cosmetics(tf_path, b'"XtemTintColor"')
    if not disabled:
        return 0

    restored = 0
    for vmt_path, content in disabled:
        try:
            modified = content.replace(b'"XtemTintColor"', b'"ItemTintColor"')
            if file_handler.process_file(vmt_path, modified):
                restored += 1
        except Exception:
            log.exception(f"Error restoring paint VMT: {vmt_path}")

    if restored > 0:
        log.info(f"Restored {restored} paint VMTs")

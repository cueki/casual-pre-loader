from pathlib import Path


def get_vpk_name(tf_path):
    path = Path(tf_path)
    if path.name == "tf_goldrush":
        return "tf_goldrush_dir.vpk"
    return "tf2_misc_dir.vpk"


def check_vpk_writable(vpk_path: Path) -> bool:
    # check if VPK file can be written to (not locked by windows)
    try:
        with open(vpk_path, 'r+b'):
            pass
        return True
    except PermissionError:
        return False

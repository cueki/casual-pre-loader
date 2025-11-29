from pathlib import Path


def get_vpk_name(tf_path):
    path = Path(tf_path)
    if path.name == "tf_goldrush":
        return "tf_goldrush_dir.vpk"
    return "tf2_misc_dir.vpk"

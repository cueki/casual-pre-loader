from pathlib import Path


def auto_detect_tf2():
    common_paths = [
        "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
        "D:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2/tf",
        "~/.steam/steam/steamapps/common/Team Fortress 2/tf",
        "~/.local/share/Steam/steamapps/common/Team Fortress 2/tf",
    ]

    for path_str in common_paths:
        path = Path(path_str).expanduser()
        if path.exists() and (path / "gameinfo.txt").exists():
            return str(path)
    return None


def auto_detect_goldrush():
    common_paths = [
        "C:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "D:/Program Files (x86)/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "~/.steam/steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
        "~/.local/share/Steam/steamapps/common/Team Fortress 2 Gold Rush/tf_goldrush",
    ]

    for path_str in common_paths:
        path = Path(path_str).expanduser()
        if path.exists() and (path / "gameinfo.txt").exists():
            return str(path)
    return None


def validate_tf_directory(directory, validation_label=None):
    if not directory:
        if validation_label:
            validation_label.setText("")
        return False

    tf_path = Path(directory)

    # check if directory exists
    if not tf_path.exists():
        if validation_label:
            validation_label.setText("Directory does not exist!")
            validation_label.setStyleSheet("color: red;")
        return False

    # check if it's actually a tf directory
    if not (tf_path.name == "tf" or tf_path.name.endswith("/tf")):
        if validation_label:
            validation_label.setText("Selected directory should be named 'tf'")
            validation_label.setStyleSheet("color: orange;")

    # check for gameinfo.txt
    if not (tf_path / "gameinfo.txt").exists():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid tf/ directory")
            validation_label.setStyleSheet("color: red;")
        return False

    # check for tf2_misc_dir.vpk
    if not (tf_path / "tf2_misc_dir.vpk").exists():
        if validation_label:
            validation_label.setText("tf2_misc_dir.vpk not found - some features may not work")
            validation_label.setStyleSheet("color: orange;")
    else:
        if validation_label:
            validation_label.setText("Valid TF2 directory detected!")
            validation_label.setStyleSheet("color: green;")

    return True


def validate_goldrush_directory(directory, validation_label=None):
    if not directory:
        if validation_label:
            validation_label.setText("")
        return False

    gr_path = Path(directory)

    # check if directory exists
    if not gr_path.exists():
        if validation_label:
            validation_label.setText("Directory does not exist!")
            validation_label.setStyleSheet("color: red;")
        return False

    # check if it's actually a tf_goldrush directory
    if not (gr_path.name == "tf_goldrush" or gr_path.name.endswith("/tf_goldrush")):
        if validation_label:
            validation_label.setText("Selected directory should be named 'tf_goldrush'")
            validation_label.setStyleSheet("color: orange;")

    # check for gameinfo.txt
    if not (gr_path / "gameinfo.txt").exists():
        if validation_label:
            validation_label.setText("gameinfo.txt not found - this doesn't appear to be a valid tf_goldrush/ directory")
            validation_label.setStyleSheet("color: red;")
        return False

    # check for tf_goldrush_dir.vpk
    if not (gr_path / "tf_goldrush_dir.vpk").exists():
        if validation_label:
            validation_label.setText("tf_goldrush_dir.vpk not found - some features may not work")
            validation_label.setStyleSheet("color: orange;")
    else:
        if validation_label:
            validation_label.setText("Valid Gold Rush directory detected!")
            validation_label.setStyleSheet("color: green;")

    return True

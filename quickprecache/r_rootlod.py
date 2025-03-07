from pathlib import Path


def check_root_lod(game_path: str) -> bool:
    config_file = Path(game_path) / "tf" / "cfg" / "config.cfg"

    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return False

    # read the config file
    config_text = config_file.read_text()

    # find r_rootlod setting
    root_lod_index = config_text.find("r_rootlod")

    if root_lod_index > -1:
        # find the line with r_rootlod
        end_index = config_text.find("\n", root_lod_index)
        old_line = config_text[root_lod_index:end_index]

        # replace with r_rootlod "0"
        config_text = config_text.replace(old_line, 'r_rootlod "0"')

        # write the updated config
        config_file.write_text(config_text)
        print(f"Updated r_rootlod setting to 0 in {config_file}")
        return True

    return False

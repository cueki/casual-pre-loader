import logging
from pathlib import Path

log = logging.getLogger()


def check_root_lod(game_path: Path) -> bool:
    config_file = game_path / "tf" / "cfg" / "config.cfg"

    if not config_file.exists():
        log.warning(f"Config file not found: {config_file}")
        return False

    # read the config file. binds can hold any text the user typed, in whatever encoding the game wrote,
    # so undecodable bytes are carried through untouched instead of failing on the locale's codec
    config_text = config_file.read_text(encoding="utf-8", errors="surrogateescape")

    # find r_rootlod setting
    root_lod_index = config_text.find("r_rootlod")

    if root_lod_index > -1:
        # find the line with r_rootlod
        end_index = config_text.find("\n", root_lod_index)
        if end_index == -1:  # last line without a trailing newline
            end_index = len(config_text)
        old_line = config_text[root_lod_index:end_index]

        # replace with r_rootlod "0"
        config_text = config_text.replace(old_line, 'r_rootlod "0"')
        log.info(f"Updated r_rootlod setting to 0 in {config_file}")
    else:
        # r_rootlod not found, add it to the end of the file
        if not config_text.endswith("\n"):
            config_text += "\n"
        config_text += 'r_rootlod "0"\n'
        log.info(f"Added r_rootlod setting to {config_file}")

    # write the updated config
    config_file.write_text(config_text, encoding="utf-8", errors="surrogateescape")
    return True

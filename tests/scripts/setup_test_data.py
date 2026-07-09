import logging
import shutil
from pathlib import Path

from core.settings import Settings

log = logging.getLogger()


def setup_test_data():
    test_fixtures = Path("tests/fixtures")
    test_fixtures.mkdir(exist_ok=True)
    test_settings = Settings()
    tf2_path = test_settings.game_path

    if tf2_path is not None:
        log.info(f"Found TF2 installation at: {tf2_path}")

        # Copy essential files for testing
        files_to_copy = [
            "gameinfo.txt",
            "tf2_misc_dir.vpk",
            "tf2_misc_000.vpk",
            "tf2_misc_017.vpk"
        ]

        for file_name in files_to_copy:
            src = tf2_path / file_name
            dst = test_fixtures / "tf" / file_name
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                log.info(f"Copied: {file_name}")
    else:
        log.info("No TF2 installation found. Tests will use mock data.")


if __name__ == "__main__":
    setup_test_data()

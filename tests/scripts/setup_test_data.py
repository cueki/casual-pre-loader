import shutil
from pathlib import Path
from gui.settings_manager import SettingsManager


def setup_test_data():
    test_fixtures = Path("tests/fixtures")
    test_fixtures.mkdir(exist_ok=True)
    test_settings_manager = SettingsManager()
    tf2_path = test_settings_manager.get_tf_directory()

    if tf2_path:
        print(f"Found TF2 installation at: {tf2_path}")

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
                print(f"Copied: {file_name}")
    else:
        print("No TF2 installation found. Tests will use mock data.")


if __name__ == "__main__":
    setup_test_data()

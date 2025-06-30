import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture(scope="session")
def test_data_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="function")
def temp_tf_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        tf_path = Path(temp_dir) / "tf"
        tf_path.mkdir()

        # mock gameinfo
        (tf_path / "gameinfo.txt").write_text("""
"GameInfo"
{
    game    "Team Fortress 2"
    type    multiplayer_only
}
""")

        # mock VPK
        (tf_path / "tf2_misc_dir.vpk").write_bytes(b"MOCK_VPK_DATA" * 1000)

        # mock custom
        (tf_path / "custom").mkdir()

        yield str(tf_path)


@pytest.fixture(scope="function")
def mock_folder_setup(monkeypatch):
    from core.folder_setup import FolderConfig

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # mock folder structure
        mock_config = Mock(spec=FolderConfig)
        mock_config.temp_dir = temp_path / "temp"
        mock_config.temp_mods_dir = temp_path / "temp" / "mods"
        mock_config.backup_dir = temp_path / "backup"
        mock_config.addons_dir = temp_path / "addons"

        mock_config.temp_dir.mkdir(parents=True)
        mock_config.temp_mods_dir.mkdir(parents=True)
        mock_config.backup_dir.mkdir(parents=True)
        mock_config.addons_dir.mkdir(parents=True)

        monkeypatch.setattr("core.folder_setup.folder_setup", mock_config)
        yield mock_config


@pytest.fixture(autouse=True)
def ensure_test_isolation():
    original_cwd = Path.cwd()
    yield
    import os
    os.chdir(original_cwd)
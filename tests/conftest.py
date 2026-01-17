import pytest
import tempfile
import core.folder_setup
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

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # mock folder structure
        mock_config = Mock()
        mock_config.temp_dir = temp_path / "temp"
        mock_config.temp_to_be_patched_dir = temp_path / "temp" / "to_be_patched"
        mock_config.temp_to_be_vpk_dir = temp_path / "temp" / "to_be_vpk"
        mock_config.backup_dir = temp_path / "backup"
        mock_config.addons_dir = temp_path / "addons"
        mock_config.install_dir = temp_path / "install"

        for attr in ['temp_dir', 'temp_to_be_patched_dir', 'temp_to_be_vpk_dir', 'backup_dir', 'addons_dir', 'install_dir']:
            getattr(mock_config, attr).mkdir(parents=True, exist_ok=True)

        # create backup structure
        (mock_config.backup_dir / "particles").mkdir()
        (mock_config.backup_dir / "materials" / "skybox").mkdir(parents=True)
        monkeypatch.setattr(core.folder_setup, "folder_setup", mock_config)
        yield mock_config


@pytest.fixture(autouse=True)
def ensure_test_isolation():
    original_cwd = Path.cwd()
    yield
    import os
    os.chdir(original_cwd)

import pytest
import struct
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from core.parsers.vpk_file import VPKFile
from core.handlers.pcf_handler import restore_particle_files


class TestVPKSafety:
    @pytest.fixture
    def sample_vpk_data(self):
        # VPK header: signature, version, tree_size, file_data_section_size,
        # archive_md5_section_size, other_md5_section_size, signature_section_size
        header = struct.pack('<7I', 0x55AA1234, 2, 4, 0, 0, 48, 0)  # minimal header
        tree_data = b'\x00\x00\x00'  # empty tree (extension, path, filename terminators)
        return header + tree_data

    @pytest.fixture
    def temp_vpk_file(self, sample_vpk_data):
        with tempfile.NamedTemporaryFile(suffix='.vpk', delete=False) as f:
            f.write(sample_vpk_data)
            temp_path = Path(f.name)

        yield temp_path

        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def sample_pcf_data(self):
        return (
                b'<!-- dmx encoding binary 2 format pcf 1 -->\n\x00' +  # header
                b'\x01\x00' +  # string dict count (1)
                b'DmeElement\x00' +  # string
                b'\x01\x00\x00\x00' +  # element count (1)
                b'\x00\x00' +  # type index (0)
                b'root\x00' +  # element name
                b'\x00' * 16 +  # signature
                b'\x00\x00\x00\x00'  # attribute count (0)
        )

    def test_vpk_patching_safety(self, temp_vpk_file, sample_pcf_data):
        backup_path = Path(str(temp_vpk_file) + ".backup")

        if backup_path.exists():
            backup_path.unlink()

        original_size = temp_vpk_file.stat().st_size

        with patch.object(VPKFile, 'get_file_entry') as mock_get_entry:
            # mock entry with specific size
            mock_entry = Mock()
            mock_entry.archive_index = 0x7fff  # dir vpk
            mock_entry.entry_offset = original_size
            mock_entry.entry_length = len(sample_pcf_data)
            mock_entry.preload_bytes = 0
            mock_entry.preload_data = None

            mock_get_entry.return_value = ("pcf", "particles", mock_entry)

            # extend file to accommodate the mock data
            with open(temp_vpk_file, 'ab') as f:
                f.write(sample_pcf_data)

            vpk = VPKFile(str(temp_vpk_file))

            # test 1: successful patch with correct size pass
            result = vpk.patch_file("test.pcf", sample_pcf_data, create_backup=True)

            assert result, "VPK patching should succeed with correctly sized data"
            assert backup_path.exists(), "VPK backup was not created before modification"
            assert backup_path.stat().st_size == temp_vpk_file.stat().st_size, "VPK backup size mismatch"

            # test 2: oversized data should be rejected
            oversized_data = sample_pcf_data + b'\x00' * 100
            result = vpk.patch_file("test.pcf", oversized_data, create_backup=False)

            assert not result, "VPK patching should reject oversized data"
            # file size should remain unchanged after failed patch
            assert temp_vpk_file.stat().st_size >= original_size, "VPK file size was corrupted"

    def test_vpk_header_integrity(self, temp_vpk_file):
        # read original header
        with open(temp_vpk_file, 'rb') as f:
            original_header = f.read(28)  # VPK header is 28 bytes

        vpk = VPKFile(str(temp_vpk_file))

        # parse directory
        vpk.parse_directory()

        # file header should remain unchanged on disk
        with open(temp_vpk_file, 'rb') as f:
            current_header = f.read(28)

        assert current_header == original_header, "Somehow VPK header was corrupted during parsing -- VERY BAD"

        # signature should be valid
        signature = struct.unpack('<I', current_header[:4])[0]
        assert signature == 0x55AA1234, f"VPK signature corrupted: {hex(signature)}"

        # vpk object should be populated
        assert hasattr(vpk, 'directory'), "VPK should have directory attribute after parsing"
        assert vpk.directory is not None, "VPK directory should be populated after parsing"

    def test_atomic_vpk_operations(self, temp_vpk_file, sample_pcf_data):
        original_content = temp_vpk_file.read_bytes()

        with patch.object(VPKFile, 'get_file_entry') as mock_get_entry:
            mock_entry = Mock()
            mock_entry.archive_index = 0x7fff
            mock_entry.entry_offset = len(original_content)
            mock_entry.entry_length = len(sample_pcf_data)
            mock_entry.preload_bytes = 0
            mock_entry.preload_data = None

            mock_get_entry.return_value = ("pcf", "particles", mock_entry)

            vpk = VPKFile(str(temp_vpk_file))

            # Simulate write failure mid-operation
            original_open = open

            def failing_open(*args, **kwargs):
                if 'rb+' in args:
                    # Fail on write mode
                    raise IOError("Disk full")
                return original_open(*args, **kwargs)

            with patch('builtins.open', side_effect=failing_open):
                result = vpk.patch_file("test.pcf", sample_pcf_data, create_backup=False)

                # operation should fail
                assert not result, "VPK patch should fail gracefully on write error"

                # and should remain unchanged
                current_content = temp_vpk_file.read_bytes()
                assert current_content == original_content, "VPK file was partially corrupted"

    def test_no_modification_without_backup_files(self, temp_vpk_file, mock_folder_setup):
        backup_particles = mock_folder_setup.backup_dir / "particles"

        if backup_particles.exists():
            shutil.rmtree(backup_particles)

        result = restore_particle_files(str(temp_vpk_file.parent))
        # count should be 0 because the dir is empty
        assert result == 0, "Should not attempt restoration when backup files missing"

        # test with Path.exists returning False globally
        with patch('pathlib.Path.exists', return_value=False):
            result = restore_particle_files(str(temp_vpk_file.parent))
            assert result == 0, "Operations should fail gracefully when backup directory missing"

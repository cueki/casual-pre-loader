from core.handlers.skybox_handler import remove_staged_skybox_vmts


def test_remove_staged_skybox_vmts_keeps_textures(tmp_path):
    skybox_dir = tmp_path / "materials" / "skybox"
    skybox_dir.mkdir(parents=True)
    vmt = skybox_dir / "sky.vmt"
    vtf = skybox_dir / "sky.vtf"
    vmt.write_bytes(b"material")
    vtf.write_bytes(b"texture")

    assert remove_staged_skybox_vmts(tmp_path) == 1
    assert not vmt.exists()
    assert vtf.read_bytes() == b"texture"

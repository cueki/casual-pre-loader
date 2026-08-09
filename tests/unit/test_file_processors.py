from core.operations import file_processors


def test_get_from_custom_dir_skips_only_unchanged_external_files(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    unchanged_vpk = custom_dir / "external.vpk"
    managed_vpk = custom_dir / "_casual_preloader_dir.vpk"
    unchanged_vpk.touch()
    managed_vpk.touch()

    unchanged_material = custom_dir / "effects" / "materials" / "effects" / "old.vmt"
    changed_material = custom_dir / "effects" / "materials" / "effects" / "new.vmt"
    unchanged_material.parent.mkdir(parents=True)
    unchanged_material.touch()
    changed_material.touch()

    visited_vpks = []
    visited_files = []
    monkeypatch.setattr(file_processors, "get_from_vpk", visited_vpks.append)
    monkeypatch.setattr(file_processors, "get_from_file", visited_files.append)

    file_processors.get_from_custom_dir(
        custom_dir,
        skip_paths={
            "external.vpk",
            "effects/materials/effects/old.vmt",
        },
    )

    assert visited_vpks == [managed_vpk]
    assert visited_files == [changed_material]

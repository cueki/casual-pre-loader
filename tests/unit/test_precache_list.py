from core.quickprecache import precache_list


def test_make_precache_list_ignores_generated_quickprecache_vpks(tmp_path, monkeypatch):
    custom_dir = tmp_path / "tf" / "custom"
    custom_dir.mkdir(parents=True)
    generated_vpk = custom_dir / "_QuickPrecache.vpk"
    legacy_vpk = custom_dir / "QuickPrecache.vpk"
    addon_vpk = custom_dir / "addon.vpk"
    for path in (generated_vpk, legacy_vpk, addon_vpk):
        path.touch()

    visited = []

    def fake_manage_vpk(path):
        visited.append(path.name)
        return {"weapons/test.mdl"}

    monkeypatch.setattr(precache_list, "manage_vpk", fake_manage_vpk)

    assert precache_list.make_precache_list(str(tmp_path)) == {"weapons/test.mdl"}
    assert visited == ["addon.vpk"]

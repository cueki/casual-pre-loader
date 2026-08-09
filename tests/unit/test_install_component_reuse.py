from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from core.services import install as install_service


def test_install_reuses_direct_game_patches_for_a_texture_only_change(tmp_path, monkeypatch):
    tf_path = tmp_path / "tf"
    custom_dir = tf_path / "custom"
    addons_dir = tmp_path / "addons"
    addon_dir = addons_dir / "texture_addon" / "materials"
    addon_dir.mkdir(parents=True)
    (addon_dir / "texture.vtf").write_bytes(b"texture")
    custom_dir.mkdir(parents=True)
    (tf_path / "tf2_misc_dir.vpk").write_bytes(b"directory")

    temp_dir = tmp_path / "temp"
    folder_setup = SimpleNamespace(
        install_state_file=tmp_path / "install_state.json",
        addons_dir=addons_dir,
        temp_dir=temp_dir,
        temp_to_be_referenced_dir=temp_dir / "to_be_referenced",
        temp_to_be_patched_dir=temp_dir / "to_be_patched",
        temp_to_be_vpk_dir=temp_dir / "to_be_vpk",
        backup_dir=tmp_path / "backup",
        install_dir=tmp_path / "install",
    )
    folder_setup.temp_to_be_referenced_dir.mkdir(parents=True)

    state_store = Mock()
    state_store.evaluate.return_value = (False, "request_changed")
    state_store.reusable_external_custom_paths.return_value = set()
    state_store.can_reuse_direct_game_files.return_value = True
    state_store.can_reuse_precache.return_value = False
    monkeypatch.setattr(install_service, "folder_setup", folder_setup)
    monkeypatch.setattr(install_service, "InstallStateStore", lambda _path: state_store)
    monkeypatch.setattr(install_service, "check_writable", Mock(return_value=True))

    forbidden = [
        "initialize_pcf",
        "restore_skybox_files",
        "restore_particle_files",
        "enable_paints",
        "handle_skybox_mods",
        "disable_paints",
    ]
    for name in forbidden:
        monkeypatch.setattr(
            install_service,
            name,
            Mock(side_effect=AssertionError(f"{name} must be reused")),
        )

    remove_skybox_vmts = Mock(return_value=0)
    monkeypatch.setattr(install_service, "remove_staged_skybox_vmts", remove_skybox_vmts)
    monkeypatch.setattr(install_service, "stage_particle_selections", Mock())
    monkeypatch.setattr(install_service, "game_type", Mock())
    monkeypatch.setattr(install_service, "copy_config_files", Mock())
    monkeypatch.setattr(install_service, "patch_mainmenuoverride", Mock())
    monkeypatch.setattr(install_service, "relocate_mdl_paths", Mock())
    monkeypatch.setattr(install_service, "generate_missing_vmt_files", Mock())
    monkeypatch.setattr(install_service.VPKFile, "create", Mock(return_value=True))
    monkeypatch.setattr(install_service, "make_precache_list", Mock(return_value=set()))
    monkeypatch.setattr(install_service, "get_from_custom_dir", Mock())
    reset_working_copy = Mock()
    monkeypatch.setattr(install_service, "prepare_working_copy", reset_working_copy)

    quickprecache = Mock()
    monkeypatch.setattr(install_service, "QuickPrecache", Mock(return_value=quickprecache))

    result = install_service.InstallService().install(
        tf_path,
        ["texture_addon"],
        particle_selections={},
    )

    assert result is True
    remove_skybox_vmts.assert_called_once_with(folder_setup.temp_to_be_vpk_dir)
    quickprecache.flush_files.assert_called_once_with()
    state_store.save_current.assert_called_once()
    reset_working_copy.assert_called_once_with()

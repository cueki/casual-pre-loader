import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from core.services import install as install_service
from core.services import install_state
from core.services.install_state import InstallStateStore, make_request_header


def _request():
    return make_request_header(
        ["addon"],
        {"particle": "particle_mod"},
        disable_paint_colors=False,
        show_console_on_startup=True,
        fix_mdl_paths=True,
        skip_quickprecache=False,
        game_target="Team Fortress 2",
    )


def _setup_files(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    addons = project / "addons"
    particles = project / "particles"
    tf_path = tmp_path / "tf"
    custom = tf_path / "custom"

    (addons / "addon" / "materials").mkdir(parents=True)
    (addons / "addon" / "materials" / "addon.vtf").write_bytes(b"addon")
    (particles / "particle_mod" / "actual_particles").mkdir(parents=True)
    (particles / "particle_mod" / "actual_particles" / "particle.pcf").write_bytes(b"particle")
    custom.mkdir(parents=True)
    (custom / "external.vpk").write_bytes(b"external")
    (custom / "_casual_preloader_dir.vpk").write_bytes(b"managed")
    (tf_path / "models").mkdir()
    (tf_path / "models" / "precache.mdl").write_bytes(b"precache")
    (tf_path / "gameinfo.txt").write_text("gameinfo", encoding="utf-8")
    (tf_path / "tf2_misc_dir.vpk").write_bytes(b"game vpk")

    monkeypatch.setattr(
        install_state,
        "folder_setup",
        SimpleNamespace(addons_dir=addons, particles_dir=particles),
    )
    return tf_path


def test_saved_install_state_recognizes_an_unchanged_install(tmp_path, monkeypatch):
    tf_path = _setup_files(tmp_path, monkeypatch)
    store = InstallStateStore(tmp_path / "state" / "install_state.json")
    request = _request()

    store.save_current(tf_path, request, ["addon"], {"particle": "particle_mod"})

    assert store.evaluate(tf_path, request, ["addon"], {"particle": "particle_mod"}) == (
        True,
        "up_to_date",
    )
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["schema"] == install_state.INSTALL_STATE_SCHEMA

    (tf_path / "custom" / "runtime.vpk.sound.cache").write_bytes(b"runtime cache")
    assert store.evaluate(tf_path, request, ["addon"], {"particle": "particle_mod"}) == (
        True,
        "up_to_date",
    )


def test_source_external_and_managed_output_changes_invalidate_state(tmp_path, monkeypatch):
    tf_path = _setup_files(tmp_path, monkeypatch)
    store = InstallStateStore(tmp_path / "install_state.json")
    request = _request()
    selections = {"particle": "particle_mod"}

    def save():
        store.save_current(tf_path, request, ["addon"], selections)

    save()
    addon_file = install_state.folder_setup.addons_dir / "addon" / "materials" / "addon.vtf"
    addon_file.write_bytes(b"changed addon")
    assert store.evaluate(tf_path, request, ["addon"], selections)[1] == "source_files_changed"

    save()
    (tf_path / "custom" / "new_external.vpk").write_bytes(b"new")
    assert store.evaluate(tf_path, request, ["addon"], selections)[1] == "external_custom_changed"

    save()
    (tf_path / "custom" / "_casual_preloader_dir.vpk").unlink()
    assert store.evaluate(tf_path, request, ["addon"], selections)[1] == "managed_outputs_changed"


def test_request_changes_and_clear_invalidate_state(tmp_path, monkeypatch):
    tf_path = _setup_files(tmp_path, monkeypatch)
    store = InstallStateStore(tmp_path / "install_state.json")
    request = _request()
    selections = {"particle": "particle_mod"}
    store.save_current(tf_path, request, ["addon"], selections)

    changed_request = {**request, "selected_addons": ["another_addon"]}
    assert store.evaluate(tf_path, changed_request, ["addon"], selections)[1] == "request_changed"

    store.clear(tf_path)
    assert store.evaluate(tf_path, request, ["addon"], selections)[1] == "no_previous_state"


def test_unchanged_external_custom_files_can_be_reused_across_selection_changes(
    tmp_path,
    monkeypatch,
):
    tf_path = _setup_files(tmp_path, monkeypatch)
    loose_file = tf_path / "custom" / "effects" / "materials" / "effects" / "beam.vmt"
    loose_file.parent.mkdir(parents=True)
    loose_file.write_bytes(b"material")
    store = InstallStateStore(tmp_path / "install_state.json")
    request = _request()
    store.save_current(tf_path, request, ["addon"], {"particle": "particle_mod"})

    changed_selection = {**request, "selected_addons": ["another_addon"]}
    assert store.reusable_external_custom_paths(tf_path, changed_selection) == {
        "external.vpk",
        "effects/materials/effects/beam.vmt",
    }

    loose_file.write_bytes(b"changed material")
    assert store.reusable_external_custom_paths(tf_path, changed_selection) == {
        "external.vpk",
    }

    changed_recipe = {**changed_selection, "recipe": request["recipe"] + 1}
    assert store.reusable_external_custom_paths(tf_path, changed_recipe) == set()


def test_install_service_returns_before_mutating_an_up_to_date_target(tmp_path, monkeypatch):
    state_store = Mock()
    state_store.evaluate.return_value = (True, "up_to_date")
    reset_working_copy = Mock()
    progress = Mock()

    monkeypatch.setattr(install_service, "InstallStateStore", lambda _path: state_store)
    monkeypatch.setattr(install_service, "prepare_working_copy", reset_working_copy)
    monkeypatch.setattr(install_service, "check_writable", Mock(side_effect=AssertionError("must not write")))

    result = install_service.InstallService().install(
        tmp_path / "tf",
        [],
        on_progress=progress,
        particle_selections={},
    )

    assert result is False
    progress.assert_called_once_with(100, "Mods are already up to date")
    reset_working_copy.assert_not_called()


def test_precache_outputs_are_reused_only_when_models_and_files_match(tmp_path, monkeypatch):
    tf_path = _setup_files(tmp_path, monkeypatch)
    quick_vpk = tf_path / "custom" / "_QuickPrecache.vpk"
    quick_vpk.write_bytes(b"quick vpk")
    store = InstallStateStore(tmp_path / "install_state.json")
    request = _request()
    models = {"player/scout.mdl", "weapons/rocket.mdl"}
    store.save_current(
        tf_path,
        request,
        ["addon"],
        {"particle": "particle_mod"},
        precache_models=models,
    )

    changed_selection = {**request, "selected_addons": ["another_addon"]}
    assert store.can_reuse_precache(tf_path, changed_selection, models)
    assert not store.can_reuse_precache(
        tf_path,
        changed_selection,
        models | {"weapons/new.mdl"},
    )

    (tf_path / "models" / "precache.mdl").write_bytes(b"changed precache")
    assert not store.can_reuse_precache(tf_path, changed_selection, models)


def test_precache_outputs_from_another_recipe_are_not_reused(tmp_path, monkeypatch):
    tf_path = _setup_files(tmp_path, monkeypatch)
    store = InstallStateStore(tmp_path / "install_state.json")
    request = _request()
    store.save_current(
        tf_path,
        request,
        ["addon"],
        {"particle": "particle_mod"},
        precache_models=set(),
    )

    assert not store.can_reuse_precache(
        tf_path,
        {**request, "recipe": request["recipe"] + 1},
        set(),
    )

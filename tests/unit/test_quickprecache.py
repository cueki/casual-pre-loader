from unittest.mock import Mock

from core.quickprecache import quick_precache
from core.quickprecache.quick_precache import QuickPrecache


def test_precache_builder_partitions_models_in_one_deterministic_pass():
    models = {
        f"props/generated/model_{index:04d}_with_a_representative_path.mdl"
        for index in range(500)
    }
    precache = QuickPrecache("/tmp", debug=True)
    outputs = []
    precache.make_precache_sub_list_file = lambda filename, data: outputs.append((filename, data)) or True

    precache.make_precache_sub_list(models)

    combined = "".join(data for _filename, data in outputs)
    assert len(outputs) == precache.builder_index
    assert precache.total_compiles == len(outputs) + 1
    assert [filename for filename, _data in outputs] == [
        f"precache_{index}.qc" for index in range(len(outputs))
    ]
    for model in models:
        assert combined.count(f'$includemodel "{model}"') == 1


def test_precache_builder_accepts_a_single_path_larger_than_the_soft_limit():
    model = "props/" + ("very_long_directory/" * 120) + "model.mdl"
    precache = QuickPrecache("/tmp", debug=True)
    outputs = []
    precache.make_precache_sub_list_file = lambda filename, data: outputs.append((filename, data)) or True

    precache.make_precache_sub_list({model})

    assert len(outputs) == 1
    assert f'$includemodel "{model}"' in outputs[0][1]


def test_run_reuses_a_provided_model_list_without_scanning_or_flushing(monkeypatch):
    models = {"props/example.mdl"}
    precache = QuickPrecache("/tmp", debug=True)
    precache.flush_files = Mock(side_effect=AssertionError("existing files were already flushed"))
    precache.make_precache_sub_list = Mock()
    precache.make_precache_list_file = Mock()

    monkeypatch.setattr(
        quick_precache,
        "make_precache_list",
        Mock(side_effect=AssertionError("provided models must not be scanned again")),
    )
    monkeypatch.setattr(quick_precache, "check_root_lod", Mock())
    monkeypatch.setattr(quick_precache, "StudioMDL", Mock())

    assert precache.run(model_list=models, flush_existing=False)
    assert precache.model_list == models
    precache.make_precache_sub_list.assert_called_once_with(models)
    precache.make_precache_list_file.assert_called_once_with()

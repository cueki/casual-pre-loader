from pathlib import Path

from core.handlers import sound_handler


class FakeVPK:
    archives = {}
    list_calls = []

    def __init__(self, path):
        self.path = Path(path)

    def list_files(self, extension=None):
        self.list_calls.append((self.path.name, extension))
        return [
            path
            for path in self.archives[self.path.name]
            if path.rsplit('.', 1)[-1] == extension
        ]


def test_sound_mapping_indexes_each_vpk_once_and_preserves_priority(tmp_path, monkeypatch):
    first_vpk = tmp_path / "first.vpk"
    second_vpk = tmp_path / "second.vpk"
    first_vpk.touch()
    second_vpk.touch()
    FakeVPK.archives = {
        "first.vpk": [
            "sound/weapons/shared.wav",
            "sound/ui/alert.mp3",
        ],
        "second.vpk": [
            "sound/player/shared.wav",
            "sound/player/unique.wav",
        ],
    }
    FakeVPK.list_calls = []
    monkeypatch.setattr(sound_handler, "VPKFile", FakeVPK)

    shared = tmp_path / "shared.wav"
    unique = tmp_path / "unique.wav"
    alert = tmp_path / "alert.mp3"
    for path in (shared, unique, alert):
        path.write_bytes(b"sound")

    mappings = sound_handler.create_vpk_based_mappings(
        [shared, unique, alert],
        [first_vpk, second_vpk],
    )

    assert [mapping["canonical_path"] for mapping in mappings] == [
        "weapons/shared.wav",
        "player/unique.wav",
        "ui/alert.mp3",
    ]
    assert [mapping["final_path"] for mapping in mappings] == [
        "misc/weapons/shared.wav",
        "misc/player/unique.wav",
        "ui/alert.mp3",
    ]
    assert FakeVPK.list_calls == [
        ("first.vpk", "wav"),
        ("first.vpk", "mp3"),
        ("second.vpk", "wav"),
        ("second.vpk", "mp3"),
    ]


def test_sound_mapping_removes_files_missing_from_the_game_vpks(tmp_path, monkeypatch):
    vpk_path = tmp_path / "sounds.vpk"
    vpk_path.touch()
    FakeVPK.archives = {"sounds.vpk": ["sound/ui/found.wav"]}
    FakeVPK.list_calls = []
    monkeypatch.setattr(sound_handler, "VPKFile", FakeVPK)

    found = tmp_path / "found.wav"
    missing = tmp_path / "missing.wav"
    found.write_bytes(b"found")
    missing.write_bytes(b"missing")

    mappings = sound_handler.create_vpk_based_mappings([found, missing], [vpk_path])

    assert [mapping["source_file"] for mapping in mappings] == [found]
    assert found.exists()
    assert not missing.exists()


def test_sound_mapping_preserves_extension_case_matching(tmp_path, monkeypatch):
    vpk_path = tmp_path / "sounds.vpk"
    vpk_path.touch()
    FakeVPK.archives = {"sounds.vpk": ["sound/ui/alert.WAV"]}
    FakeVPK.list_calls = []
    monkeypatch.setattr(sound_handler, "VPKFile", FakeVPK)

    alert = tmp_path / "alert.WAV"
    alert.write_bytes(b"alert")

    mappings = sound_handler.create_vpk_based_mappings([alert], [vpk_path])

    assert [mapping["canonical_path"] for mapping in mappings] == ["ui/alert.WAV"]
    assert FakeVPK.list_calls == [("sounds.vpk", "WAV")]

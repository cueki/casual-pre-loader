import logging

import pytest

from core.util.perf import StageTimer


def test_stage_timer_records_stage_and_total_durations(caplog):
    clock_values = iter((10.0, 10.25, 11.0, 11.5))
    timer = StageTimer(logging.getLogger("test.perf"), "install", lambda: next(clock_values))

    first = timer.checkpoint("scan", files=12, bytes=4096)
    second = timer.checkpoint("build", files=3)

    with caplog.at_level(logging.INFO, logger="test.perf"):
        elapsed = timer.finish()

    assert first.duration == pytest.approx(0.25)
    assert first.elapsed == pytest.approx(0.25)
    assert first.counters == {"files": 12, "bytes": 4096}
    assert second.duration == pytest.approx(0.75)
    assert second.elapsed == pytest.approx(1.0)
    assert elapsed == pytest.approx(1.5)
    assert "operation=install complete elapsed=1.500s stages=2" in caplog.text

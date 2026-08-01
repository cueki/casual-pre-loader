import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class StageTiming:
    name: str
    duration: float
    elapsed: float
    counters: dict[str, int]


class StageTimer:
    """Record structured wall-clock timings for a multi-stage operation."""

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        clock: Callable[[], float] = perf_counter,
    ):
        self.logger = logger
        self.operation = operation
        self.clock = clock
        self.started_at = self.clock()
        self.last_checkpoint = self.started_at
        self.timings: list[StageTiming] = []

    def checkpoint(self, name: str, **counters: int) -> StageTiming:
        now = self.clock()
        timing = StageTiming(
            name=name,
            duration=now - self.last_checkpoint,
            elapsed=now - self.started_at,
            counters=counters,
        )
        self.timings.append(timing)
        self.last_checkpoint = now

        counter_text = " ".join(f"{key}={value}" for key, value in sorted(counters.items()))
        self.logger.info(
            "Performance operation=%s stage=%s duration=%.3fs elapsed=%.3fs%s",
            self.operation,
            name,
            timing.duration,
            timing.elapsed,
            f" {counter_text}" if counter_text else "",
        )
        return timing

    def finish(self) -> float:
        elapsed = self.clock() - self.started_at
        self.logger.info(
            "Performance operation=%s complete elapsed=%.3fs stages=%d",
            self.operation,
            elapsed,
            len(self.timings),
        )
        return elapsed

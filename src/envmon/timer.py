import time


class Timer():
    def __init__(self) -> None:
        self._now = time.perf_counter
        self._prev = 0.0

    @property
    def now(self) -> float:
        return self._now

    def tick(self) -> None:
        self._now = time.perf_counter

    def elapsed(self, interval: float) -> bool:
        if self._now - self._prev > interval:
            self._prev = self._now
            return True
        return False

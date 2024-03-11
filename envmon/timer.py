import time


class Event():
    def __init__(self, callback: callable, interval: float):
        self._callback = callback
        self._interval = interval
        self._prev = 0.0

    def update(self, now):
        if now - self._prev > self._interval:
            self._callback()
            self._prev = now


class Timer():
    def __init__(self) -> None:
        self._now = time.perf_counter()
        self._prev = 0.0
        self._events: list[Event] = []

    @property
    def now(self) -> float:
        return self._now

    def run(self) -> None:
        self._now = time.perf_counter()
        for e in self._events:
            e.update(self._now)

    def add_event(self, callback: callable, interval: float):
        self._events.append(Event(callback, interval))

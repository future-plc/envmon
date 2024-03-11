import time
from typing import Callable

"""
Basic timer class
Similar to arduino's "blink without delay"
Calculate delta between current time and the previous event trigger
"""

class Event():
    def __init__(self, callback: Callable, interval: float):
        self._callback = callback  # the function to call when event triggers
        self._interval = interval  # time between event triggers
        self._prev = 0.0

    def update(self, now):
        if now - self._prev > self._interval:
            self._callback()
            self._prev = now


class Timer():
    def __init__(self) -> None:
        self._now = time.perf_counter()  # current time
        self._prev = 0.0
        self._events: list[Event] = []  # array of event objects

    @property
    def now(self) -> float:
        return self._now

    def run(self) -> None:
        """ 
        Update the timer, check events for trigger
        Must be called every loop
        """
        self._now = time.perf_counter()
        for e in self._events:
            e.update(self._now)

    def add_event(self, callback: Callable, interval: float):
        """ Add an event object to the list """
        self._events.append(Event(callback, interval))

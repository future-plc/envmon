import smbus
from dataclasses import dataclass
from sensors import AQISensor
import display
import logging
import time
import argparse

UPDATE_INTERVAL = 1000
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--debug", help="Enable debug logging")

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


@dataclass
class Environment():
    o2_percent: float
    co2_percent: float
    particle_count: float
    vox: float


def update():
    for s in my_sensors:
        results = s.read()
        if results is not None:
            pass
            # write them to some data structure


# read command line args for loglevel
timer = Timer()

if __name__ == "__main__":
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN)

    if timer.elapsed(UPDATE_INTERVAL):
        update()
    display.draw()
    timer.tick()

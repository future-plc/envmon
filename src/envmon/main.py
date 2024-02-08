from sensors import AQISensor
from plotting import Plotter
from timer import Timer
from dataclasses import dataclass
import board
from busio import I2C
import logging
import argparse

i2c = I2C(board.SCL, board.SDA, frequency=100000)
my_sensors = [AQISensor(i2c)]
UPDATE_INTERVAL = 1000
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--debug", help="Enable debug logging")



@dataclass
class Environment():
    o2_percent: float
    co2_percent: float
    particle_count: float
    vox: float


def update() -> Environment:
    for s in my_sensors:
        results = s.read()
    return


timer = Timer()
plot = Plotter()

if __name__ == "__main__":
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARN)

    update()
    # plot.draw()
    # timer.tick()

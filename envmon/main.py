from scd40 import SCD4X
from pm25aqi import AQISensor
from bmp280 import BMP280_I2C
from plotting import Plotter, Environment
from timer import Timer
import time
import board
from busio import I2C
import logging
import argparse

UPDATE_INTERVAL = 1000
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--debug", help="Enable debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.WARNING)

def update(s: list[Sensor]) -> Environment:
    for s in my_sensors:
        results = s.read()
        print(results)
    return


timer = Timer()
# plot = Plotter()

if __name__ == "__main__":
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    i2c = I2C(board.SCL, board.SDA, frequency=100000)
    aqi = AQISensor(i2c)
    bmp280 = BMP280_I2C(i2c)
    scd40 = SCD4X(i2c)
    my_sensors = [aqi, bmp280]
    
    time.sleep(2)

    update(my_sensors)
    # plot.draw()
    # timer.tick()

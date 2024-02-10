from sensors import SensorData
from scd40 import SCD4X
from pm25aqi import AQISensor
from bmp280 import BMP280
from plotting import Plotter
from timer import Timer
import time
import board
from busio import I2C
import logging
import argparse
from sensors import Sensor
from dataclasses import dataclass

UPDATE_INTERVAL = 1000
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--debug", help="Enable debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.WARNING)



# plot = Plotter()

def print_readings(sensor_data: SensorData):
    print(sensor_data)


if __name__ == "__main__":
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    data = SensorData()

    i2c = I2C(board.SCL, board.SDA, frequency=100000)
    aqi = AQISensor(i2c, data)
    bmp280 = BMP280(i2c, data)
#    scd40 = SCD4X(i2c, data)
    my_sensors = [aqi, bmp280]

    timer = Timer()
    for sensor in my_sensors:
        timer.add_event(sensor.read, sensor.read_interval)

    timer.add_event(print_readings, 2.0)

    while 1:
        timer.run()
    # plot.draw()
    # timer.tick()

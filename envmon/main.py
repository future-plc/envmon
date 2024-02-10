from sensors import SensorData
from scd40 import SCD40
from pm25aqi import AQISensor
from bmp280 import BMP280
from plotting import Plotter
from timer import Timer
import board
from busio import I2C
import logging
import argparse
import time

UPDATE_INTERVAL = 1000
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--debug", help="Enable debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.WARNING)





if __name__ == "__main__":
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    data = SensorData()

    i2c = I2C(board.SCL, board.SDA, frequency=100000)
    aqi = AQISensor(i2c, data)
    bmp280 = BMP280(i2c, data)
    scd40 = SCD40(i2c, data)
    my_sensors = [aqi, bmp280, scd40]
    scd40.start_periodic_measurement()
    time.sleep(0.2)

    plot = Plotter(data)
    timer = Timer()
    for sensor in my_sensors:
        timer.add_event(sensor.read, sensor.read_interval)

    def print_readings():
        print(data)
    timer.add_event(print_readings, 5.0)
    timer.add_event(plot.draw, 0.1)

    try:
        while 1:
            timer.run()
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt Caught")
        print("Shutting down")
        #  put the sensors to sleep here


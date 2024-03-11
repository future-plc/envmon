import logging
import argparse
import time
import sys
import dataclasses

from sensors import SensorData
from scd40 import SCD40
from pm25aqi import AQISensor
from bmp280 import BMP280
from timer import Timer

import board
from busio import I2C

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib as mpl
import datetime as dt

"""
Sensor Data Plotter
(c) Gumgum Studio 2024
License: GPL 

This example is intended for educational purposes.
Sensors are not calibrated by default, as such,
this code should not be depended on in safety critical environments

"""

# Create command line arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "-v",
    "--debug",
    help="Enable debug logging",
    action="store_const",
    dest="loglevel",
    const=logging.DEBUG,
    default=logging.WARNING
)

# Set size and formatting options for the plot
mpl.rcParams['toolbar'] = 'None'
fig, axs = plt.subplots(
    7,
    figsize=(6.5, 4.5),
    layout='constrained',
    sharex=True
)

fig.canvas.manager.full_screen_toggle()
colors = ['red', 'orange', 'cyan', 'blue', 'green', 'purple', 'brown']

xs = []
y_data = []


def main():
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    # This is a dataclass whose fields are updated by the sensors 
    # when their "read" method is called
    data = SensorData()

    i2c = I2C(board.SCL, board.SDA, frequency=100000)
    aqi = AQISensor(i2c, data)
    bmp280 = BMP280(i2c, data)
    scd40 = SCD40(i2c, data)

    my_sensors = [aqi, bmp280, scd40]
    time.sleep(0.1)

    # required for C02 measurement
    scd40.start_periodic_measurement()
    time.sleep(0.2)

    # The Timer class keeps track of how long since reading each sensor
    # This prevents overloading the I2C bus with constant read requests
    timer = Timer()

    for sensor in my_sensors:
        timer.add_event(sensor.read, sensor.read_interval)

    # This function is called when the user left clicks (or touches touchscreen)
    def on_click(event):
        plt.close(fig)
        logging.debug("Click detected, shutting down")
        print("Shutting down")
        plt.close(fig)
        for s in my_sensors:
            s.shutdown()
        sys.exit(0)

    # Register the shutdown function with the click event
    plt.connect("button_press_event", on_click)

    # The animation loop for the plot window
    def animate(i, xs, y_data):
        timer.run()

        xs.append(dt.datetime.now().strftime('%H:%M:%S'))
        sensor_data_dict = dataclasses.asdict(data)
        y_data.append(sensor_data_dict)

        x_limit = 20

        xs = xs[-x_limit:]
        y_data = y_data[-x_limit:]
        for ax in axs:
            ax.clear()
        for key, ax, c in zip(list(sensor_data_dict), axs, colors):
            ys = [y[key] for y in y_data]
            ax.plot(xs, ys, lw=3, color=c)
            ax.set_ylabel(key.upper(), labelpad=10.0, rotation="horizontal")
            ax.set_xlim(0, 20)
            ax.set_xticks(ticks=xs)
            ax.tick_params(axis='x', labelrotation=45)
            ax.tick_params(axis='y', labelleft=False,
                           labelright=True, left=False, right=True)

        fig.suptitle("Sensor Data")

    ani = animation.FuncAnimation(fig, animate, fargs=(
        xs, y_data), interval=1000, cache_frame_data=False)

    while 1:
        plt.show()


if __name__ == "__main__":
    main()

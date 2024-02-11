#!/usr/bin/python3
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
License: GPL + MIT (dependencies)
"""

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

parser.add_argument(
    "-a",
    "--altitude",
    help="Set current altitude in meters",
    action="store",
    dest="altitude"
)

mpl.rcParams['toolbar'] = 'None'

fig, axs = plt.subplots(
    7,
    figsize=(6.5, 4.5),
    layout='constrained',
    sharex=True
)

fig.canvas.manager.full_screen_toggle()
xs = []
y_data = []

colors = ['red', 'orange', 'cyan', 'blue', 'green', 'purple', 'brown']
def on_click(event):
    plt.close(fig)

plt.connect("button_press_event", on_click)

def main():
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    data = SensorData()

    i2c = I2C(board.SCL, board.SDA, frequency=100000)
    aqi = AQISensor(i2c, data)
    bmp280 = BMP280(i2c, data)
    scd40 = SCD40(i2c, data)
    my_sensors = [aqi, bmp280, scd40]

    if args.altitude:
        scd40.altitude(args.altitude)

    scd40.start_periodic_measurement()
    time.sleep(0.2)

    timer = Timer()

    for sensor in my_sensors:
        timer.add_event(sensor.read, sensor.read_interval)

    def animate(i, xs, y_data):
        timer.run()

        xs.append(dt.datetime.now().strftime('%H:%M:%S'))
        sensor_data_dict = dataclasses.asdict(data)
        y_data.append(sensor_data_dict)  # list of dictified objects

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

    try:
        while 1:
            plt.show()
    except KeyboardInterrupt:

        logging.info("Keyboard Interrupt Caught")
        print("Shutting down")
        ani.pause()
        plt.close(fig)
        for s in my_sensors:
            s.shutdown()

        time.sleep(0.1)
        sys.exit(0)


if __name__ == "__main__":
    main()

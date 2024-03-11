import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
from sensors import SensorData
import datetime as dt



class Plotter():
    def __init__(self, sensor_data: SensorData):
        self.fig: Figure = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.xs: list[str] = []
        self.ys: list[float] = []
        self.animation = animation.FuncAnimation(
                self.fig,
                self._animate,
                fargs=(self.xs, self.ys),
                interval=1000
                )
        self.data: SensorData = sensor_data

    def draw(self):
        plt.show()

    def _animate(self, i, xs, ys):

        self.xs.append(dt.datetime.now().strftime('%H:%M:%S:$f'))
        self.ys.append(self.data.temp_c)

        x_limit = 20

        xs = self.xs[-x_limit:]
        ys = self.ys[-x_limit:]
        self.ax.clear()
        self.ax.plot(xs, ys)

        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.30)
        plt.title("Shit")
        plt.ylabel("poop")

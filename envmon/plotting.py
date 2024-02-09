import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
import datetime as dt
from dataclasses import dataclass


@dataclass
class Environment():
    o2_percent: float
    co2_percent: float
    particle_count: float
    vox: float

class Plotter():
    def __init__(self):
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
        self.env: Environment = None

    def draw(self, env: Environment):
        self.env = env
        plt.show()

    def _animate(self, i, xs, ys):
        vox = self.env.vox

        self.xs.append(dt.datetime.now().strftime('%H:%M:%S:$f'))
        self.ys.append(vox)

        x_limit = 20

        xs = self.xs[-x_limit:]
        ys = self.ys[-x_limit:]
        self.ax.clear()
        self.ax.plot(xs, ys)

        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.30)
        plt.title("Shit")
        plt.ylabel("poop")

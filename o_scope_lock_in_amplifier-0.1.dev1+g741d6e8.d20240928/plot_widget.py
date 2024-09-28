# plot_widget.py
from PySide2.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PlotWidget(QWidget):
    def __init__(self, title: str, xlabel: str, ylabel: str, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot(self, x, y):
        self.ax.clear()
        self.ax.plot(x, y)
        self.ax.set_title(self.figure.axes[0].get_title())
        self.ax.set_xlabel(self.figure.axes[0].get_xlabel())
        self.ax.set_ylabel(self.figure.axes[0].get_ylabel())
        self.canvas.draw()

# plot_widget.py

from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class PlotWidget(QWidget):
    def __init__(self, title: str, xlabel: str, ylabel: str, parent=None):
        super().__init__(parent)

        # Create a vertical layout to hold the toolbar and canvas
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Initialize the Matplotlib Figure and Canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Initialize the Navigation Toolbar and add it to the layout
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)

        # Create an Axes instance
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        # Initialize the plot line (empty)
        (self.line,) = self.ax.plot([], [], "r-")  # 'r-' is a red solid line

        # Lists to store the data points
        self.x_data = []
        self.y_data = []

    def plot(self, x: float, y: float):
        """
        Add a new data point to the plot and update the display.
        """
        self.x_data.append(x)
        self.y_data.append(y)
        self.line.set_data(self.x_data, self.y_data)

        # Adjust the view limits to accommodate new data
        self.ax.relim()
        self.ax.autoscale_view()

        # Redraw the canvas
        self.canvas.draw_idle()  # Use draw_idle for better performance during rapid updates

    def clear(self):
        """
        Clear the current plot data.
        """
        self.x_data.clear()
        self.y_data.clear()
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

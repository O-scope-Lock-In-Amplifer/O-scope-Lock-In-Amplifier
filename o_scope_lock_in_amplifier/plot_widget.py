from typing import List, Optional

from PySide6.QtWidgets import QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class PlotWidget(QWidget):
    def __init__(
        self, title: str, xlabel: str, ylabel: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        # Create a vertical layout to hold the toolbar and canvas
        self.main_layout = (
            QVBoxLayout()
        )  # Renamed to avoid conflict with QWidget.layout() method
        self.setLayout(self.main_layout)

        # Initialize the Matplotlib Figure and Canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)  # type: ignore
        self.main_layout.addWidget(self.canvas)

        # Initialize the Navigation Toolbar and add it to the layout
        self.toolbar = NavigationToolbar(self.canvas, self)  # type: ignore
        self.main_layout.addWidget(self.toolbar)

        # Create an Axes instance
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        # Initialize the plot line (empty)
        (self.line,) = self.ax.plot([], [], "r-")  # 'r-' is a red solid line

        # Lists to store the data points
        self.x_data: List[float] = []
        self.y_data: List[float] = []

    def plot(self, x: float, y: float) -> None:
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
        self.canvas.draw_idle()  # type: ignore  # Use draw_idle for better performance during rapid updates

    def clear(self) -> None:
        """
        Clear the current plot data.
        """
        self.x_data.clear()
        self.y_data.clear()
        self.line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()  # type: ignore

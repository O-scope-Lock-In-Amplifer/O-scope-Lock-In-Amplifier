import csv
import logging
import math
import sys
import time
from typing import Dict, List, Optional, Union

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

from o_scope_lock_in_amplifier.lock_in_proc import (
    generate_reference_signals,
    perform_lock_in,
)
from o_scope_lock_in_amplifier.oscilloscope_utils import OScope
from o_scope_lock_in_amplifier.plot_widget import PlotWidget
from o_scope_lock_in_amplifier.setup_panel import SetupPanel

logger = logging.getLogger("o_scope_lock_in_amplifier")


def format_si_prefix(value: float, unit: str) -> str:
    """
    Formats a value with SI prefix.

    Parameters:
        value (float): The value to format.
        unit (str): The unit symbol.

    Returns:
        str: Formatted string with SI prefix.
    """
    if math.isnan(value):
        return f"NaN {unit}"
    if value == 0:
        return f"0 {unit}"
    exponent = int(np.floor(np.log10(abs(value)) / 3) * 3)
    exponent = min(max(exponent, -24), 24)
    value_scaled = value / (10**exponent)
    prefixes = {
        -24: "y",
        -21: "z",
        -18: "a",
        -15: "f",
        -12: "p",
        -9: "n",
        -6: "μ",
        -3: "m",
        0: "",
        3: "k",
        6: "M",
        9: "G",
        12: "T",
        15: "P",
        18: "E",
        21: "Z",
        24: "Y",
    }
    prefix = prefixes.get(exponent, "")
    return f"{value_scaled:.3f} {prefix}{unit}"


class LockInSettingsPanel(QWidget):
    """
    A panel to configure lock-in amplifier parameters.
    """

    settings_changed = Signal()
    debug_run_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        layout = QFormLayout()

        # Low-pass filter cutoff frequency
        self.low_pass_cutoff_input = QDoubleSpinBox()
        self.low_pass_cutoff_input.setRange(0.1, 10000.0)
        self.low_pass_cutoff_input.setValue(10.0)
        self.low_pass_cutoff_input.setSuffix(" Hz")

        # Filter order
        self.filter_order_input = QSpinBox()
        self.filter_order_input.setRange(1, 10)
        self.filter_order_input.setValue(4)

        # Averaging length (as fraction of data length)
        self.averaging_length_input = QDoubleSpinBox()
        self.averaging_length_input.setRange(0.0, 1.0)
        self.averaging_length_input.setSingleStep(0.1)
        self.averaging_length_input.setValue(0.5)
        self.averaging_length_input.setSuffix(" (fraction)")

        # Add widgets to layout
        layout.addRow("Low-Pass Cutoff Frequency:", self.low_pass_cutoff_input)
        layout.addRow("Filter Order:", self.filter_order_input)
        layout.addRow("Averaging Length:", self.averaging_length_input)

        # Debug Run Button
        self.debug_button = QPushButton("Debug Run")
        layout.addRow(self.debug_button)

        # Connect signals using lambda to discard extra arguments
        self.low_pass_cutoff_input.valueChanged.connect(
            lambda _: self.settings_changed.emit()
        )
        self.filter_order_input.valueChanged.connect(
            lambda _: self.settings_changed.emit()
        )
        self.averaging_length_input.valueChanged.connect(
            lambda _: self.settings_changed.emit()
        )
        self.debug_button.clicked.connect(self.debug_run_requested.emit)

        self.setLayout(layout)

    def get_settings(self) -> Dict[str, Union[int, float]]:
        """
        Returns the current lock-in settings as a dictionary.
        """
        return {
            "low_pass_cutoff": self.low_pass_cutoff_input.value(),
            "filter_order": self.filter_order_input.value(),
            "averaging_length": self.averaging_length_input.value(),
        }


class DataProcessor(QObject):
    """
    Processes data from the oscilloscope and performs lock-in amplification.
    """

    # Define signals to emit processed data
    amplitude_computed = Signal(float, float)  # (amplitude, timestamp)
    phase_computed = Signal(float, float)  # (phase, timestamp)
    finished = Signal()

    def __init__(
        self,
        oscilloscope: OScope,
        start_time: float,
        lock_in_settings: Dict[str, Union[int, float]],
    ) -> None:
        super().__init__()
        self.oscilloscope = oscilloscope
        self._is_running = True
        self.start_time = start_time  # Reference start time
        self.lock_in_settings = lock_in_settings

    def run(self) -> None:
        """
        The main loop that acquires data, processes it, and emits the results.
        """
        while self._is_running:
            try:
                data = self.oscilloscope.get_data()

                # Perform lock-in amplification using the provided settings
                results = perform_lock_in(
                    ampl_data=data,
                    low_pass_cutoff=self.lock_in_settings["low_pass_cutoff"],
                    filter_order=int(self.lock_in_settings["filter_order"]),
                )

                # Get amplitude and phase
                amplitude = results["amplitude"]
                phase = np.degrees(results["phase"])  # Convert phase to degrees

                # Apply averaging over the specified length
                avg_length = self.lock_in_settings["averaging_length"]
                start_idx = int(len(amplitude) * (1 - avg_length))
                avg_amplitude = np.mean(amplitude[start_idx:])
                avg_phase = np.mean(phase[start_idx:])

                current_time = time.time() - self.start_time  # Relative time

                self.amplitude_computed.emit(avg_amplitude, current_time)
                self.phase_computed.emit(avg_phase, current_time)

                # Sleep briefly to prevent overwhelming the oscilloscope
                time.sleep(0.1)  # Adjust as needed

            except Exception as e:
                logger.error(f"Error in data processing thread: {e}")
                self.finished.emit()
                break

    def stop(self) -> None:
        """
        Stop the worker loop.
        """
        self._is_running = False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Oscilloscope Lock-In Amplifier")
        self.resize(1200, 800)

        # Initialize data storage lists
        self.amplitude_data: List[float] = []
        self.phase_data: List[float] = []
        self.time_data: List[float] = []

        # Create a central widget with a vertical layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout()
        central_widget.setLayout(self.central_layout)

        # Add Menu Bar
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)

        # File Menu
        file_menu = QMenu("File", self)
        self.menu_bar.addMenu(file_menu)

        # Export Action
        export_action = QAction("Export Data to CSV", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        # Add Tabs
        self.tabs = QTabWidget()
        self.central_layout.addWidget(self.tabs)

        # Main View Tab
        self.main_view = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_view.setLayout(self.main_layout)

        # Plots
        self.amplitude_plot = PlotWidget("Amplitude vs Time", "Time (s)", "Amplitude")
        self.amplitude_plot.ax.yaxis.set_major_formatter(
            FuncFormatter(lambda y, _: format_si_prefix(y, "V"))
        )
        self.phase_plot = PlotWidget("Phase vs Time", "Time (s)", "Phase (degrees)")

        # Current Phase and Amplitude Bars
        self.current_bar_layout = QHBoxLayout()

        self.current_amplitude_bar = QProgressBar()
        self.current_amplitude_bar.setOrientation(Qt.Orientation.Horizontal)
        self.current_amplitude_bar.setMaximum(100)  # Example max value
        self.current_amplitude_bar.setFormat("Amplitude: %p%")

        self.current_phase_bar = QProgressBar()
        self.current_phase_bar.setOrientation(Qt.Orientation.Horizontal)
        self.current_phase_bar.setMaximum(180)  # Phase in degrees (0-180)
        self.current_phase_bar.setFormat("Phase: %p°")

        self.current_bar_layout.addWidget(QLabel("Current Amplitude:"))
        self.current_bar_layout.addWidget(self.current_amplitude_bar)
        self.current_bar_layout.addWidget(QLabel("Current Phase:"))
        self.current_bar_layout.addWidget(self.current_phase_bar)

        # Run and Stop Buttons
        self.button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.stop_button = QPushButton("Stop")
        self.clear_button = QPushButton("Clear")
        self.stop_button.setEnabled(False)  # Initially disabled

        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.clear_button)

        # Add to main layout
        self.main_layout.addWidget(self.amplitude_plot)
        self.main_layout.addWidget(self.phase_plot)
        self.main_layout.addLayout(self.current_bar_layout)
        self.main_layout.addLayout(self.button_layout)

        self.tabs.addTab(self.main_view, "Main View")

        # Setup View Tab
        self.setup_view = SetupPanel()
        self.tabs.addTab(self.setup_view, "Setup")

        # Lock-In Settings Tab
        self.lock_in_settings_view = LockInSettingsPanel()
        self.tabs.addTab(self.lock_in_settings_view, "Lock-In Settings")

        # Placeholder for oscilloscope worker and thread
        self.oscilloscope_worker: Optional[DataProcessor] = None
        self.worker_thread: Optional[QThread] = None

        # Start time for relative time display
        self.start_time = time.time()

        # Connect SetupPanel's oscilloscope_configured signal to handle_configuration
        self.setup_view.oscilloscope_configured.connect(self.handle_configuration)

        # Connect Run and Stop buttons
        self.run_button.clicked.connect(self.start_data_acquisition)
        self.stop_button.clicked.connect(self.stop_data_acquisition)
        self.clear_button.clicked.connect(self.clear_data)

        # Connect debug run signal from lock-in settings panel
        self.lock_in_settings_view.debug_run_requested.connect(self.perform_debug_run)

    def handle_configuration(self, oscilloscope: OScope) -> None:
        """
        Handle the oscilloscope configuration by preparing for data acquisition.
        """
        logger.info("Oscilloscope configured and ready for data acquisition.")
        # Enable the Run button since oscilloscope is configured
        self.run_button.setEnabled(True)

    def start_data_acquisition(self) -> None:
        """
        Start the data acquisition and processing thread.
        """
        # Prevent starting multiple threads
        if self.oscilloscope_worker and self.worker_thread:
            if self.worker_thread.isRunning():
                logger.warning("Data acquisition is already running.")
                return

        if (
            not hasattr(self.setup_view, "oscilloscope")
            or not self.setup_view.oscilloscope
        ):
            QMessageBox.warning(
                self, "No Oscilloscope", "Please initialize an oscilloscope first."
            )
            return

        oscilloscope: OScope = self.setup_view.oscilloscope

        # Get lock-in settings
        lock_in_settings = self.lock_in_settings_view.get_settings()

        # Create a new worker and thread
        self.oscilloscope_worker = DataProcessor(
            oscilloscope, self.start_time, lock_in_settings
        )
        self.worker_thread = QThread()

        # Move the worker to the thread
        self.oscilloscope_worker.moveToThread(self.worker_thread)

        # Connect signals and slots
        self.worker_thread.started.connect(self.oscilloscope_worker.run)
        self.oscilloscope_worker.amplitude_computed.connect(self.update_amplitude)
        self.oscilloscope_worker.phase_computed.connect(self.update_phase)
        self.oscilloscope_worker.finished.connect(self.worker_thread.quit)
        self.oscilloscope_worker.finished.connect(self.oscilloscope_worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Start the thread
        self.worker_thread.start()

        # Update button states
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        logger.info("Data acquisition started.")

    def clear_data(self) -> None:
        self.amplitude_data = []
        self.phase_data = []
        self.time_data = []
        self.amplitude_plot.x_data = []
        self.amplitude_plot.y_data = []
        self.phase_plot.x_data = []
        self.phase_plot.y_data = []

    def stop_data_acquisition(self) -> None:
        """
        Stop the data acquisition and processing thread.
        """
        if (
            self.oscilloscope_worker
            and self.worker_thread
            and self.worker_thread.isRunning()
        ):
            self.oscilloscope_worker.stop()
            self.worker_thread.quit()
            self.worker_thread.wait()

            # Update button states
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            logger.info("Data acquisition stopped.")

            # Clear references to allow garbage collection
            self.oscilloscope_worker = None
            self.worker_thread = None
        else:
            logger.warning("Data acquisition is not running.")

    def update_amplitude(self, amplitude: float, timestamp: float) -> None:
        """
        Update the amplitude plot and progress bar.
        """
        # Update amplitude plot with relative time
        self.amplitude_plot.plot(timestamp, amplitude)

        # Append data to lists for export
        self.amplitude_data.append(amplitude)
        self.time_data.append(timestamp)

        # Update amplitude progress bar (assuming amplitude ranges 0-100)
        scaled_amp = min(max(amplitude, 0), 100)
        self.current_amplitude_bar.setValue(int(scaled_amp))

    def update_phase(self, phase: float, timestamp: float) -> None:
        """
        Update the phase plot and progress bar.
        """
        # Update phase plot with relative time
        self.phase_plot.plot(timestamp, phase % 360.0)

        # Append data to list for export
        self.phase_data.append(phase)

        # Update phase progress bar (0-180 degrees)
        scaled_phase = min(max(phase, 0), 180)
        self.current_phase_bar.setValue(int(scaled_phase))

    def export_data(self) -> None:
        """
        Export the collected data (phase, amplitude, time) to a CSV file.
        """
        if not self.time_data or not self.amplitude_data or not self.phase_data:
            QMessageBox.warning(
                self,
                "No Data",
                "No data available to export. Please start data acquisition first.",
            )
            return

        # Open a file dialog to choose the save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data to CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )

        if file_path:
            try:
                with open(file_path, mode="w", newline="") as csv_file:
                    csv_writer = csv.writer(csv_file)
                    # Write header
                    csv_writer.writerow(["Time (s)", "Amplitude", "Phase (degrees)"])
                    # Write data rows
                    for t, amp, ph in zip(
                        self.time_data, self.amplitude_data, self.phase_data
                    ):
                        csv_writer.writerow([t, amp, ph])

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Data successfully exported to {file_path}",
                )
                logger.info(f"Data exported to {file_path}")
            except Exception as e:
                logger.error(f"Failed to export data: {e}")
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"An error occurred while exporting data:\n{e}",
                )

    def perform_debug_run(self) -> None:
        """
        Perform a debug run that acquires data once and generates plots.
        """
        if (
            not hasattr(self.setup_view, "oscilloscope")
            or not self.setup_view.oscilloscope
        ):
            QMessageBox.warning(
                self, "No Oscilloscope", "Please initialize an oscilloscope first."
            )
            return

        oscilloscope: OScope = self.setup_view.oscilloscope

        # Get lock-in settings
        lock_in_settings = self.lock_in_settings_view.get_settings()

        # Acquire data once
        try:
            data = oscilloscope.get_data()
        except Exception as e:
            logger.error(f"Error acquiring data: {e}")
            QMessageBox.critical(
                self,
                "Data Acquisition Failed",
                f"An error occurred while acquiring data:\n{e}",
            )
            return

        # Perform lock-in amplification
        results = perform_lock_in(
            ampl_data=data,
            low_pass_cutoff=lock_in_settings["low_pass_cutoff"],
            filter_order=int(lock_in_settings["filter_order"]),
        )

        # Get time array
        t = results["time"]
        amplitude = results["amplitude"]
        phase = np.degrees(results["phase"])  # Convert phase to degrees

        # Generate reference signals for plotting
        N = len(t)
        time_increment = t[1] - t[0]
        cos_ref, sin_ref = generate_reference_signals(
            results["fundamental_freq"], N, time_increment
        )

        # Compute averaged amplitude and phase over specified length
        avg_length = lock_in_settings["averaging_length"]
        start_idx = int(len(amplitude) * (1 - avg_length))
        avg_amplitude = np.mean(amplitude[start_idx:])
        avg_phase = np.mean(phase[start_idx:])

        # Format averaged amplitude with SI prefix
        avg_amplitude_formatted = format_si_prefix(avg_amplitude, "V")

        # Create a single figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(
            f"Debug Run Results - Averaged Amplitude: {avg_amplitude_formatted}, "
            f"Averaged Phase: {avg_phase:.3f} degrees"
        )

        # Plot reference data and in-phase (sin) component scaled to amplitude
        axs[0, 0].plot(t, data.ref_dat, label="Reference Data")
        # Compute RMS amplitude of ref_dat
        ref_rms = np.sqrt(np.mean(np.square(data.ref_dat)))
        # Scale sin_ref to match amplitude
        scaled_sin_ref = ref_rms * np.sqrt(2) * sin_ref
        axs[0, 0].plot(
            t, scaled_sin_ref, label="In-Phase Component (Scaled)", alpha=0.7
        )
        axs[0, 0].set_xlabel("Time (s)")
        axs[0, 0].set_ylabel("Voltage (V)")
        axs[0, 0].set_title("Reference Data and In-Phase Component")
        axs[0, 0].legend()
        axs[0, 0].grid(True)

        # Plot acquired data
        axs[0, 1].plot(t, data.aqu_dat, label="Acquired Data", alpha=0.5)
        axs[0, 1].set_xlabel("Time (s)")
        axs[0, 1].set_ylabel("Voltage (V)")
        axs[0, 1].set_title("Acquired Data")
        axs[0, 1].legend()
        axs[0, 1].grid(True)

        # Plot recovered amplitude
        axs[1, 0].plot(t, amplitude, label="Recovered Amplitude", color="m")
        axs[1, 0].set_xlabel("Time (s)")
        axs[1, 0].set_ylabel("Amplitude (V)")
        axs[1, 0].set_title("Recovered Amplitude Signal")
        axs[1, 0].legend()
        axs[1, 0].grid(True)
        # Autoscale y-axis with SI prefixes
        axs[1, 0].yaxis.set_major_formatter(
            FuncFormatter(lambda y, _: format_si_prefix(y, "V"))
        )

        # Plot recovered phase
        axs[1, 1].plot(t, phase, label="Recovered Phase (degrees)", color="c")
        axs[1, 1].set_xlabel("Time (s)")
        axs[1, 1].set_ylabel("Phase (degrees)")
        axs[1, 1].set_title("Recovered Phase Signal")
        axs[1, 1].legend()
        axs[1, 1].grid(True)

        plt.tight_layout(
            rect=(0, 0.03, 1, 0.95)
        )  # Adjust layout to make room for the title
        plt.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Ensure that the worker thread is properly terminated when the application closes.
        """
        self.stop_data_acquisition()
        event.accept()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.root.handlers:
        handler.addFilter(logging.Filter("o_scope_lock_in_amplifier"))

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

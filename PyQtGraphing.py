#! /usr/bin/env python3

"""A sample program that demonstrates data acquisition and graphing.

Demonstrates how to use a QThread to capture sensor data independent of the main (GUI) thread,
and how to display it as a graph using the two well-known graphing frameworks available when using PyQt:
Matplotlib and PyQtGraph.
"""

import time
import sys
import psutil
import numpy as np

# Import Qt stuff.

from PySide6.QtCore import Signal, QThread
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

# Import Matplotlib stuff.

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure

# Import and configure PyQtGraph stuff.

import pyqtgraph as pg

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('useOpenGL', True)
pg.setConfigOption('leftButtonPan', False)


class MeasurementThread(QThread):
    """The MeasurementThread measures the CPU load periodically, then emits it as a signal.

    The advantage of doing this in a thread is that the data acquisition doesn't interfere with other
    threads; for example, it doesn't make the GUI sluggish.

    For this example we could do the data acquisition in the main thread just fine (using a QTimer) since
    reading the CPU load doesn't really take time. But if we would talk to external hardware where
    the interaction would take a noticable time, this could be important.
    """

    measurement = Signal(float, float)

    def __init__(self, measurement_interval, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.measurement_interval = measurement_interval

    def run(self):
        while not self.isInterruptionRequested():
            self.measurement.emit(time.time(), psutil.cpu_percent())
            time.sleep(self.measurement_interval)


class SlidingWindow:
    """A SlidingWindow gives access to the 'window_size' most recent values that were appended to it."""

    def __init__(self, window_size, dtype, buffer_size=None):
        if buffer_size is None:
            buffer_size = 10 * window_size
        self.data = np.empty(buffer_size, dtype=dtype)
        self.n = 0
        self.window_size = window_size

    def append(self, value):
        """Append a value to the sliding window."""
        if self.n == len(self.data):
            # Buffer is full.
            # Make room.
            copy_size = self.window_size - 1
            self.data[:copy_size] = self.data[-copy_size:]
            self.n = copy_size

        self.data[self.n] = value
        self.n += 1

    def window(self):
        """Get a window of the most recent 'window_size' samples (or less if not available)."""
        return self.data[max(0, self.n - self.window_size):self.n]


class MatplotlibGraphWidget(QWidget):
    """A Widget that has a Matplotlib graph sub-widget and updates its data."""

    def __init__(self, sliding_window_size, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.setMinimumSize(300, 200)

        xy_dtype = np.dtype([("x", np.float64), ("y", np.float64)])
        self.xy = SlidingWindow(sliding_window_size, xy_dtype)

        fig = Figure()
        self.ax = fig.subplots()
        self.ax.grid()
        self.line2d, = self.ax.plot([], [], "rx")
        self.canvas = FigureCanvas(fig)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        app = QApplication.instance()
        app.measurement_thread.measurement.connect(self.handleMeasurement)

        self.updateGraph()

    def handleMeasurement(self, timestamp, value):
        """Receive a timestamped value and update the graph."""

        self.xy.append((timestamp, value))
        self.updateGraph()

    def updateGraph(self):
        """Update graph and change window title to show update duration."""

        t1 = time.monotonic()
        
        w = self.xy.window()  # Get recent timestamps and values.

        t_now = time.time()

        # Set the line2d (plotline) data.
        self.line2d.set_data(w["x"] - t_now, w["y"])

        # Magic to do rescale & redraw.
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

        t2 = time.monotonic()

        duration = (t2 - t1)

        self.setWindowTitle("matplotlib: {:.3f} ms".format(1000.0 * duration))


class PyQtGraphWidget(QWidget):
    """A Widget that has a PyQtGraph sub-widget and updates its data."""

    def __init__(self, sliding_window_size, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.setMinimumSize(300, 200)

        xy_dtype = np.dtype([("x", np.float64), ("y", np.float64)])
        self.xy = SlidingWindow(sliding_window_size, xy_dtype)

        plotWidget = pg.PlotWidget()
        self.plot = plotWidget.plot(symbol='x', symbolPen='r', pen=None)
        plotWidget.showGrid(x=1, y=1, alpha = 0.1)

        layout = QVBoxLayout()
        layout.addWidget(plotWidget)
        self.setLayout(layout)

        app = QApplication.instance()
        app.measurement_thread.measurement.connect(self.handleMeasurement)

        self.updateGraph()

    def handleMeasurement(self, timestamp, value):
        """Receive a timestamped value and update the graph."""
        self.xy.append((timestamp, value))
        self.updateGraph()

    def updateGraph(self):
        """Update graph and change window title to show update duration."""

        t1 = time.monotonic()

        w = self.xy.window()  # Get recent timestamps and values.

        t_now = time.time()

        self.plot.setData(w["x"] - t_now, w["y"])

        t2 = time.monotonic()

        duration = (t2 - t1)

        self.setWindowTitle("pyqtgraph: {:.3f} ms".format(1000.0 * duration))


class Application(QApplication):

    def __init__(self, measurement_interval, sliding_window_size, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.measurement_thread = MeasurementThread(measurement_interval)

        self.matplotlib_graph_widget = MatplotlibGraphWidget(sliding_window_size)

        self.pyqtgraph_graph_widget = PyQtGraphWidget(sliding_window_size)

        self.matplotlib_graph_widget.show()
        self.pyqtgraph_graph_widget.show()

        self.aboutToQuit.connect(self.aboutToQuitHandler)

        print("Starting data acquisition thread.")
        self.measurement_thread.start()

    def aboutToQuitHandler(self):
        print("Stopping data acquisition thread.")
        self.measurement_thread.requestInterruption()
        self.measurement_thread.wait()
        
app = None

def main():

    global app
    measurement_interval = 0.100 # [s] (acquire data at approx. 10 Hz)
    sliding_window_size = 100 # [samples]
    app = Application(measurement_interval, sliding_window_size, sys.argv)
    app.exec()

if __name__ == "__main__":
    main()

from PyQt5 import QtCore, QtGui, QtWidgets
from datetime import datetime
import requests
import os
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

OPENWEATHER_API_KEY = "3fae6cca1db478f55461f19fe07b602e"
IP_API_URL = "http://ip-api.com/json"
OPENWEATHER_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_BACKGROUND_IMAGE = "bgimg.png"
WEATHER_BACKGROUND_PATH = "weather_backgrounds"
ICON_PATH = "icons"

class TempGraphCanvas(FigureCanvas):
    def __init__(self, parent=None, days=None, max_temps=None, min_temps=None):
        self.fig = Figure(figsize=(8, 3), dpi=100, facecolor='none')
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumHeight(250)
        self.plot(days, max_temps, min_temps)

    def plot(self, days, max_temps, min_temps):
        import numpy as np
        from scipy.interpolate import make_interp_spline

        self.axes.clear()
        self.fig.patch.set_alpha(0.0)
        self.axes.set_facecolor('none')

        x = np.arange(len(days))

        # Spline interpolation for smooth curves
        if len(x) >= 3:
            xnew = np.linspace(x.min(), x.max(), 300)
            spline_max = make_interp_spline(x, max_temps, k=3)
            spline_min = make_interp_spline(x, min_temps, k=3)
            smooth_max = spline_max(xnew)
            smooth_min = spline_min(xnew)

            self.axes.plot(xnew, smooth_max, label='Max Temp', color='tomato', linewidth=2)
            self.axes.plot(xnew, smooth_min, label='Min Temp', color='deepskyblue', linewidth=2)
        else:
            # Not enough points for spline, fallback to straight lines
            self.axes.plot(x, max_temps, label='Max Temp', color='tomato', linewidth=2)
            self.axes.plot(x, min_temps, label='Min Temp', color='deepskyblue', linewidth=2)

        self.axes.set_title('Temperature Trend', color='white')
        self.axes.set_ylabel('Temperature (°C)', color='white')
        self.axes.set_xticks(x)
        self.axes.set_xticklabels(days)
        self.axes.tick_params(axis='x', colors='white')
        self.axes.tick_params(axis='y', colors='white')
        self.axes.grid(False)
        self.axes.legend(facecolor='black', edgecolor='white', labelcolor='white')
        self.draw()

class HoverGifIcon(QtWidgets.QLabel):
    def __init__(self, gif_path, size=None, parent=None):
        super().__init__(parent)
        self.gif_path = gif_path
        self.icon_size = size
        self.movie = QtGui.QMovie(self.gif_path)
        self.movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.movie.jumpToFrame(0)

        if size is None or size == (0, 0):
            gif_size = self.movie.currentPixmap().size()
            self.icon_size = (gif_size.width(), gif_size.height())

        self.movie.setScaledSize(QtCore.QSize(*self.icon_size))
        self.setMovie(self.movie)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setMinimumSize(self.icon_size[0] + 10, self.icon_size[1] + 10)
        self.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.movie.start()
        self.movie.setPaused(True)

    def set_gif(self, gif_path):
        self.gif_path = gif_path
        self.movie.stop()
        self.movie.setFileName(self.gif_path)
        self.movie.start()
        self.movie.setScaledSize(QtCore.QSize(*self.icon_size))
        self.movie.setPaused(True)

    def enterEvent(self, event):
        self.movie.setPaused(False)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.movie.setPaused(True)
        self.movie.jumpToFrame(0)
        super().leaveEvent(event)

class WeatherApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('icon.ico'))
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Real-Time Weather App")
        self.resize(1280, 720)

        # Main layout with 30 gap from all sides
        self.content_layout = QtWidgets.QVBoxLayout(self)
        self.content_layout.setContentsMargins(30, 30, 30, 30)  # 30 gap from all corners

        self.update_background(DEFAULT_BACKGROUND_IMAGE)

        # Info box (black transparent)
        self.info_box = QtWidgets.QWidget()
        self.info_box.setStyleSheet("background-color: rgba(0, 0, 0, 128); border-radius: 20px;")
        info_box_layout = QtWidgets.QVBoxLayout()
        info_box_layout.setContentsMargins(20, 20, 20, 20)  # Padding inside box
        info_box_layout.setSpacing(0)
        self.info_box.setLayout(info_box_layout)

        # Make info_box expand to fill the window
        self.info_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Scroll area inside info box
        self.info_content = QtWidgets.QWidget()
        self.info_content_layout = QtWidgets.QVBoxLayout(self.info_content)
        self.info_content_layout.setSpacing(18)
        self.info_content_layout.setContentsMargins(0, 0, 0, 0)

        self.info_scroll = QtWidgets.QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setWidget(self.info_content)
        self.info_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        self.info_scroll.viewport().setStyleSheet("background: transparent;")
        self.info_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        # Scroll area expands to fill info_box
        self.info_scroll.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        info_box_layout.addWidget(self.info_scroll)
        self.content_layout.addWidget(self.info_box)

        # Add everything to self.info_content_layout
        self.title_label = QtWidgets.QLabel("Today's Weather")
        self.title_label.setFont(QtGui.QFont("Helvetica", 28, QtGui.QFont.Bold))
        self.title_label.setStyleSheet("color: white; padding: 10px; background: transparent;")
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_content_layout.addWidget(self.title_label, alignment=QtCore.Qt.AlignTop)

        self.clock_label = QtWidgets.QLabel()
        self.clock_label.setFont(QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold))
        self.clock_label.setStyleSheet("color: white; padding: 10px; background: transparent;")
        self.clock_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_content_layout.addWidget(self.clock_label, alignment=QtCore.Qt.AlignTop)
        self.update_clock()

        weather_info_row = QtWidgets.QHBoxLayout()
        weather_info_row.setAlignment(QtCore.Qt.AlignCenter)

        initial_gif = os.path.join(ICON_PATH, "sunny.gif")
        self.weather_icon_label = HoverGifIcon(initial_gif, size=None)
        weather_info_row.addWidget(self.weather_icon_label)

        self.weather_label = QtWidgets.QLabel("Getting weather data...")
        self.weather_label.setFont(QtGui.QFont("Arial", 15))
        self.weather_label.setStyleSheet("color: white; background: transparent; padding-left: 15px;")
        self.weather_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        weather_info_row.addWidget(self.weather_label)
        self.info_content_layout.addLayout(weather_info_row)

        self.info_content_layout.addSpacing(10)

        self.forecast_title = QtWidgets.QLabel("7-Day Forecast")
        self.forecast_title.setFont(QtGui.QFont("Arial", 18, QtGui.QFont.Bold))
        self.forecast_title.setStyleSheet("color: white; padding: 8px; background: transparent;")
        self.forecast_title.setAlignment(QtCore.Qt.AlignCenter)
        self.info_content_layout.addWidget(self.forecast_title, alignment=QtCore.Qt.AlignTop)

        self.forecast_widget = QtWidgets.QWidget()
        self.forecast_widget.setStyleSheet("background: transparent; padding: 0px;")
        self.forecast_layout = QtWidgets.QHBoxLayout()
        self.forecast_layout.setContentsMargins(10, 10, 10, 10)
        self.forecast_widget.setLayout(self.forecast_layout)
        self.info_content_layout.addWidget(self.forecast_widget, alignment=QtCore.Qt.AlignTop)

        self.toggle_graph_checkbox = QtWidgets.QCheckBox("Show Temperature Graph")
        self.toggle_graph_checkbox.setStyleSheet("color: white;")
        self.toggle_graph_checkbox.setChecked(True)
        self.toggle_graph_checkbox.stateChanged.connect(self.toggle_graph_visibility)
        self.info_content_layout.addWidget(self.toggle_graph_checkbox)

        self.info_content_layout.addSpacing(15)

        # Refresh button is now outside the text box and stretched to window width
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setFont(QtGui.QFont("Arial", 12))
        self.refresh_button.setStyleSheet(
            "background-color: #4682B4; color: white; padding: 16px 0; border-radius: 10px;"
        )
        self.refresh_button.clicked.connect(self.on_refresh_clicked)

        # Use a horizontal layout to stretch the button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0)
        button_layout.addWidget(self.refresh_button)
        self.content_layout.addLayout(button_layout)
        self.refresh_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.display_weather()

    def on_refresh_clicked(self):
        self.refresh_button.setText("Refreshing...")
        self.refresh_button.setEnabled(False)
        QtCore.QTimer.singleShot(100, self._do_refresh)  # Small delay so UI updates the text

    def _do_refresh(self):
        self.display_weather()
        self.refresh_button.setText("Refresh")
        self.refresh_button.setEnabled(True)

    def toggle_graph_visibility(self):
        if hasattr(self, 'temp_graph'):
            self.temp_graph.setVisible(self.toggle_graph_checkbox.isChecked())

    def resizeEvent(self, event):
        self.update_background(self.current_background)
        super().resizeEvent(event)

    def update_background(self, image_path):
        self.current_background = image_path
        palette = self.palette()
        background = QtGui.QPixmap(image_path)
        scaled_background = background.scaled(self.size(), QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
        palette.setBrush(QtGui.QPalette.Window, QtGui.QBrush(scaled_background))
        self.setPalette(palette)

    def update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%A, %B %d, %Y\n%H:%M:%S"))
        QtCore.QTimer.singleShot(1000, self.update_clock)

    def get_user_location(self):
        try:
            response = requests.get(IP_API_URL)
            response.raise_for_status()
            data = response.json()
            return data['lat'], data['lon'], data['city'], data['regionName']
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to retrieve location: {e}")
            return None, None, None, None

    def get_weather(self, lat, lon):
        try:
            response = requests.get(OPENWEATHER_WEATHER_URL, params={
                "lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to retrieve weather data: {e}")
            return None

    def get_7day_forecast(self, lat, lon):
        try:
            response = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&forecast_days=7&timezone=auto"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to fetch 7-day forecast: {e}")
            return None

    def display_weather(self):
        lat, lon, city, region = self.get_user_location()
        if lat is not None and lon is not None:
            weather_data = self.get_weather(lat, lon)
            if weather_data:
                weather_main = weather_data['weather'][0]['main']
                weather_desc = weather_data['weather'][0]['description'].capitalize()
                temp = weather_data['main']['temp']
                self.weather_label.setText(f"Location: {city}, {region}\nWeather: {weather_desc}\nTemperature: {temp}°C")
                self.update_weather_icon(weather_main)
                self.update_background_image(weather_main)
            forecast_data = self.get_7day_forecast(lat, lon)
            self.display_7day_forecast(forecast_data)

    def update_weather_icon(self, weather_condition):
        cond = weather_condition.lower()
        gif_file = "sunny.gif"
        if "cloud" in cond:
            gif_file = "cloudy.gif"
        elif "rain" in cond:
            gif_file = "rainy.gif"
        elif "snow" in cond:
            gif_file = "snowy.gif"
        elif "sun" in cond or "clear" in cond:
            gif_file = "sunny.gif"
        self.weather_icon_label.set_gif(os.path.join(ICON_PATH, gif_file))

    def update_background_image(self, weather_condition):
        background_file = "default.png"
        cond = weather_condition.lower()
        if "cloud" in cond:
            background_file = "cloudy.png"
        elif "rain" in cond:
            background_file = "rainy.png"
        elif "snow" in cond:
            background_file = "snowy.png"
        elif "sun" in cond or "clear" in cond:
            background_file = "sunny.png"
        path = os.path.join(WEATHER_BACKGROUND_PATH, background_file)
        self.update_background(path if os.path.exists(path) else DEFAULT_BACKGROUND_IMAGE)

    def display_7day_forecast(self, forecast_data):
        for i in reversed(range(self.forecast_layout.count())):
            widget = self.forecast_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if not forecast_data or "daily" not in forecast_data:
            self.forecast_layout.addWidget(QtWidgets.QLabel("No forecast data available.", styleSheet="color: white;"))
            return

        daily = forecast_data["daily"]
        days = daily["time"]
        max_temps = daily["temperature_2m_max"]
        min_temps = daily["temperature_2m_min"]
        weathercodes = daily["weathercode"]

        code_map = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
                    51: "Drizzle", 61: "Rain", 71: "Snow", 80: "Rain showers", 85: "Snow showers", 95: "Thunderstorm"}

        for i in range(len(days)):
            date_obj = datetime.strptime(days[i], "%Y-%m-%d")
            day_str = date_obj.strftime("%a")
            max_temp = max_temps[i]
            min_temp = min_temps[i]
            weather_txt = code_map.get(weathercodes[i], "Unknown")

            day_widget = QtWidgets.QWidget()
            vbox = QtWidgets.QVBoxLayout()
            vbox.setAlignment(QtCore.Qt.AlignCenter)
            day_widget.setLayout(vbox)

            day_lbl = QtWidgets.QLabel(day_str)
            day_lbl.setStyleSheet("color: white; font-weight: bold;")
            day_lbl.setAlignment(QtCore.Qt.AlignCenter)
            vbox.addWidget(day_lbl)

            txt_lbl = QtWidgets.QLabel(weather_txt)
            txt_lbl.setStyleSheet("color: white;")
            txt_lbl.setAlignment(QtCore.Qt.AlignCenter)
            vbox.addWidget(txt_lbl)

            temp_lbl = QtWidgets.QLabel(f"{round(max_temp)}°C / {round(min_temp)}°C")
            temp_lbl.setStyleSheet("color: white;")
            temp_lbl.setAlignment(QtCore.Qt.AlignCenter)
            vbox.addWidget(temp_lbl)

            self.forecast_layout.addWidget(day_widget)

        if hasattr(self, 'temp_graph'):
            self.info_content_layout.removeWidget(self.temp_graph)
            self.temp_graph.deleteLater()

        self.temp_graph = TempGraphCanvas(self,
            days=[datetime.strptime(d, "%Y-%m-%d").strftime("%a") for d in days],
            max_temps=max_temps,
            min_temps=min_temps
        )
        self.info_content_layout.addWidget(self.temp_graph)
        self.temp_graph.setVisible(self.toggle_graph_checkbox.isChecked())

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec_())
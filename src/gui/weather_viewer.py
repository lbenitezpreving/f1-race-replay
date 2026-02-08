import sys
import json
import math
import random
from collections import deque
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QStatusBar, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QFont, QPainter, QPen, QColor, QBrush, QRadialGradient, QPalette
from src.services.stream import TelemetryStreamClient

# Matplotlib for graphs
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches

class WeatherRadarWidget(QWidget):
    """
    Custom widget simulating a weather radar.
    Visualizes wind direction/speed and rain intensity.
    """
    def __init__(self):
        super().__init__()
        self.wind_speed = 0.0
        self.wind_direction = 0.0
        self.rain_state = "DRY"
        self.humidity = 0.0
        self.air_temp = 0.0
        self.track_temp = 0.0
        
        # Animation for radar sweep
        self.sweep_angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)  # 20 FPS
        
        # Simulated rain blobs (angle, distance, size, intensity)
        self.rain_blobs = []
        
        self.setStyleSheet("background-color: #0d1117; border-radius: 10px; border: 1px solid #30363d;")

    def update_weather(self, weather_data):
        self.wind_speed = weather_data.get('wind_speed', 0.0)
        self.wind_direction = weather_data.get('wind_direction', 0.0)
        self.rain_state = weather_data.get('rain_state', 'DRY')
        self.humidity = weather_data.get('humidity', 0.0)
        self.air_temp = weather_data.get('air_temp', 0.0)
        self.track_temp = weather_data.get('track_temp', 0.0)
        
        # Update rain simulation
        self._update_rain_blobs()
        self.update()

    def _update_rain_blobs(self):
        # Determine rain intensity factor
        intensity = 0
        if self.rain_state == 'RAINING':
            intensity = 1.0 # Simple ON/OFF for now, logic could be more complex
        
        # Update existing blobs
        # Move them slightly with wind
        # Convert wind dir to rads
        wind_rad = math.radians(self.wind_direction - 90) # Adjust for North=0
        
        # Spawn new blobs if raining
        if intensity > 0 and len(self.rain_blobs) < 20:
             self.rain_blobs.append({
                'angle': random.uniform(0, 360),
                'dist': random.uniform(0.1, 0.9), # normalized distance
                'size': random.uniform(0.1, 0.3),
                'life': 1.0
             })
             
        # Decay blobs
        for blob in self.rain_blobs:
            blob['life'] -= 0.01
            # Move visually with wind (simplified)
            # Just drift them a bit
        
        self.rain_blobs = [b for b in self.rain_blobs if b['life'] > 0]

    def animate(self):
        self.sweep_angle = (self.sweep_angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2
        radius = min(w, h) // 2 - 20
        
        # Background handled by stylesheet, but we draw the radar grid
        
        # 1. Draw Radar Grid
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(Qt.NoBrush)
        
        # Concentric circles
        for r_factor in [0.25, 0.5, 0.75, 1.0]:
            r = int(radius * r_factor)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            
        # Crosshairs
        painter.drawLine(cx - radius, cy, cx + radius, cy)
        painter.drawLine(cx, cy - radius, cx, cy + radius)
        
        # Distance labels
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(cx + int(radius * 0.25) + 2, cy - 2, "15 km")
        painter.drawText(cx + int(radius * 0.5) + 2, cy - 2, "30 km")
        painter.drawText(cx + int(radius * 0.75) + 2, cy - 2, "45 km")
        
        # 2. Draw Simulated Rain
        if self.rain_blobs:
            painter.setPen(Qt.NoPen)
            for blob in self.rain_blobs:
                # Polar to cartesian
                b_angle = math.radians(blob.angle)
                b_dist = blob['dist'] * radius
                bx = cx + b_dist * math.cos(b_angle)
                by = cy + b_dist * math.sin(b_angle)
                b_size = blob['size'] * radius
                
                # Gradient brush for "blob" look
                grad = QRadialGradient(bx, by, b_size)
                # Color based on intensity simulation (Green/Yellow/Red)
                # Randomize slightly for texture
                color = QColor(0, 255, 0, 150) # Light rain (Green)
                if random.random() > 0.7:
                    color = QColor(255, 255, 0, 150) # Yellow
                
                grad.setColorAt(0, color)
                grad.setColorAt(1, QColor(0, 0, 0, 0))
                
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(bx, by), b_size, b_size)

        # 3. Draw Radar Sweep
        sweep_grad = QRadialGradient(cx, cy, radius)
        sweep_grad.setColorAt(0, QColor(0, 255, 0, 0))
        sweep_grad.setColorAt(1, QColor(0, 255, 0, 20)) # Very faint green edge
        
        # Conical gradient for the sweep line is harder in pure Qt without composition modes
        # Simple line for sweep
        painter.setPen(QPen(QColor(0, 255, 0, 100), 2))
        sweep_rad = math.radians(self.sweep_angle - 90)
        sx = cx + radius * math.cos(sweep_rad)
        sy = cy + radius * math.sin(sweep_rad)
        painter.drawLine(cx, cy, int(sx), int(sy))
        
        # 4. Draw Center (Track Location)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(cx - 3, cy - 3, 6, 6)
        
        # 5. Draw Wind Arrow (Overlay)
        if self.wind_speed > 0:
            wind_rad = math.radians(self.wind_direction - 90)
            # Arrow in bottom right/corner or center? 
            # Let's put a wind indicator in the corner
            indicator_radius = 30
            ix = cx + radius - icon_offset if (icon_offset := 40) else 0 
            # Actually, let's draw it from center to show wind flow relative to track
            # Wind vector
            arrow_len = min(radius * 0.8, radius * (self.wind_speed / 20.0)) # Scale
            # Reverse direction because wind comes FROM
            w_dest_x = cx + arrow_len * math.cos(wind_rad + math.pi)
            w_dest_y = cy + arrow_len * math.sin(wind_rad + math.pi)
            
            painter.setPen(QPen(QColor(78, 205, 196), 3))
            painter.drawLine(cx, cy, int(w_dest_x), int(w_dest_y))
            
            # Arrowhead
            arrow_size = 10
            angle_arrow = wind_rad + math.pi
            p1_x = w_dest_x + arrow_size * math.cos(angle_arrow + 2.5)
            p1_y = w_dest_y + arrow_size * math.sin(angle_arrow + 2.5)
            p2_x = w_dest_x + arrow_size * math.cos(angle_arrow - 2.5)
            p2_y = w_dest_y + arrow_size * math.sin(angle_arrow - 2.5)
            painter.drawLine(int(w_dest_x), int(w_dest_y), int(p1_x), int(p1_y))
            painter.drawLine(int(w_dest_x), int(w_dest_y), int(p2_x), int(p2_y))

        # 6. Overlay Text Stats
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        
        # Wind Info
        painter.drawText(20, 30, f"WIND: {self.wind_speed:.1f} m/s")
        painter.setFont(QFont("Arial", 10))
        painter.drawText(20, 50, f"DIR: {self.wind_direction:.0f}°")
        
        # Rain Info
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        rain_color = QColor(52, 152, 219) if self.rain_state == 'RAINING' else QColor(149, 165, 166)
        painter.setPen(rain_color)
        painter.drawText(20, h - 20, f"RAIN: {self.rain_state}")


class TrendGraphWidget(QWidget):
    """
    Widget containing Temperature and Humidity history graphs.
    """
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #0d1117; border-radius: 10px; border: 1px solid #30363d;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create matplotlib figure
        self.figure = Figure(facecolor='#0d1117')
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)
        
        # Setup subplots (2 rows, 1 col)
        gs = self.figure.add_gridspec(2, 1, hspace=0.3)
        self.ax_temp = self.figure.add_subplot(gs[0, 0])
        self.ax_humid = self.figure.add_subplot(gs[1, 0])
        
        # Styling
        for ax in [self.ax_temp, self.ax_humid]:
            ax.set_facecolor('#0d1117')
            ax.tick_params(colors='#8b949e', which='both')
            for spine in ax.spines.values():
                spine.set_color('#30363d')
            ax.grid(True, color='#21262d', linestyle='-', linewidth=0.5)
            
        self.ax_temp.set_title("Temperature History", color='#c9d1d9', fontsize=10, loc='left')
        self.ax_humid.set_title("Humidity History", color='#c9d1d9', fontsize=10, loc='left')

    def update_graphs(self, history):
        if not history:
            return
            
        times = [x['time'] for x in history]
        # Start times from 0 relative to first data point if desired, 
        # or use session time directly. Assuming 'time' is session time.
        
        # Extract data
        track_temps = [x['track_temp'] for x in history]
        air_temps = [x['air_temp'] for x in history]
        humidities = [x['humidity'] for x in history]
        
        # Clear axes
        self.ax_temp.clear()
        self.ax_humid.clear()
        
        # Re-apply styles (clear resets them)
        for ax, title in [(self.ax_temp, "Temperature Evolution"), (self.ax_humid, "Humidity Evolution")]:
            ax.set_facecolor('#0d1117')
            ax.tick_params(colors='#8b949e')
            for spine in ax.spines.values():
                spine.set_color('#30363d')
            ax.grid(True, color='#21262d', linestyle='-', linewidth=0.5)
            ax.set_title(title, color='#c9d1d9', fontsize=10, loc='left')
        
        # Plot Temp
        # Filter Nones
        valid_track = [(t, v) for t, v in zip(times, track_temps) if v is not None]
        valid_air = [(t, v) for t, v in zip(times, air_temps) if v is not None]
        
        if valid_track:
            t, v = zip(*valid_track)
            self.ax_temp.plot(t, v, color='#ff6b6b', label='Track', linewidth=1.5)
            # Fill under curve
            self.ax_temp.fill_between(t, v, min(v)-1, color='#ff6b6b', alpha=0.1)
            
        if valid_air:
            t, v = zip(*valid_air)
            self.ax_temp.plot(t, v, color='#4ecdc4', label='Air', linewidth=1.5)
            
        self.ax_temp.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='#c9d1d9', loc='upper left', fontsize=8)
        
        # Plot Humidity
        valid_humid = [(t, v) for t, v in zip(times, humidities) if v is not None]
        if valid_humid:
            t, v = zip(*valid_humid)
            self.ax_humid.plot(t, v, color='#3498db', label='Humidity', linewidth=1.5)
            self.ax_humid.fill_between(t, v, 0, color='#3498db', alpha=0.1)
            
        self.canvas.draw()


class WeatherViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 Race Replay - Weather Viewer [Conectando...]")
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color: #010409;") # Main window bg
        
        # Data
        self.weather_history = [] # List for full history
        self.current_weather = {}
        
        # Telemetry
        self.client = TelemetryStreamClient()
        self.client.data_received.connect(self.on_data_received)
        self.client.connection_status.connect(self.on_connection_status)
        self.client.error_occurred.connect(self.on_error)
        
        self.setup_ui()
        self.client.start()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 2x2 Grid Layout
        grid = QGridLayout(central_widget)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(10)
        
        # 1. Connection Status Bar (Top, Spanning)
        self.status_bar = QLabel("Inicializando...")
        self.status_bar.setFixedHeight(30)
        self.status_bar.setAlignment(Qt.AlignCenter)
        self.status_bar.setStyleSheet("background-color: #21262d; color: #8b949e; border-radius: 4px; font-weight: bold;")
        # We can put this in the layout or just use it as a header. 
        # Using row 0 for header/status might be cleaner.
        grid.addWidget(self.status_bar, 0, 0, 1, 2)
        
        # 2. Zone 1 (Top-Left): Weather Radar
        self.radar_widget = WeatherRadarWidget()
        grid.addWidget(self.radar_widget, 1, 0)
        
        # 3. Zone 2 (Top-Right): Trend Graphs
        self.graphs_widget = TrendGraphWidget()
        grid.addWidget(self.graphs_widget, 1, 1)
        
        # 4. Zone 3 (Bottom-Left): Placeholder
        self.zone3 = QFrame()
        self.zone3.setStyleSheet("background-color: #0d1117; border-radius: 10px; border: 1px dashed #30363d;")
        label3 = QLabel("ZONE 3 (Reserved)", self.zone3)
        label3.setStyleSheet("color: #30363d; font-size: 20px; font-weight: bold;")
        label3.setAlignment(Qt.AlignCenter)
        layout3 = QVBoxLayout(self.zone3)
        layout3.addWidget(label3)
        grid.addWidget(self.zone3, 2, 0)
        
        # 5. Zone 4 (Bottom-Right): Placeholder
        self.zone4 = QFrame()
        self.zone4.setStyleSheet("background-color: #0d1117; border-radius: 10px; border: 1px dashed #30363d;")
        grid.addWidget(self.zone4, 2, 1)
        
        # Set row/col stretch to enforce 2x2 equal sizing (after header)
        grid.setRowStretch(1, 1) # Top Row
        grid.setRowStretch(2, 1) # Bottom Row
        grid.setColumnStretch(0, 1) # Left Col
        grid.setColumnStretch(1, 1) # Right Col

    def on_data_received(self, data):
        if 'frame' in data and 'weather' in data['frame']:
            weather = data['frame']['weather']
            self.current_weather = weather
            
            # Append to history
            self.weather_history.append({
                'time': data['frame'].get('t', 0),
                'track_temp': weather.get('track_temp'),
                'air_temp': weather.get('air_temp'),
                'humidity': weather.get('humidity'),
                'wind_speed': weather.get('wind_speed'),
                'wind_direction': weather.get('wind_direction'),
                'rain_state': weather.get('rain_state', 'DRY')
            })
            
            # Update Widgets
            self.radar_widget.update_weather(weather)
            self.graphs_widget.update_graphs(self.weather_history)

    def on_connection_status(self, status):
        if status == "Connected":
            self.setWindowTitle("F1 Race Replay - Weather Viewer [ONLINE]")
            self.status_bar.setText("✓ SYSTEM ONLINE - RECEIVING TELEMETRY")
            self.status_bar.setStyleSheet("background-color: #238636; color: white; border-radius: 4px; font-weight: bold;")
        elif status == "Connecting...":
            self.setWindowTitle("F1 Race Replay - Weather Viewer [Connecting...]")
            self.status_bar.setText("⟳ CONNECTING TO TRACK SERVERS...")
            self.status_bar.setStyleSheet("background-color: #9e6a03; color: white; border-radius: 4px; font-weight: bold;")
        else:
            self.setWindowTitle("F1 Race Replay - Weather Viewer [OFFLINE]")
            self.status_bar.setText("⚠ OFFLINE - WAITING FOR SESSION")
            self.status_bar.setStyleSheet("background-color: #da3633; color: white; border-radius: 4px; font-weight: bold;")

    def on_error(self, error_msg):
        print(f"Error: {error_msg}")
        # Could show in status bar briefly, but stick to connection state for now

    def closeEvent(self, event):
        if self.client.isRunning():
            self.client.stop()
            self.client.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Weather Viewer")
    viewer = WeatherViewer()
    viewer.show()
    sys.exit(app.exec())

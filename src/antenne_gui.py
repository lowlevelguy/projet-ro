import math
import sys

import numpy as np
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from antenne import solve_set_covering  # Import the solver logic


class AntennaCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 400)
        self.area_width = 0
        self.area_height = 0
        self.antenna_positions = []  # List of (x, y, antenna_type_index)
        self.antenna_types = []  # List of (radius, price)

    def set_data(self, width, height, positions, antenna_types):
        self.area_width = width
        self.area_height = height
        self.antenna_positions = positions
        self.antenna_types = antenna_types
        self.update()

    def paintEvent(self, event):
        if self.area_width == 0 or self.area_height == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate scaling to fit the canvas with padding
        padding = 40
        available_width = self.width() - 2 * padding
        available_height = self.height() - 2 * padding

        scale_x = available_width / self.area_width
        scale_y = available_height / self.area_height
        scale = min(scale_x, scale_y)

        # Calculate offset to center the drawing
        scaled_width = self.area_width * scale
        scaled_height = self.area_height * scale
        offset_x = (self.width() - scaled_width) / 2
        offset_y = (self.height() - scaled_height) / 2

        # Draw modern styled area rectangle with gradient background
        painter.setPen(QPen(QColor(74, 144, 226), 3))
        painter.setBrush(QColor(20, 20, 40))
        painter.drawRect(
            int(offset_x), int(offset_y), int(scaled_width), int(scaled_height)
        )

        # Define color palette for different antenna types
        colors = [
            (255, 100, 100),  # Red
            (100, 255, 100),  # Green
            (100, 150, 255),  # Blue
            (255, 255, 100),  # Yellow
            (255, 150, 255),  # Magenta
            (100, 255, 255),  # Cyan
            (255, 200, 100),  # Orange
        ]

        # Draw coverage circles and antennas grouped by type
        for pos in self.antenna_positions:
            x, y, antenna_type = pos
            radius, _ = self.antenna_types[antenna_type]

            # Get color for this antenna type
            color = colors[antenna_type % len(colors)]

            # Draw coverage circle
            scaled_x = offset_x + x * scale
            scaled_y = offset_y + y * scale
            scaled_radius = radius * scale

            painter.setPen(QPen(QColor(*color, 80), 1))
            painter.setBrush(QColor(*color, 30))
            painter.drawEllipse(
                int(scaled_x - scaled_radius),
                int(scaled_y - scaled_radius),
                int(scaled_radius * 2),
                int(scaled_radius * 2),
            )

        # Draw antenna positions
        antenna_size = 12

        for pos in self.antenna_positions:
            x, y, antenna_type = pos

            # Get color for this antenna type
            color = colors[antenna_type % len(colors)]

            scaled_x = offset_x + x * scale
            scaled_y = offset_y + y * scale

            # Draw antenna as a triangle (tower shape) using QPolygonF
            painter.setPen(QPen(QColor(*color), 2))
            painter.setBrush(QColor(*color))

            points = [
                QPointF(scaled_x, scaled_y - antenna_size),
                QPointF(scaled_x - antenna_size / 2, scaled_y + antenna_size / 2),
                QPointF(scaled_x + antenna_size / 2, scaled_y + antenna_size / 2),
            ]

            triangle = QPolygonF(points)
            painter.drawPolygon(triangle)

            # Draw a small circle at the center
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(scaled_x - 3), int(scaled_y - 3), 6, 6)

        # Draw legend
        legend_x = 10
        legend_y = 10
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(
            legend_x,
            legend_y,
            300,
            20,
            Qt.AlignmentFlag.AlignLeft,
            f"Area: {self.area_width}m × {self.area_height}m",
        )

        # Count antennas by type
        type_counts = {}
        for _, _, antenna_type in self.antenna_positions:
            type_counts[antenna_type] = type_counts.get(antenna_type, 0) + 1

        y_offset = legend_y + 20
        painter.drawText(
            legend_x,
            y_offset,
            300,
            20,
            Qt.AlignmentFlag.AlignLeft,
            f"Total Antennas: {len(self.antenna_positions)}",
        )

        # Draw antenna type legend
        y_offset += 20
        for antenna_type in sorted(type_counts.keys()):
            if antenna_type < len(self.antenna_types):
                radius, price = self.antenna_types[antenna_type]
                count = type_counts[antenna_type]
                color = colors[antenna_type % len(colors)]

                # Draw colored square
                painter.setBrush(QColor(*color))
                painter.setPen(QPen(QColor(*color), 1))
                painter.drawRect(legend_x, y_offset - 10, 15, 15)

                # Draw text
                painter.setPen(QPen(QColor(200, 200, 200), 1))
                painter.drawText(
                    legend_x + 20,
                    y_offset,
                    300,
                    20,
                    Qt.AlignmentFlag.AlignLeft,
                    f"Type {antenna_type}: {count}x (r={radius}m, ${price})",
                )
                y_offset += 20


class VisualizationWindow(QMainWindow):
    """Separate window for displaying the antenna placement visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Antenna Placement Visualization")
        self.setGeometry(150, 150, 900, 700)

        # Apply same dark theme
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1e, stop:1 #1a1a2e);
            }
        """)

        # Create canvas
        self.canvas = AntennaCanvas()
        self.canvas.setMinimumSize(800, 600)
        self.setCentralWidget(self.canvas)

    def set_data(self, width, height, positions, antenna_types):
        """Update the canvas with new data."""
        self.canvas.set_data(width, height, positions, antenna_types)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Set Covering - Antenna Placement Optimizer")
        self.setGeometry(100, 100, 1000, 700)

        # Apply modern dark theme with improved styling
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1e, stop:1 #1a1a2e);
            }
            QWidget {
                background-color: transparent;
                color: #e8e8f0;
                font-family: 'Segoe UI', 'San Francisco', Arial, sans-serif;
                font-size: 11pt;
            }
            QLabel {
                color: #e8e8f0;
                font-size: 11pt;
            }
            QLineEdit {
                background-color: #252538;
                border: 2px solid #3a3a52;
                border-radius: 8px;
                padding: 10px 14px;
                color: #e8e8f0;
                font-size: 11pt;
                selection-background-color: #4a90e2;
            }
            QLineEdit:focus {
                border: 2px solid #4a90e2;
                background-color: #2a2a3e;
            }
            QLineEdit:hover {
                background-color: #2a2a3e;
                border: 2px solid #4a4a62;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 11pt;
                font-weight: 600;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5aa0f2, stop:1 #4580cd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3570ad, stop:1 #2560a0);
            }
            QPushButton:disabled {
                background: #3a3a52;
                color: #6a6a82;
            }
            QTableWidget {
                background-color: #1e1e32;
                border: 2px solid #2a2a42;
                border-radius: 10px;
                gridline-color: #2a2a42;
                color: #e8e8f0;
                selection-background-color: #4a90e2;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2a2a42;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #252538;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a42, stop:1 #252238);
                color: #a8a8c0;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #4a90e2;
                border-right: 1px solid #2a2a42;
                font-weight: 600;
                font-size: 10pt;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QSplitter::handle {
                background-color: #2a2a42;
                height: 3px;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
        """)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title with subtitle
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setSpacing(5)
        title_layout.setContentsMargins(0, 0, 0, 10)

        title = QLabel("Antenna Placement Optimizer")
        title.setStyleSheet(
            "font-size: 24pt; font-weight: 700; "
            "color: #4a90e2; margin-bottom: 0px; letter-spacing: 1px;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Multi-Type Set Covering with Interference Constraints")
        subtitle.setStyleSheet(
            "font-size: 11pt; font-weight: 400; color: #a8a8c0; "
            "margin-top: 0px; font-style: italic;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        main_layout.addWidget(title_widget)

        # Input section with improved styling
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e32;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setSpacing(20)
        input_layout.setContentsMargins(15, 15, 15, 15)

        # Area width
        width_label = QLabel("Area Width (m):")
        width_label.setStyleSheet("font-weight: 600; color: #a8a8c0;")
        input_layout.addWidget(width_label)
        self.width_input = QLineEdit("500")
        self.width_input.setMaximumWidth(120)
        self.width_input.setPlaceholderText("Width")
        input_layout.addWidget(self.width_input)

        # Area height
        height_label = QLabel("Area Height (m):")
        height_label.setStyleSheet("font-weight: 600; color: #a8a8c0;")
        input_layout.addWidget(height_label)
        self.height_input = QLineEdit("500")
        self.height_input.setMaximumWidth(120)
        self.height_input.setPlaceholderText("Height")
        input_layout.addWidget(self.height_input)

        # Maximum budget
        budget_label = QLabel("💰 Max Budget ($):")
        budget_label.setStyleSheet("font-weight: 600; color: #a8a8c0;")
        input_layout.addWidget(budget_label)
        self.budget_input = QLineEdit("10000")
        self.budget_input.setMaximumWidth(120)
        self.budget_input.setPlaceholderText("Budget")
        input_layout.addWidget(self.budget_input)

        input_layout.addStretch()
        main_layout.addWidget(input_container)

        # Antenna types section
        antenna_types_label = QLabel("🎛️ Available Antenna Types")
        antenna_types_label.setStyleSheet(
            "font-size: 14pt; font-weight: 700; color: #4a90e2; "
            "margin-top: 15px; margin-bottom: 5px;"
        )
        main_layout.addWidget(antenna_types_label)

        # Antenna types table
        self.antenna_types_table = QTableWidget()
        self.antenna_types_table.setColumnCount(3)
        self.antenna_types_table.setHorizontalHeaderLabels(
            ["Type #", "Coverage Radius (m)", "Price ($)"]
        )
        self.antenna_types_table.horizontalHeader().setStretchLastSection(True)
        self.antenna_types_table.setMinimumHeight(200)
        self.antenna_types_table.setMaximumHeight(300)

        # Add default antenna types
        self.set_default_antenna_types()
        main_layout.addWidget(self.antenna_types_table)

        # Buttons for antenna types with improved styling
        antenna_buttons_widget = QWidget()
        antenna_buttons_layout = QHBoxLayout(antenna_buttons_widget)
        antenna_buttons_layout.setSpacing(10)

        add_antenna_btn = QPushButton("➕ Add Antenna Type")
        add_antenna_btn.clicked.connect(self.add_antenna_type)
        add_antenna_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ecc71, stop:1 #27ae60);
            }
        """)
        antenna_buttons_layout.addWidget(add_antenna_btn)

        remove_antenna_btn = QPushButton("➖ Remove Selected")
        remove_antenna_btn.clicked.connect(self.remove_antenna_type)
        remove_antenna_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ec7063, stop:1 #e74c3c);
            }
        """)
        antenna_buttons_layout.addWidget(remove_antenna_btn)

        antenna_buttons_layout.addStretch()
        main_layout.addWidget(antenna_buttons_widget)

        # Calculate button with enhanced styling
        self.calc_button = QPushButton("Calculate Optimal Placement")
        self.calc_button.clicked.connect(self.calculate_placement)
        self.calc_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                font-size: 14pt;
                padding: 16px;
                margin-top: 15px;
                margin-bottom: 10px;
                font-weight: 700;
                border-radius: 10px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7b8ffb, stop:1 #8a5cb3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #653a91);
            }
        """)
        main_layout.addWidget(self.calc_button)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Antenna #", "X Position (m)", "Y Position (m)", "Type", "Price ($)"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(300)
        main_layout.addWidget(self.table)

        # Initialize visualization window as None
        self.visualization_window = None

    def set_default_antenna_types(self):
        """Set default antenna types in the table."""
        default_types = [
            (50, 100),  # Type 0: 50m radius, $100
            (80, 250),  # Type 1: 80m radius, $250
            (100, 500),  # Type 2: 100m radius, $500
        ]

        self.antenna_types_table.setRowCount(len(default_types))
        for i, (radius, price) in enumerate(default_types):
            self.antenna_types_table.setItem(i, 0, QTableWidgetItem(f"Type {i}"))
            self.antenna_types_table.setItem(i, 1, QTableWidgetItem(str(radius)))
            self.antenna_types_table.setItem(i, 2, QTableWidgetItem(str(price)))

            for col in range(3):
                item = self.antenna_types_table.item(i, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def add_antenna_type(self):
        """Add a new row to the antenna types table."""
        row_count = self.antenna_types_table.rowCount()
        self.antenna_types_table.insertRow(row_count)

        # Set default values
        self.antenna_types_table.setItem(
            row_count, 0, QTableWidgetItem(f"Type {row_count}")
        )
        self.antenna_types_table.setItem(row_count, 1, QTableWidgetItem("20"))
        self.antenna_types_table.setItem(row_count, 2, QTableWidgetItem("200"))

        for col in range(3):
            item = self.antenna_types_table.item(row_count, col)
            if item:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def remove_antenna_type(self):
        """Remove selected row from the antenna types table."""
        current_row = self.antenna_types_table.currentRow()
        if current_row >= 0:
            self.antenna_types_table.removeRow(current_row)

    def calculate_placement(self):
        try:
            # Get input values
            width = float(self.width_input.text())
            height = float(self.height_input.text())
            max_budget = float(self.budget_input.text())

            if width <= 0 or height <= 0 or max_budget <= 0:
                QMessageBox.warning(
                    self, "Invalid Input", "All values must be positive numbers!"
                )
                return

            # Get antenna types from table
            antenna_types = []
            for i in range(self.antenna_types_table.rowCount()):
                try:
                    radius = float(self.antenna_types_table.item(i, 1).text())
                    price = float(self.antenna_types_table.item(i, 2).text())
                    if radius <= 0 or price <= 0:
                        QMessageBox.warning(
                            self,
                            "Invalid Input",
                            f"Antenna type {i}: radius and price must be positive!",
                        )
                        return
                    antenna_types.append((radius, price))
                except (ValueError, AttributeError):
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        f"Antenna type {i}: please enter valid numbers!",
                    )
                    return

            if not antenna_types:
                QMessageBox.warning(
                    self, "Invalid Input", "Please add at least one antenna type!"
                )
                return

            # Solve the set covering problem
            positions = solve_set_covering(width, height, antenna_types, max_budget)

            if not positions:
                QMessageBox.warning(
                    self,
                    "No Solution",
                    "No feasible solution found! Try increasing the budget or adjusting antenna types.",
                )
                return

            # Calculate total cost
            total_cost = sum(antenna_types[a][1] for _, _, a in positions)

            # Create and show visualization window
            if (
                self.visualization_window is None
                or not self.visualization_window.isVisible()
            ):
                self.visualization_window = VisualizationWindow(self)

            self.visualization_window.set_data(width, height, positions, antenna_types)
            self.visualization_window.show()
            self.visualization_window.raise_()
            self.visualization_window.activateWindow()

            # Update table
            self.update_table(positions, antenna_types)

            # Count antennas by type
            type_counts = {}
            for _, _, antenna_type in positions:
                type_counts[antenna_type] = type_counts.get(antenna_type, 0) + 1

            summary = f"Optimal placement found!\n"
            summary += f"Total antennas: {len(positions)}\n"
            summary += f"Total cost: ${total_cost:.2f} / ${max_budget:.2f}\n\n"
            summary += "Breakdown by type:\n"
            for antenna_type in sorted(type_counts.keys()):
                radius, price = antenna_types[antenna_type]
                count = type_counts[antenna_type]
                summary += (
                    f"  Type {antenna_type}: {count}x (r={radius}m, ${price} each)\n"
                )
            summary += f"\n✨ Visualization window opened!"

            QMessageBox.information(self, "Success", summary)

        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def update_table(self, positions, antenna_types):
        self.table.setRowCount(len(positions))

        for i, (x, y, antenna_type) in enumerate(positions):
            _, price = antenna_types[antenna_type]
            self.table.setItem(i, 0, QTableWidgetItem(f"Antenna {i + 1}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{x:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{y:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"Type {antenna_type}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{price:.2f}"))

        # Center align all cells
        for row in range(len(positions)):
            for col in range(5):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

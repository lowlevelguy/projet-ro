import sys
import numpy as np
import gurobipy as gp
from gurobipy import GRB
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                             QLabel, QSpinBox, QDoubleSpinBox, QGroupBox, QSplitter,
                             QHeaderView, QMessageBox, QTabWidget, QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon

from affect_students import affect_interns

class OptimizationThread(QThread):
    finished = pyqtSignal(object, float, int)
    error = pyqtSignal(str)
    
    def __init__(self, students, internships, capacities):
        super().__init__()
        self.students = students
        self.internships = internships
        self.capacities = capacities
    
    def run(self):
        try:
            result, obj_val, status = affect_interns(self.students, self.internships, self.capacities)
            self.finished.emit(result, obj_val, status)
        except Exception as e:
            self.error.emit(str(e))


class ModernTableWidget(QTableWidget):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0d7377;
                color: white;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 8px;
                border: none;
                border-right: 1px solid #3a3a3a;
                border-bottom: 1px solid #3a3a3a;
                font-weight: bold;
            }
        """)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


class AffectStudentsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.num_skills = 3
        self.skill_names = ["Embedded Prog", "Web Dev", "Data Science"]
        self.students_data = []
        self.internships_data = []
        self.results = None
        self.init_ui()
        self.add_sample_data()

    def init_ui(self):
        self.setWindowTitle("Internship Assignment Optimizer - PLNE Solver")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Internship Assignment Optimization System")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet("color: #14ffec; margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #1e1e1e;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
                color: white;
            }
        """)
        main_layout.addWidget(tabs)
        
        # Tab 1: Data Input
        input_tab = QWidget()
        input_layout = QVBoxLayout(input_tab)
        input_layout.setSpacing(15)
        
        # Skills configuration
        skills_group = QGroupBox("Skills Configuration")
        skills_group.setStyleSheet(self.get_group_style())
        skills_layout = QHBoxLayout()
        skills_layout.addWidget(QLabel("Number of Skills:"))
        self.num_skills_spin = QSpinBox()
        self.num_skills_spin.setRange(1, 10)
        self.num_skills_spin.setValue(self.num_skills)
        self.num_skills_spin.valueChanged.connect(self.update_skill_count)
        skills_layout.addWidget(self.num_skills_spin)
        skills_layout.addStretch()
        skills_group.setLayout(skills_layout)
        input_layout.addWidget(skills_group)
        
        # Splitter for students and internships
        splitter = QSplitter(Qt.Horizontal)
        
        # Students section
        students_widget = QWidget()
        students_layout = QVBoxLayout(students_widget)
        students_layout.setContentsMargins(0, 0, 0, 0)
        
        students_header = QHBoxLayout()
        students_label = QLabel("Students")
        students_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        students_label.setStyleSheet("color: #14ffec;")
        students_header.addWidget(students_label)
        students_header.addStretch()
        
        add_student_btn = QPushButton("Add Student")
        add_student_btn.setStyleSheet(self.get_button_style())
        add_student_btn.clicked.connect(self.add_student)
        students_header.addWidget(add_student_btn)
        
        remove_student_btn = QPushButton("Remove")
        remove_student_btn.setStyleSheet(self.get_button_style("#d32f2f"))
        remove_student_btn.clicked.connect(self.remove_student)
        students_header.addWidget(remove_student_btn)
        
        students_layout.addLayout(students_header)
        
        self.students_table = ModernTableWidget(0, self.num_skills + 1)
        self.update_students_table_headers()
        students_layout.addWidget(self.students_table)
        
        splitter.addWidget(students_widget)
        
        # Internships section
        internships_widget = QWidget()
        internships_layout = QVBoxLayout(internships_widget)
        internships_layout.setContentsMargins(0, 0, 0, 0)
        
        internships_header = QHBoxLayout()
        internships_label = QLabel("Internships")
        internships_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        internships_label.setStyleSheet("color: #14ffec;")
        internships_header.addWidget(internships_label)
        internships_header.addStretch()
        
        add_internship_btn = QPushButton("Add Internship")
        add_internship_btn.setStyleSheet(self.get_button_style())
        add_internship_btn.clicked.connect(self.add_internship)
        internships_header.addWidget(add_internship_btn)
        
        remove_internship_btn = QPushButton("Remove")
        remove_internship_btn.setStyleSheet(self.get_button_style("#d32f2f"))
        remove_internship_btn.clicked.connect(self.remove_internship)
        internships_header.addWidget(remove_internship_btn)
        
        internships_layout.addLayout(internships_header)
        
        self.internships_table = ModernTableWidget(0, self.num_skills + 2)
        self.update_internships_table_headers()
        internships_layout.addWidget(self.internships_table)
        
        splitter.addWidget(internships_widget)
        splitter.setSizes([700, 700])
        
        input_layout.addWidget(splitter)
        tabs.addTab(input_tab, "Data Input")
        
        # Tab 2: Results
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        results_header = QLabel("Assignment Results")
        results_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        results_header.setStyleSheet("color: #14ffec;")
        results_layout.addWidget(results_header)
        
        self.results_table = ModernTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Student", "Assigned Internship", "Mismatch Score"])
        results_layout.addWidget(self.results_table)
        
        stats_group = QGroupBox("Statistics")
        stats_group.setStyleSheet(self.get_group_style())
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        results_layout.addWidget(stats_group)
        
        tabs.addTab(results_tab, "Results")
        
        # Tab 3: Matrix View
        matrix_tab = QWidget()
        matrix_layout = QVBoxLayout(matrix_tab)
        
        matrix_header = QLabel("Assignment Matrix")
        matrix_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        matrix_header.setStyleSheet("color: #14ffec;")
        matrix_layout.addWidget(matrix_header)
        
        self.matrix_table = ModernTableWidget(0, 0)
        matrix_layout.addWidget(self.matrix_table)
        
        tabs.addTab(matrix_tab, "Matrix")
        
        # Control panel
        control_group = QGroupBox("Control Panel")
        control_group.setStyleSheet(self.get_group_style())
        control_layout = QHBoxLayout()
        
        self.optimize_btn = QPushButton("Run Optimization")
        self.optimize_btn.setStyleSheet(self.get_button_style("#0d7377", 14))
        self.optimize_btn.clicked.connect(self.run_optimization)
        self.optimize_btn.setMinimumHeight(50)
        control_layout.addWidget(self.optimize_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #1e1e1e;
                text-align: center;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #0d7377;
                border-radius: 3px;
            }
        """)
        control_layout.addWidget(self.progress_bar)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(self.get_button_style("#d32f2f", 12))
        clear_btn.clicked.connect(self.clear_all)
        clear_btn.setMaximumWidth(150)
        control_layout.addWidget(clear_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Status bar
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
        """)
        self.statusBar().showMessage("Ready")

    def apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
        palette.setColor(QPalette.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.Text, QColor(224, 224, 224))
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
        self.setPalette(palette)

    def get_group_style(self):
        return """
            QGroupBox {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #14ffec;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    def get_button_style(self, bg_color="#0d7377", font_size=11):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: {font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(bg_color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(bg_color, 20)};
            }}
            QPushButton:disabled {{
                background-color: #3a3a3a;
                color: #6a6a6a;
            }}
        """

    def lighten_color(self, hex_color, percent):
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        l = min(255, l + int(255 * percent / 100))
        color.setHsl(h, s, l, a)
        return color.name()

    def darken_color(self, hex_color, percent):
        color = QColor(hex_color)
        h, s, l, a = color.getHsl()
        l = max(0, l - int(255 * percent / 100))
        color.setHsl(h, s, l, a)
        return color.name()

    def update_skill_count(self, value):
        self.num_skills = value
        self.update_students_table_headers()
        self.update_internships_table_headers()
        
    def update_students_table_headers(self):
        headers = ["Name"] + [f"Skill {i+1}" for i in range(self.num_skills)]
        self.students_table.setColumnCount(len(headers))
        self.students_table.setHorizontalHeaderLabels(headers)
        
    def update_internships_table_headers(self):
        headers = ["Name"] + [f"Skill {i+1}" for i in range(self.num_skills)] + ["Capacity"]
        self.internships_table.setColumnCount(len(headers))
        self.internships_table.setHorizontalHeaderLabels(headers)

    def add_student(self):
        row = self.students_table.rowCount()
        self.students_table.insertRow(row)
        self.students_table.setItem(row, 0, QTableWidgetItem(f"Student {row+1}"))
        for col in range(1, self.num_skills + 1):
            spin = QDoubleSpinBox()
            spin.setRange(0, 10)
            spin.setValue(np.random.uniform(1, 5))
            spin.setStyleSheet("""
                QDoubleSpinBox {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 3px;
                }
            """)
            self.students_table.setCellWidget(row, col, spin)

    def remove_student(self):
        row = self.students_table.currentRow()
        if row >= 0:
            self.students_table.removeRow(row)

    def add_internship(self):
        row = self.internships_table.rowCount()
        self.internships_table.insertRow(row)
        self.internships_table.setItem(row, 0, QTableWidgetItem(f"Internship {row+1}"))
        for col in range(1, self.num_skills + 1):
            spin = QDoubleSpinBox()
            spin.setRange(0, 10)
            spin.setValue(np.random.uniform(1, 5))
            spin.setStyleSheet("""
                QDoubleSpinBox {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 3px;
                }
            """)
            self.internships_table.setCellWidget(row, col, spin)
        
        cap_spin = QSpinBox()
        cap_spin.setRange(1, 100)
        cap_spin.setValue(2)
        cap_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        self.internships_table.setCellWidget(row, self.num_skills + 1, cap_spin)

    def remove_internship(self):
        row = self.internships_table.currentRow()
        if row >= 0:
            self.internships_table.removeRow(row)

    def add_sample_data(self):
        # Add 5 students
        for _ in range(5):
            self.add_student()
        
        # Add 3 internships
        for _ in range(3):
            self.add_internship()

    def get_students_data(self):
        students = []
        for row in range(self.students_table.rowCount()):
            skills = []
            for col in range(1, self.num_skills + 1):
                widget = self.students_table.cellWidget(row, col)
                skills.append(widget.value())
            students.append(skills)
        return np.array(students)

    def get_internships_data(self):
        internships = []
        capacities = []
        for row in range(self.internships_table.rowCount()):
            skills = []
            for col in range(1, self.num_skills + 1):
                widget = self.internships_table.cellWidget(row, col)
                skills.append(widget.value())
            internships.append(skills)
            
            cap_widget = self.internships_table.cellWidget(row, self.num_skills + 1)
            capacities.append(cap_widget.value())
        return np.array(internships), np.array(capacities)

    def run_optimization(self):
        if self.students_table.rowCount() == 0 or self.internships_table.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "Please add students and internships first!")
            return
        
        students = self.get_students_data()
        internships, capacities = self.get_internships_data()
        
        self.optimize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.statusBar().showMessage("Optimizing...")
        
        self.optimization_thread = OptimizationThread(students, internships, capacities)
        self.optimization_thread.finished.connect(self.optimization_finished)
        self.optimization_thread.error.connect(self.optimization_error)
        self.optimization_thread.start()

    def optimization_finished(self, result, obj_val, status):
        self.results = result
        self.optimize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Optimization completed!")
        
        self.display_results()
        self.display_matrix()
        
        QMessageBox.information(self, "Success", 
                               f"Optimization completed!\nStatus: {'OPTIMAL' if status == GRB.OPTIMAL else 'TIME_LIMIT'}\nObjective Value: {obj_val:.2f}")

    def optimization_error(self, error_msg):
        self.optimize_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("Optimization failed!")
        QMessageBox.critical(self, "Error", f"Optimization failed:\n{error_msg}")

    def display_results(self):
        if self.results is None:
            return
        
        students = self.get_students_data()
        internships, _ = self.get_internships_data()
        
        self.results_table.setRowCount(0)
        
        assigned_count = 0
        total_mismatch = 0
        
        for i in range(len(students)):
            student_name = self.students_table.item(i, 0).text()
            assigned_j = None
            
            for j in range(len(internships)):
                if self.results[i, j] > 0.5:
                    assigned_j = j
                    break
            
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(student_name))
            
            if assigned_j is not None:
                internship_name = self.internships_table.item(assigned_j, 0).text()
                mismatch = np.sum((students[i] - internships[assigned_j]) ** 2)
                self.results_table.setItem(row, 1, QTableWidgetItem(internship_name))
                self.results_table.setItem(row, 2, QTableWidgetItem(f"{mismatch:.2f}"))
                assigned_count += 1
                total_mismatch += mismatch
            else:
                self.results_table.setItem(row, 1, QTableWidgetItem("Not Assigned"))
                self.results_table.setItem(row, 2, QTableWidgetItem("N/A"))
        
        # Update statistics
        avg_mismatch = total_mismatch / assigned_count if assigned_count > 0 else 0
        assignment_rate = (assigned_count / len(students)) * 100
        
        stats = f"""
╔══════════════════════════════════════╗
║        OPTIMIZATION STATISTICS       ║
╠══════════════════════════════════════╣
║ Total Students:      {len(students):>4}            ║
║ Total Internships:   {len(internships):>4}            ║
║ Students Assigned:   {assigned_count:>4}            ║
║ Assignment Rate:     {assignment_rate:>5.1f}%          ║
║ Avg Mismatch:        {avg_mismatch:>6.2f}          ║
╚══════════════════════════════════════╝
        """
        self.stats_text.setText(stats)

    def display_matrix(self):
        if self.results is None:
            return
        
        n, m = self.results.shape
        self.matrix_table.setRowCount(n)
        self.matrix_table.setColumnCount(m)
        
        # Set headers
        row_headers = [self.students_table.item(i, 0).text() for i in range(n)]
        col_headers = [self.internships_table.item(j, 0).text() for j in range(m)]
        self.matrix_table.setVerticalHeaderLabels(row_headers)
        self.matrix_table.setHorizontalHeaderLabels(col_headers)
        
        # Fill matrix
        for i in range(n):
            for j in range(m):
                value = int(self.results[i, j])
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                if value == 1:
                    item.setBackground(QColor("#0d7377"))
                self.matrix_table.setItem(i, j, item)

    def clear_all(self):
        reply = QMessageBox.question(self, "Confirm", 
                                    "Are you sure you want to clear all data?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.students_table.setRowCount(0)
            self.internships_table.setRowCount(0)
            self.results_table.setRowCount(0)
            self.matrix_table.setRowCount(0)
            self.matrix_table.setColumnCount(0)
            self.stats_text.clear()
            self.results = None
            self.statusBar().showMessage("All data cleared")

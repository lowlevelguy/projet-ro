import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QTabWidget, QGroupBox,
                             QMessageBox, QProgressBar, QHeaderView, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from facility_location import FacilityLocationSolver, DemandPoint, FacilityConstraints
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class SolverThread(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, locations, demand_points, constraints):
        super().__init__()
        self.locations = locations
        self.demand_points = demand_points
        self.constraints = constraints
    
    def run(self):
        try:
            solver = FacilityLocationSolver(self.locations, self.demand_points, 
                                           self.constraints)
            solution = solver.solve()
            self.finished.emit(solution)
        except Exception as e:
            import traceback
            self.finished.emit({
                "status": "error", 
                "message": f"{str(e)}\n\n{traceback.format_exc()}"
            })


class MapCanvas(FigureCanvas):
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 8))
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
    
    def plot_solution(self, locations, demand_points, solution):
        self.fig.clear()
        self.axes = self.fig.add_subplot(111)
        
        import numpy as np
        
        opened_facs = solution.get('opened_facilities', [])
        if not opened_facs:
            return
        
        side_length = 100
        grid_res = 50
        x_range = np.linspace(0, side_length, grid_res)
        y_range = np.linspace(0, side_length, grid_res)
        X, Y = np.meshgrid(x_range, y_range)
        
        Z = np.zeros_like(X)
        for i in range(grid_res):
            for j in range(grid_res):
                min_dist = float('inf')
                for fac in opened_facs:
                    dist = np.sqrt((X[i,j] - fac['x'])**2 + (Y[i,j] - fac['y'])**2)
                    min_dist = min(min_dist, dist)
                Z[i,j] = min_dist
        
        self.axes.contourf(X, Y, Z, levels=15, cmap='RdYlGn_r', alpha=0.6)
        self.fig.colorbar(self.axes.collections[0], ax=self.axes, label='Distance to nearest facility (km)')
        
        special_demands = [dp for dp in demand_points if dp.demand_multiplier > 1.0]
        
        for dp in special_demands:
            size = 100 * dp.demand_multiplier
            self.axes.scatter(dp.x, dp.y, c='orange', s=size, alpha=0.8, 
                            marker='o', edgecolors='black', linewidth=2, zorder=5)
            self.axes.annotate(dp.name, (dp.x, dp.y), fontsize=8, 
                             xytext=(0, 0), textcoords='offset points',
                             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='none', alpha=0.8),
                             ha='center', va='center', zorder=15)
        
        for fac in opened_facs:
            self.axes.scatter(fac['x'], fac['y'], c='darkblue', s=500, 
                            marker='H', edgecolors='black', linewidth=2,
                            zorder=10)
            self.axes.annotate(fac['name'], (fac['x'], fac['y']), 
                             fontsize=10, fontweight='bold',
                             xytext=(0, -20), textcoords='offset points',
                             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='none', alpha=0.8),
                             ha='center', va='top', zorder=15)
        
        self.axes.set_xlabel('X (km)', fontsize=12)
        self.axes.set_ylabel('Y (km)', fontsize=12)
        self.axes.set_title('Distance Field to Nearest Facility', fontsize=14, fontweight='bold')
        self.axes.grid(True, alpha=0.3)
        
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='orange', label='High-demand zones'),
            Patch(facecolor='darkblue', label='Opened facilities')
        ]
        self.axes.legend(handles=legend_elements, loc='upper right', fontsize=9)
        
        self.fig.tight_layout()
        self.draw()


class FacilityLocationGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.demand_points = []
        self.constraints = None
        self.solution = None
        self.solver_thread = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Facility Location Optimization")
        self.showMaximized()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        self.input_tab = self.create_input_tab()
        self.tabs.addTab(self.input_tab, "Input Data")
        
        self.results_tab = self.create_results_tab()
        self.tabs.addTab(self.results_tab, "Results")
        
        self.viz_tab = self.create_visualization_tab()
        self.tabs.addTab(self.viz_tab, "Map")
        
        button_layout = QHBoxLayout()
        
        self.solve_btn = QPushButton("Solve")
        self.solve_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.solve_btn.clicked.connect(self.solve_problem)
        button_layout.addWidget(self.solve_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 14px; padding: 10px;")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.load_default_data()
    
    def create_input_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        constraints_group = QGroupBox("Global Constraints")
        constraints_layout = QGridLayout()
        
        constraints_layout.addWidget(QLabel("Number of facilities:"), 0, 0)
        self.num_fac_spin = QSpinBox()
        self.num_fac_spin.setRange(1, 50)
        self.num_fac_spin.setValue(4)
        constraints_layout.addWidget(self.num_fac_spin, 0, 1)
        
        constraints_layout.addWidget(QLabel("Total area (km²):"), 1, 0)
        self.total_area_spin = QDoubleSpinBox()
        self.total_area_spin.setRange(0, 100000)
        self.total_area_spin.setValue(10000)
        self.total_area_spin.setDecimals(0)
        constraints_layout.addWidget(self.total_area_spin, 1, 1)
        
        constraints_layout.addWidget(QLabel("Travel cost per km (€):"), 2, 0)
        self.travel_cost_spin = QDoubleSpinBox()
        self.travel_cost_spin.setRange(0, 1000)
        self.travel_cost_spin.setValue(2)
        self.travel_cost_spin.setDecimals(2)
        constraints_layout.addWidget(self.travel_cost_spin, 2, 1)
        
        constraints_layout.addWidget(QLabel("Grid density:"), 3, 0)
        self.grid_density_spin = QSpinBox()
        self.grid_density_spin.setRange(3, 20)
        self.grid_density_spin.setValue(6)
        self.grid_density_spin.setToolTip("Number of grid points per side (e.g., 6 = 6x6 = 36 potential locations)")
        constraints_layout.addWidget(self.grid_density_spin, 3, 1)
        
        constraints_layout.addWidget(QLabel("Base annual visits:"), 4, 0)
        self.base_annual_visits_spin = QSpinBox()
        self.base_annual_visits_spin.setRange(1, 10000)
        self.base_annual_visits_spin.setValue(50)
        self.base_annual_visits_spin.setToolTip("Base number of annual visits per zone")
        constraints_layout.addWidget(self.base_annual_visits_spin, 4, 1)
        
        constraints_group.setLayout(constraints_layout)
        layout.addWidget(constraints_group)
        
        demand_group = QGroupBox("Demand Points")
        demand_layout = QVBoxLayout()
        
        self.demand_table = QTableWidget()
        self.demand_table.setColumnCount(4)
        self.demand_table.setHorizontalHeaderLabels([
            "Name", "X (km)", "Y (km)", "Demand Multiplier"
        ])
        self.demand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        demand_layout.addWidget(self.demand_table)
        
        dem_btn_layout = QHBoxLayout()
        add_dem_btn = QPushButton("Add Demand Point")
        add_dem_btn.clicked.connect(self.add_demand_row)
        dem_btn_layout.addWidget(add_dem_btn)
        
        remove_dem_btn = QPushButton("Remove Selected")
        remove_dem_btn.clicked.connect(lambda: self.remove_selected_row(self.demand_table))
        dem_btn_layout.addWidget(remove_dem_btn)
        
        demand_layout.addLayout(dem_btn_layout)
        demand_group.setLayout(demand_layout)
        layout.addWidget(demand_group)
        
        return tab
    
    def create_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.results_text)
        
        facilities_group = QGroupBox("Opened Facilities")
        facilities_layout = QVBoxLayout()
        
        self.facilities_table = QTableWidget()
        self.facilities_table.setColumnCount(3)
        self.facilities_table.setHorizontalHeaderLabels([
            "Name", "Position (X, Y)", "Service Area"
        ])
        self.facilities_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        facilities_layout.addWidget(self.facilities_table)
        
        facilities_group.setLayout(facilities_layout)
        layout.addWidget(facilities_group)
        
        assignments_group = QGroupBox("Assignments")
        assignments_layout = QVBoxLayout()
        
        self.assignments_table = QTableWidget()
        self.assignments_table.setColumnCount(4)
        self.assignments_table.setHorizontalHeaderLabels([
            "Demand Point", "Multiplier", "Facility", "Distance (km)"
        ])
        self.assignments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        assignments_layout.addWidget(self.assignments_table)
        
        assignments_group.setLayout(assignments_layout)
        layout.addWidget(assignments_group)
        
        return tab
    
    def create_visualization_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.map_canvas = MapCanvas(tab)
        layout.addWidget(self.map_canvas)
        
        return tab
    
    def add_demand_row(self):
        row = self.demand_table.rowCount()
        self.demand_table.insertRow(row)
        
        self.demand_table.setItem(row, 0, QTableWidgetItem(f"Zone_{row+1}"))
        self.demand_table.setItem(row, 1, QTableWidgetItem("0"))
        self.demand_table.setItem(row, 2, QTableWidgetItem("0"))
        self.demand_table.setItem(row, 3, QTableWidgetItem("10"))
    
    def remove_selected_row(self, table):
        selected_rows = set(index.row() for index in table.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            table.removeRow(row)
    
    def load_default_data(self):
        default_demands = [
            ("Zone_A", 30, 40, 20),
            ("Zone_B", 70, 35, 15)
        ]
        
        for dem_data in default_demands:
            row = self.demand_table.rowCount()
            self.demand_table.insertRow(row)
            for col, value in enumerate(dem_data):
                self.demand_table.setItem(row, col, QTableWidgetItem(str(value)))
    
    def collect_data(self):
        demand_points = []
        for row in range(self.demand_table.rowCount()):
            name = self.demand_table.item(row, 0).text()
            x = float(self.demand_table.item(row, 1).text())
            y = float(self.demand_table.item(row, 2).text())
            multiplier = float(self.demand_table.item(row, 3).text())
            
            demand_points.append(DemandPoint(
                id=row, name=name, x=x, y=y, 
                demand_multiplier=multiplier
            ))
        
        constraints = FacilityConstraints(
            num_facilities=self.num_fac_spin.value(),
            total_area=self.total_area_spin.value(),
            travel_cost_per_km=self.travel_cost_spin.value(),
            grid_density=self.grid_density_spin.value(),
            base_annual_visits=self.base_annual_visits_spin.value()
        )
        
        return demand_points, constraints
    
    def solve_problem(self):
        try:
            self.demand_points, self.constraints = self.collect_data()
            
            if not self.demand_points:
                QMessageBox.warning(self, "Error", "Add at least one demand point")
                return
            
            self.solve_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Optimizing...")
            
            self.solver_thread = SolverThread(
                [], self.demand_points, 
                self.constraints
            )
            self.solver_thread.finished.connect(self.on_solve_finished)
            self.solver_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")
            self.solve_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def on_solve_finished(self, solution):
        self.solve_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if solution['status'] == 'error':
            self.status_label.setText("Error")
            QMessageBox.critical(self, "Error", solution['message'])
            return
        
        if solution['status'] == 'infeasible':
            self.status_label.setText("No solution found")
            QMessageBox.warning(self, "Infeasible", solution['message'])
            return
        
        self.solution = solution
        self.status_label.setText(f"Solution found in {solution['solve_time']:.2f}s")
        
        self.display_results()
        self.tabs.setCurrentIndex(1)
    
    def display_results(self):
        sol = self.solution
        
        text = f"Status: {sol['status'].upper()}\n\n"
        text += f"Total travel cost: {sol['total_travel_cost']:,.2f} €\n"
        text += f"Facilities opened: {sol['num_facilities']}\n"
        text += f"Average distance: {sol['avg_distance']:.2f} km\n"
        text += f"Solve time: {sol['solve_time']:.2f}s\n\n"
        
        text += "Opened Facilities:\n"
        for fac in sol['opened_facilities']:
            text += f"  {fac['name']} at ({fac['x']:.1f}, {fac['y']:.1f})\n"
        
        self.results_text.setText(text)
        
        self.facilities_table.setRowCount(0)
        for fac in sol['opened_facilities']:
            row = self.facilities_table.rowCount()
            self.facilities_table.insertRow(row)
            
            self.facilities_table.setItem(row, 0, QTableWidgetItem(fac['name']))
            self.facilities_table.setItem(row, 1, QTableWidgetItem(f"({fac['x']:.1f}, {fac['y']:.1f})"))
            
            num_served = sum(1 for a in sol['assignments'] if a['facility'] == fac['name'])
            self.facilities_table.setItem(row, 2, QTableWidgetItem(f"{num_served} zones"))
        
        self.assignments_table.setRowCount(0)
        for assign in sol['assignments']:
            row = self.assignments_table.rowCount()
            self.assignments_table.insertRow(row)
            self.assignments_table.setItem(row, 0, QTableWidgetItem(assign['demand_point']))
            self.assignments_table.setItem(row, 1, QTableWidgetItem(f"{assign['multiplier']:.1f}"))
            self.assignments_table.setItem(row, 2, QTableWidgetItem(assign['facility']))
            self.assignments_table.setItem(row, 3, QTableWidgetItem(f"{assign['distance']:.2f}"))
        
        self.map_canvas.plot_solution([], self.demand_points, sol)
    
    def clear_all(self):
        self.demand_table.setRowCount(0)
        self.facilities_table.setRowCount(0)
        self.assignments_table.setRowCount(0)
        self.results_text.clear()
        self.solution = None
        self.status_label.setText("Ready")
        self.map_canvas.fig.clear()
        self.map_canvas.axes = self.map_canvas.fig.add_subplot(111)
        self.map_canvas.draw()


def main():
    app = QApplication(sys.argv)
    window = FacilityLocationGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

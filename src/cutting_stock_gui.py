import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
                             QComboBox, QTextEdit, QTabWidget, QGroupBox,
                             QMessageBox, QProgressBar, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from cutting_stock import CuttingStockSolver, Piece, PlateType



class SolverThread(QThread):
    """Thread pour exécuter le solveur sans bloquer l'interface"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    
    def __init__(self, pieces, plates, allow_rotation, time_limit):
        super().__init__()
        self.pieces = pieces
        self.plates = plates
        self.allow_rotation = allow_rotation
        self.time_limit = time_limit
    
    def run(self):
        try:
            self.progress.emit("Initialisation du solveur...")
            solver = CuttingStockSolver(self.pieces, self.plates, self.allow_rotation)
            
            self.progress.emit("Génération des motifs de découpe...")
            solver.generate_patterns()
            
            self.progress.emit("Résolution du problème d'optimisation...")
            solution = solver.solve(self.time_limit)
            
            self.finished.emit(solution)
        except Exception as e:
            self.finished.emit({"status": "error", "message": str(e)})


class CuttingStockGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pieces = []
        self.plates = []
        self.solution = None
        self.solver_thread = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Optimisation de Découpe 2D - Cutting Stock Problem")
        self.showMaximized()
        # Widget central avec tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Titre
        title = QLabel(" ◆ Solveur de Découpe 2D avec Gurobi")
        title_font = QFont("JetBrainsMonoNL Nerd Font Mono", 16, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Onglets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Onglet 1: Saisie des données
        self.input_tab = self.create_input_tab()
        self.tabs.addTab(self.input_tab, "📋 Données d'entrée")
        
        # Onglet 2: Résultats
        self.results_tab = self.create_results_tab()
        self.tabs.addTab(self.results_tab, "📊 Résultats")
        
        # Boutons d'action en bas
        button_layout = QHBoxLayout()
        
        self.solve_btn = QPushButton("▶ Résoudre le problème")
        self.solve_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.solve_btn.clicked.connect(self.solve_problem)
        button_layout.addWidget(self.solve_btn)
        
        self.clear_btn = QPushButton("🗑️ Réinitialiser")
        self.clear_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 14px; padding: 10px;")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(button_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Prêt à optimiser")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Charger des données par défaut
        self.load_default_data()
    

    def create_input_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Section Pièces
        pieces_group = QGroupBox("Pièces à découper")
        pieces_layout = QVBoxLayout()
        
        self.pieces_table = QTableWidget(0, 6)
        self.pieces_table.setHorizontalHeaderLabels([
            "Nom", "Largeur (cm)", "Hauteur (cm)", "Demande", "Priorité", "Actions"
        ])
        ph = self.pieces_table.horizontalHeader()
        ph.setSectionResizeMode(QHeaderView.Stretch)
        ph.setDefaultSectionSize(140)
        pieces_layout.addWidget(self.pieces_table)
        
        add_piece_btn = QPushButton("✘ Ajouter une pièce")
        add_piece_btn.clicked.connect(self.add_piece_row)
        pieces_layout.addWidget(add_piece_btn)
        
        pieces_group.setLayout(pieces_layout)
        layout.addWidget(pieces_group)
        
        # Section Plaques
        plates_group = QGroupBox("Plaques brutes disponibles")
        plates_layout = QVBoxLayout()
        
        self.plates_table = QTableWidget(0, 6)
        self.plates_table.setHorizontalHeaderLabels([
            "Nom", "Largeur (cm)", "Hauteur (cm)", "Coût (€)", "Stock max", "Qualité"
        ])
        rph = self.plates_table.horizontalHeader()
        rph.setSectionResizeMode(QHeaderView.Stretch)
        rph.setDefaultSectionSize(140)
        plates_layout.addWidget(self.plates_table)
        
        add_plate_btn = QPushButton("✘ Ajouter un type de plaque")
        add_plate_btn.clicked.connect(self.add_plate_row)
        plates_layout.addWidget(add_plate_btn)
        
        plates_group.setLayout(plates_layout)
        layout.addWidget(plates_group)
        
        # Options
        options_group = QGroupBox("Options de résolution")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Autoriser rotation 90°:"))
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["Oui", "Non"])
        options_layout.addWidget(self.rotation_combo)
        
        options_layout.addWidget(QLabel("Temps limite (sec):"))
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(10, 3600)
        self.time_limit_spin.setValue(300)
        options_layout.addWidget(self.time_limit_spin)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        return widget
 
    
    def create_results_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Résumé
        summary_group = QGroupBox("📈 Résumé de la solution")
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(150)
        summary_layout.addWidget(self.summary_text)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Détails des motifs
        patterns_group = QGroupBox("⛙ Motifs de découpe utilisés")
        patterns_layout = QVBoxLayout()
        
        self.patterns_table = QTableWidget(0, 5)
        self.patterns_table.setHorizontalHeaderLabels([
            "Motif #", "Type de plaque", "Quantité", "Pièces découpées", "Chute (cm²)"
        ])
        pth = self.patterns_table.horizontalHeader()
        pth.setSectionResizeMode(QHeaderView.Stretch)
        pth.setDefaultSectionSize(140)
        patterns_layout.addWidget(self.patterns_table)
        
        patterns_group.setLayout(patterns_layout)
        layout.addWidget(patterns_group)
        
        # Production
        production_group = QGroupBox("📦 Production par pièce")
        production_layout = QVBoxLayout()
        
        self.production_table = QTableWidget(0, 3)
        self.production_table.setHorizontalHeaderLabels([
            "Pièce", "Produit", "Demande"
        ])
        pth2 = self.production_table.horizontalHeader()
        pth2.setSectionResizeMode(QHeaderView.Stretch)
        pth2.setDefaultSectionSize(140)
        production_layout.addWidget(self.production_table)
        
        production_group.setLayout(production_layout)
        layout.addWidget(production_group)
        
        return widget
    
  
    def add_piece_row(self):
        row = self.pieces_table.rowCount()
        self.pieces_table.insertRow(row)
        
        self.pieces_table.setItem(row, 0, QTableWidgetItem(f"Pièce {row+1}"))
        
        width_spin = QDoubleSpinBox()
        width_spin.setRange(1, 10000)
        width_spin.setValue(50)
        width_spin.setSuffix(" cm")
        self.pieces_table.setCellWidget(row, 1, width_spin)
        
        height_spin = QDoubleSpinBox()
        height_spin.setRange(1, 10000)
        height_spin.setValue(30)
        height_spin.setSuffix(" cm")
        self.pieces_table.setCellWidget(row, 2, height_spin)
        
        demand_spin = QSpinBox()
        demand_spin.setRange(1, 1000)
        demand_spin.setValue(10)
        self.pieces_table.setCellWidget(row, 3, demand_spin)
        
        priority_combo = QComboBox()
        priority_combo.addItems(["Haute (1)", "Moyenne (2)", "Basse (3)"])
        priority_combo.setCurrentIndex(1)
        self.pieces_table.setCellWidget(row, 4, priority_combo)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.clicked.connect(lambda: self.delete_piece_row(row))
        self.pieces_table.setCellWidget(row, 5, delete_btn)
    
    def add_plate_row(self):
        row = self.plates_table.rowCount()
        self.plates_table.insertRow(row)
        
        self.plates_table.setItem(row, 0, QTableWidgetItem(f"Plaque Type {row+1}"))
        
        width_spin = QDoubleSpinBox()
        width_spin.setRange(10, 10000)
        width_spin.setValue(200)
        width_spin.setSuffix(" cm")
        self.plates_table.setCellWidget(row, 1, width_spin)
        
        height_spin = QDoubleSpinBox()
        height_spin.setRange(10, 10000)
        height_spin.setValue(100)
        height_spin.setSuffix(" cm")
        self.plates_table.setCellWidget(row, 2, height_spin)
        
        cost_spin = QDoubleSpinBox()
        cost_spin.setRange(1, 100000)
        cost_spin.setValue(50)
        cost_spin.setSuffix(" €")
        self.plates_table.setCellWidget(row, 3, cost_spin)
        
        stock_spin = QSpinBox()
        stock_spin.setRange(1, 10000)
        stock_spin.setValue(100)
        self.plates_table.setCellWidget(row, 4, stock_spin)
        
        quality_combo = QComboBox()
        quality_combo.addItems(["Premium (1)", "Standard (2)", "Économique (3)"])
        quality_combo.setCurrentIndex(1)
        self.plates_table.setCellWidget(row, 5, quality_combo)
    

    def delete_piece_row(self, row):
        self.pieces_table.removeRow(row)

    def load_default_data(self):
        # Pièces par défaut
        default_pieces = [
            ("Panneau A", 80, 60, 15, 0),
            ("Panneau B", 50, 40, 25, 1),
            ("Panneau C", 100, 30, 10, 2),
        ]
        
        for name, w, h, demand, priority in default_pieces:
            row = self.pieces_table.rowCount()
            self.pieces_table.insertRow(row)
            
            self.pieces_table.setItem(row, 0, QTableWidgetItem(name))
            
            width_spin = QDoubleSpinBox()
            width_spin.setRange(1, 10000)
            width_spin.setValue(w)
            width_spin.setSuffix(" cm")
            self.pieces_table.setCellWidget(row, 1, width_spin)
            
            height_spin = QDoubleSpinBox()
            height_spin.setRange(1, 10000)
            height_spin.setValue(h)
            height_spin.setSuffix(" cm")
            self.pieces_table.setCellWidget(row, 2, height_spin)
            
            demand_spin = QSpinBox()
            demand_spin.setValue(demand)
            self.pieces_table.setCellWidget(row, 3, demand_spin)
            
            priority_combo = QComboBox()
            priority_combo.addItems(["Haute (1)", "Moyenne (2)", "Basse (3)"])
            priority_combo.setCurrentIndex(priority)
            self.pieces_table.setCellWidget(row, 4, priority_combo)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_piece_row(r))
            self.pieces_table.setCellWidget(row, 5, delete_btn)
        
        # Plaques par défaut
        default_plates = [
            ("Plaque Premium", 250, 120, 120, 50, 0),
            ("Plaque Standard", 200, 100, 80, 100, 1),
        ]
        
        for name, w, h, cost, stock, quality in default_plates:
            row = self.plates_table.rowCount()
            self.plates_table.insertRow(row)
            
            self.plates_table.setItem(row, 0, QTableWidgetItem(name))
            
            width_spin = QDoubleSpinBox()
            width_spin.setRange(10, 10000)
            width_spin.setValue(w)
            width_spin.setSuffix(" cm")
            self.plates_table.setCellWidget(row, 1, width_spin)
            
            height_spin = QDoubleSpinBox()
            height_spin.setRange(10, 10000)
            height_spin.setValue(h)
            height_spin.setSuffix(" cm")
            self.plates_table.setCellWidget(row, 2, height_spin)
            
            cost_spin = QDoubleSpinBox()
            cost_spin.setRange(1, 100000)
            cost_spin.setValue(cost)
            cost_spin.setSuffix(" €")
            self.plates_table.setCellWidget(row, 3, cost_spin)
            
            stock_spin = QSpinBox()
            stock_spin.setRange(0, 10000)
            stock_spin.setValue(stock)
            self.plates_table.setCellWidget(row, 4, stock_spin)
            
            quality_combo = QComboBox()
            quality_combo.addItems(["Premium (1)", "Standard (2)", "Économique (3)"])
            quality_combo.setCurrentIndex(quality)
            self.plates_table.setCellWidget(row, 5, quality_combo)
 
    def collect_input_data(self):
        pieces = []
        plates = []
        
        # Pièces
        for row in range(self.pieces_table.rowCount()):
            name = self.pieces_table.item(row, 0).text()
            width = self.pieces_table.cellWidget(row, 1).value()
            height = self.pieces_table.cellWidget(row, 2).value()
            demand = self.pieces_table.cellWidget(row, 3).value()
            priority_text = self.pieces_table.cellWidget(row, 4).currentText()
            priority = int(priority_text.split("(")[1][0])
            
            pieces.append(Piece(
                id=row,
                width=width,
                height=height,
                demand=demand,
                priority=priority,
                name=name
            ))
        
        # Plaques
        for row in range(self.plates_table.rowCount()):
            name = self.plates_table.item(row, 0).text()
            width = self.plates_table.cellWidget(row, 1).value()
            height = self.plates_table.cellWidget(row, 2).value()
            cost = self.plates_table.cellWidget(row, 3).value()
            stock = self.plates_table.cellWidget(row, 4).value()
            quality_text = self.plates_table.cellWidget(row, 5).currentText()
            quality = int(quality_text.split("(")[1][0])
            
            plates.append(PlateType(
                id=row,
                width=width,
                height=height,
                cost=cost,
                max_available=stock,
                quality_level=quality,
                name=name
            ))
        
        return pieces, plates


    def solve_problem(self):
        if self.pieces_table.rowCount() == 0:
            QMessageBox.warning(self, "Erreur", "Veuillez ajouter au moins une pièce!")
            return
        if self.plates_table.rowCount() == 0:
            QMessageBox.warning(self, "Erreur", "Veuillez ajouter au moins un type de plaque!")
            return
        
        pieces, plates = self.collect_input_data()
        allow_rotation = self.rotation_combo.currentText() == "Oui"
        time_limit = self.time_limit_spin.value()
        
        self.solve_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Résolution en cours...")
        
        self.solver_thread = SolverThread(pieces, plates, allow_rotation, time_limit)
        self.solver_thread.progress.connect(self.update_progress)
        self.solver_thread.finished.connect(self.on_solution_ready)
        self.solver_thread.start()
    
    def update_progress(self, message):
        self.status_label.setText(message)
    
    def on_solution_ready(self, solution):
        self.solve_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if solution['status'] == 'error':
            QMessageBox.critical(self, "Erreur", f"Erreur: {solution['message']}")
            self.status_label.setText("Erreur lors de la résolution")
            return
        
        if solution['status'] == 'infeasible':
            QMessageBox.warning(self, "Pas de solution", solution['message'])
            self.status_label.setText("Aucune solution trouvée")
            return
        
        self.solution = solution
        self.display_solution()
        self.status_label.setText("✓ Solution optimale trouvée!")
        self.tabs.setCurrentIndex(1)

    def display_solution(self):
        sol = self.solution
        
        summary = f"""
<b>Statut:</b> {sol['status'].upper()}<br>
<b>Coût total:</b> {sol['total_cost']:.2f} €<br>
<b>Chute totale:</b> {sol['total_waste']:.2f} cm²<br>
<b>Nombre de plaques utilisées:</b> {sol['total_plates']}<br>
<b>Temps de résolution:</b> {sol['solve_time']:.2f} secondes<br>
<b>Valeur de la fonction objectif:</b> {sol['objective_value']:.2f}
        """
        self.summary_text.setHtml(summary)
        
        self.patterns_table.setRowCount(0)
        for pattern in sol['used_patterns']:
            row = self.patterns_table.rowCount()
            self.patterns_table.insertRow(row)
            
            self.patterns_table.setItem(row, 0, QTableWidgetItem(str(pattern['pattern_id'])))
            self.patterns_table.setItem(row, 1, QTableWidgetItem(pattern['plate_type']))
            self.patterns_table.setItem(row, 2, QTableWidgetItem(str(pattern['count'])))
            
            pieces_desc = ", ".join([f"{pid}×{qty}" for pid, qty in pattern['pieces'].items()])
            self.patterns_table.setItem(row, 3, QTableWidgetItem(pieces_desc))
            
            waste_item = QTableWidgetItem(f"{pattern['waste_per_plate']:.2f}")
            self.patterns_table.setItem(row, 4, waste_item)
        
        self.production_table.setRowCount(0)
        pieces, _ = self.collect_input_data()
        for piece in pieces:
            row = self.production_table.rowCount()
            self.production_table.insertRow(row)
            
            self.production_table.setItem(row, 0, QTableWidgetItem(piece.name))
            
            produced = sol['pieces_produced'][piece.id]
            produced_item = QTableWidgetItem(str(produced))
            if produced >= piece.demand:
                produced_item.setBackground(QColor(200, 255, 200))
            else:
                produced_item.setBackground(QColor(255, 200, 200))
            self.production_table.setItem(row, 1, produced_item)
            
            self.production_table.setItem(row, 2, QTableWidgetItem(str(piece.demand)))
    

    def clear_all(self):
        reply = QMessageBox.question(
            self, 'Confirmation',
            'Voulez-vous vraiment réinitialiser toutes les données?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.pieces_table.setRowCount(0)
            self.plates_table.setRowCount(0)
            self.patterns_table.setRowCount(0)
            self.production_table.setRowCount(0)
            self.summary_text.clear()
            self.solution = None
            self.status_label.setText("Prêt à optimiser")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # --- Load Nerd Font globally ---
    font_path = "/usr/share/fonts/custom/JetBrainsMonoNLNerdFontMono-Bold.ttf"
    font_id = QFontDatabase.addApplicationFont(font_path)

    if font_id == -1:
        print(f"CRITICAL: Could not find font at {font_path}")
    else:
        families = QFontDatabase.applicationFontFamilies(font_id)
        print(f"SUCCESS: Font loaded! Family name is: {families[0]}")
        app.setFont(QFont(families[0], 11))
        
    gui = CuttingStockGUI()
    gui.show()
    sys.exit(app.exec_())

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QApplication, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QSpinBox, QScrollArea, QDialog, QTableWidget, QTableWidgetItem)
from PyQt5.QtGui import QFont, QValidator, QIntValidator
from PyQt5.QtCore import Qt
from affect import affect_interns
from affect_machines import assign_tasks_to_machines
from cutting_stock import solve_cutting_stock
from os import getcwd

def do_nothing():
    print("Button clicked")
    return 0

class ActionButton(QPushButton):
    def __init__(self, action_callback, *args, **kwargs):
        assert(callable(action_callback))
        super().__init__(*args, **kwargs)
       
        self.setFont(QFont('FiraCode Nerd Font', 12))
        self.clicked.connect(action_callback)

    def update_action(self, action_callback):
        assert(callable(action_callback))
        self.clicked.connect(action_callback)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self): 
        label = QLabel('Veuillez choisir une application:', self)
        label.setFont(QFont('FiraCode Nerd Font', 14, 100))
        label.move(102, 110)

        btn = [
            ActionButton(self.open_affect_window, 'Affecter des étudiants à des stages', self),
            ActionButton(self.open_task_assignment_window, 'Affecter des tâches à des machines', self),
            ActionButton(self.open_cutting_stock_window, 'Problème de découpe (Cutting Stock)', self),
            ActionButton(do_nothing, 'Button 4', self)
        ]

        i = 0
        for b in btn:
            b.resize(400, 30)
            b.move(100, 200+i)
            i += 40

        self.setGeometry(690, 315, 600, 450)
        self.setWindowTitle('Main Menu')
        self.show()

    def open_affect_window(self):
        self.aff_win = AffectWindow()

    def open_task_assignment_window(self):
        self.task_win = TaskAssignmentWindow()

    def open_cutting_stock_window(self):
        self.cutting_win = CuttingStockWindow()

class AffectWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setFont(QFont('FiraCode Nerd Font', 12))
        self.setup()

    def setup(self):
        general_label = QLabel('Veuillez fournir les données\n nécessaires en format CSV.', self)
        i_upload_label = QLabel('Données de stages:', self)
        s_upload_label = QLabel('Données des étudiants:', self)
        dest_label = QLabel('Fichier des résultats:', self)

        i_upload_btn = ActionButton(self.internships_upload, 'Parcourir...', self)
        s_upload_btn = ActionButton(self.students_upload, 'Parcourir...', self) 
        
        dest_field = QLineEdit(getcwd() + '/results.csv', self)
        dest_field.editingFinished.connect(lambda: self.update_output_loc(dest_field.text()))

        confirm_btn = ActionButton(self.affect, 'Confirmer', self)

        general_label.setFont(QFont('FiraCode Nerd Font', 14, weight=100))
        general_label.move(150, 100)

        i_upload_btn.setToolTip('Format:<br>- première colonne: titres des stages (nom de la colonne: Internships)<br>- deuxième colonne: capacités des stages (nom de la colonne: Capacities)<br>- le reste des colonnes spécifient les compétences requises')
        s_upload_btn.setToolTip('Format:<br>- première colonne: noms et prénoms des étudiants (nom de la colonne: Students)<br>- le reste des colonnes spécifient les compétences')

        i_upload_label.move(130, 200)
        i_upload_btn.move(350, 195)

        s_upload_label.move(130, 250)
        s_upload_btn.move(350, 245)

        dest_label.move(50, 325)
        dest_field.resize(250, dest_field.sizeHint().height())
        dest_field.move(300, 320)

        confirm_btn.resize(120, confirm_btn.sizeHint().height())
        confirm_btn.move(240, 375)

        self.setGeometry(690, 315, 600, 450)
        self.setWindowTitle('Affectation d\'étudiants')
        self.show()

    def internships_upload(self):
        self.i_data_file,_ = QFileDialog.getOpenFileName(self, 'Données des stages')

    def students_upload(self):
        self.s_data_file,_ = QFileDialog.getOpenFileName(self, 'Données des stages')

    def update_output_loc(self, path : str):
        self.output_file = path

    def affect(self):
        i_data = pd.read_csv(self.i_data_file)
        s_data = pd.read_csv(self.s_data_file)

        assert 'Internships' in i_data
        assert 'Capacities' in i_data
        assert 'Students' in s_data
        assert len(i_data['Internships']) == len(i_data['Capacities'])
       
        i_titles = i_data['Internships'].to_numpy()
        i_caps = i_data['Capacities'].to_numpy()
        s_names = s_data['Students'].to_numpy()

        assert i_data.columns[2:].equals(s_data.columns[1:])

        i_skills = i_data.iloc[:, 2:].to_numpy()
        s_skills = s_data.iloc[:, 1:].to_numpy()
        results = affect_interns(s_skills, i_skills, i_caps)

        aff_indices = np.argmax(results, axis=1)
        summary = pd.DataFrame({
            'Students': s_names,
            'Affected Internships': i_titles[aff_indices]
        })

        summary.to_csv(self.output_file, index=False)

class CuttingStockWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setFont(QFont('FiraCode Nerd Font', 12))
        self.material_file = None 
        self.pieces_file = None   
        self.output_file = None
        self.setup()

    def setup(self):
        general_label = QLabel('Veuillez fournir les données\n nécessaires en format CSV.', self)
        material_label = QLabel('Caractéristiques du matériau:', self)
        pieces_label = QLabel('Spécifications des pièces:', self)
        dest_label = QLabel('Fichier des résultats:', self)

        material_btn = ActionButton(self.material_upload, 'Parcourir...', self)
        pieces_btn = ActionButton(self.pieces_upload, 'Parcourir...', self) 
        
        default_output = getcwd() + '/cutting_stock_results.csv'
        self.output_file = default_output
        dest_field = QLineEdit(default_output, self)
        dest_field.editingFinished.connect(lambda: self.update_output_loc(dest_field.text()))

        confirm_btn = ActionButton(self.solve_cutting_stock, 'Confirmer', self)

        general_label.setFont(QFont('FiraCode Nerd Font', 14, weight=100))
        general_label.move(150, 100)

        material_btn.setToolTip('Format:<br>- première colonne: longueur du matériau (nom: length)<br>- deuxième colonne: largeur max (nom: max_width)<br>- autres colonnes: contraintes additionnelles')
        pieces_btn.setToolTip('Format:<br>- première colonne: longueurs des pièces (nom: lengths)<br>- deuxième colonne: demandes (nom: demands)')

        material_label.move(130, 200)
        material_btn.move(350, 195)

        pieces_label.move(130, 250)
        pieces_btn.move(350, 245)

        dest_label.move(50, 325)
        dest_field.resize(250, dest_field.sizeHint().height())
        dest_field.move(300, 320)

        confirm_btn.resize(120, confirm_btn.sizeHint().height())
        confirm_btn.move(240, 375)

        self.setGeometry(690, 315, 600, 450)
        self.setWindowTitle('Problème de découpe (Cutting Stock)')
        self.show()

    def material_upload(self):
        self.material_file,_ = QFileDialog.getOpenFileName(self, 'Caractéristiques du matériau')

    def pieces_upload(self):
        self.pieces_file,_ = QFileDialog.getOpenFileName(self, 'Spécifications des pièces')

    def update_output_loc(self, path : str):
        self.output_file = path

    def solve_cutting_stock(self):
        try:
            if not self.material_file or not self.pieces_file:
                print("Error: Please select both material and pieces files")
                return
            
            material_data = pd.read_csv(self.material_file)
            pieces_data = pd.read_csv(self.pieces_file)

            # Lire les caractéristiques du matériau
            assert 'length' in material_data
            L = float(material_data['length'].iloc[0])
            
            max_width = None
            if 'max_width' in material_data:
                max_width = int(material_data['max_width'].iloc[0])
            
            # Lire les spécifications des pièces
            assert 'lengths' in pieces_data
            assert 'demands' in pieces_data
           
            lengths = pieces_data['lengths'].astype(float).tolist()
            demands = pieces_data['demands'].astype(int).tolist()

            print(f"\n=== Cutting Stock Problem ===")
            print(f"Material length: {L}")
            print(f"Max width: {max_width if max_width else 'No limit'}")
            print(f"Pieces: {len(lengths)} types")
            print(f"Demands: {demands}")
            
            # Résoudre le problème
            result = solve_cutting_stock(L, lengths, demands, max_width)
            
            if result["status"] != "OPTIMAL":
                print("Error: No optimal solution found")
                return
            
            # Créer le résumé
            summary_data = []
            for i, item in enumerate(result["solution"]):
                pattern_str = "|".join(str(x) for x in item["pattern"])
                summary_data.append({
                    'Pattern_ID': i+1,
                    'Pattern': pattern_str,
                    'Amount': item["amount"],
                    'Waste_per_unit': item["waste_per_unit"], 
                    'Total_waste': item["waste_total"]        
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_csv(self.output_file, index=False)
            
            print(f"\n✓ Cutting stock optimization completed successfully!")
            print(f"Total material needed: {result['total_material']:.3f}")
            print(f"Total waste: {result['total_waste']:.3f}")
            print(f"Utilization rate: {result['utilization']*100:.1f}%")
            print(f"Results saved to: {self.output_file}")
            
        except Exception as e:
            print(f"Error during cutting stock optimization: {e}")
            import traceback
            traceback.print_exc()
            
class TaskAssignmentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Affectation des tâches aux machines')
        self.setGeometry(400, 200, 900, 750)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        self.machines = []
        self.tasks = []
        self.machine_capabilities = {}
        self.task_requirements = {}
        self.output_file = getcwd() + '/task_results.csv'
        
        self.setup()
        self.show()

    def setup(self):
        from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QGroupBox, 
                                      QSpinBox, QTableWidget, QTableWidgetItem,
                                      QDialog, QScrollArea)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel('Configuration des Machines et Tâches')
        title_font = QFont('Segoe UI', 18, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: white; text-align: center;")
        main_layout.addWidget(title)
        
        # Machines Section
        machines_group = self._create_section('Machines', self._create_machine_form())
        main_layout.addWidget(machines_group)
        
        # Tasks Section
        tasks_group = self._create_section('Tâches', self._create_task_form())
        main_layout.addWidget(tasks_group)
        
        # Output Section
        output_layout = QHBoxLayout()
        output_label = QLabel('Fichier résultats:')
        output_label.setStyleSheet("color: white; font-weight: bold;")
        self.output_field = QLineEdit(self.output_file)
        self.output_field.setStyleSheet(self._get_input_style())
        self.output_field.editingFinished.connect(lambda: self.update_output_loc(self.output_field.text()))
        
        output_browse = ActionButton(self._select_output_file, 'Parcourir', self)
        output_browse.setStyleSheet(self._get_button_style('#FF6B6B'))
        output_browse.setMaximumWidth(120)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_field)
        output_layout.addWidget(output_browse)
        main_layout.addLayout(output_layout)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        
        assign_btn = ActionButton(self.assign_tasks, 'Lancer l\'optimisation')
        assign_btn.setStyleSheet(self._get_button_style('#4ECDC4'))
        assign_btn.setMinimumHeight(45)
        assign_btn.setFont(QFont('Segoe UI', 12, QFont.Bold))
        
        clear_btn = ActionButton(self.clear_all, 'Réinitialiser')
        clear_btn.setStyleSheet(self._get_button_style('#95E1D3'))
        clear_btn.setMinimumHeight(45)
        clear_btn.setFont(QFont('Segoe UI', 12, QFont.Bold))
        
        action_layout.addWidget(assign_btn)
        action_layout.addWidget(clear_btn)
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def _create_section(self, title, content_widget):
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 2px solid rgba(78, 205, 196, 0.4);
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 10px;
                font-weight: bold;
                font-size: 12px;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        layout = QVBoxLayout()
        layout.addWidget(content_widget)
        group.setLayout(layout)
        return group

    def _create_machine_form(self):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QSpinBox, QLabel
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Machine count
        count_layout = QHBoxLayout()
        count_label = QLabel('Nombre de machines:')
        count_label.setStyleSheet("color: white; font-weight: bold;")
        count_spin = QSpinBox()
        count_spin.setMinimum(1)
        count_spin.setMaximum(20)
        count_spin.setValue(1)
        count_spin.setStyleSheet(self._get_input_style())
        count_spin.valueChanged.connect(lambda v: self._setup_machine_inputs(v))
        
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        count_layout.addStretch()
        layout.addLayout(count_layout)
        
        # Machine inputs container
        self.machines_container = QWidget()
        self.machines_scroll = QScrollArea()
        self.machines_scroll.setWidget(self.machines_container)
        self.machines_scroll.setWidgetResizable(True)
        self.machines_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(78, 205, 196, 0.3);
                border-radius: 5px;
                background-color: #252525;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4ECDC4;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.machines_scroll)
        
        return widget

    def _create_task_form(self):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QSpinBox, QLabel
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Task count
        count_layout = QHBoxLayout()
        count_label = QLabel('Nombre de tâches:')
        count_label.setStyleSheet("color: white; font-weight: bold;")
        count_spin = QSpinBox()
        count_spin.setMinimum(1)
        count_spin.setMaximum(20)
        count_spin.setValue(1)
        count_spin.setStyleSheet(self._get_input_style())
        count_spin.valueChanged.connect(lambda v: self._setup_task_inputs(v))
        
        count_layout.addWidget(count_label)
        count_layout.addWidget(count_spin)
        count_layout.addStretch()
        layout.addLayout(count_layout)
        
        # Task inputs container
        self.tasks_container = QWidget()
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidget(self.tasks_container)
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(78, 205, 196, 0.3);
                border-radius: 5px;
                background-color: #252525;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4ECDC4;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.tasks_scroll)
        
        return widget

    def _setup_machine_inputs(self, count):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        
        layout = QVBoxLayout(self.machines_container)
        layout.setSpacing(12)
        
        self.machine_inputs = {}
        
        for i in range(count):
            machine_layout = QHBoxLayout()
            
            name_label = QLabel(f'Machine {i+1}:')
            name_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: bold; min-width: 90px;")
            name_field = QLineEdit()
            name_field.setPlaceholderText(f'Machine_{i+1}')
            name_field.setText(f'Machine_{i+1}')
            name_field.setStyleSheet(self._get_input_style())
            
            cap_label = QLabel('Capacité:')
            cap_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: bold; min-width: 70px;")
            cap_spin = QSpinBox()
            cap_spin.setMinimum(1)
            cap_spin.setMaximum(100)
            cap_spin.setValue(5)
            cap_spin.setStyleSheet(self._get_input_style())
            
            skill1_label = QLabel('Compétence 1:')
            skill1_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: bold; min-width: 100px;")
            skill1_spin = QSpinBox()
            skill1_spin.setMinimum(0)
            skill1_spin.setMaximum(10)
            skill1_spin.setValue(5)
            skill1_spin.setStyleSheet(self._get_input_style())
            
            machine_layout.addWidget(name_label)
            machine_layout.addWidget(name_field, 1)
            machine_layout.addWidget(cap_label)
            machine_layout.addWidget(cap_spin)
            machine_layout.addWidget(skill1_label)
            machine_layout.addWidget(skill1_spin)
            machine_layout.addStretch()
            
            layout.addLayout(machine_layout)
            
            self.machine_inputs[i] = {
                'name': name_field,
                'capacity': cap_spin,
                'skills': [skill1_spin]
            }
        
        layout.addStretch()

    def _setup_task_inputs(self, count):
        from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
        
        layout = QVBoxLayout(self.tasks_container)
        layout.setSpacing(12)
        
        self.task_inputs = {}
        
        for i in range(count):
            task_layout = QHBoxLayout()
            
            name_label = QLabel(f'Tâche {i+1}:')
            name_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: bold; min-width: 80px;")
            name_field = QLineEdit()
            name_field.setPlaceholderText(f'Task_{i+1}')
            name_field.setText(f'Task_{i+1}')
            name_field.setStyleSheet(self._get_input_style())
            
            req1_label = QLabel('Exigence 1:')
            req1_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-weight: bold; min-width: 100px;")
            req1_spin = QSpinBox()
            req1_spin.setMinimum(0)
            req1_spin.setMaximum(10)
            req1_spin.setValue(3)
            req1_spin.setStyleSheet(self._get_input_style())
            
            task_layout.addWidget(name_label)
            task_layout.addWidget(name_field, 1)
            task_layout.addWidget(req1_label)
            task_layout.addWidget(req1_spin)
            task_layout.addStretch()
            
            layout.addLayout(task_layout)
            
            self.task_inputs[i] = {
                'name': name_field,
                'requirements': [req1_spin]
            }
        
        layout.addStretch()

    def _get_input_style(self):
        return """
            QLineEdit, QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 2px solid rgba(78, 205, 196, 0.6);
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                font-weight: 500;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid rgba(78, 205, 196, 1);
                background-color: #333333;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: rgba(78, 205, 196, 0.3);
                border: none;
                width: 20px;
            }
        """

    def _get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
                transform: translateY(-2px);
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color)};
                transform: translateY(0px);
            }}
        """

    def _lighten_color(self, color):
        # Simple color lightening
        color_map = {
            '#4ECDC4': '#68D8CC',
            '#95E1D3': '#A8E6DB',
            '#FF6B6B': '#FF7F7F'
        }
        return color_map.get(color, color)

    def _darken_color(self, color):
        color_map = {
            '#4ECDC4': '#3AADA5',
            '#95E1D3': '#78CFB5',
            '#FF6B6B': '#E55555'
        }
        return color_map.get(color, color)

    def _select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Sauvegarder les résultats', 
            self.output_file, 'CSV Files (*.csv)'
        )
        if file_path:
            self.output_field.setText(file_path)
            self.output_file = file_path

    def update_output_loc(self, path: str):
        self.output_file = path

    def clear_all(self):
        # Reset all inputs
        for i in self.machine_inputs.values():
            i['name'].setText('')
            i['capacity'].setValue(5)
        for i in self.task_inputs.values():
            i['name'].setText('')

    def assign_tasks(self):
        try:
            # Collect machine data
            m_names = []
            m_caps = []
            m_skills = []
            
            for i, inputs in self.machine_inputs.items():
                name = inputs['name'].text().strip() or f'Machine_{i+1}'
                capacity = inputs['capacity'].value()
                skills = [s.value() for s in inputs['skills']]
                
                m_names.append(name)
                m_caps.append(capacity)
                m_skills.append(skills)
            
            # Collect task data
            t_names = []
            t_reqs = []
            
            for i, inputs in self.task_inputs.items():
                name = inputs['name'].text().strip() or f'Task_{i+1}'
                requirements = [r.value() for r in inputs['requirements']]
                
                t_names.append(name)
                t_reqs.append(requirements)
            
            if not m_names or not t_names:
                print("Error: Please add at least one machine and one task")
                return
            
            m_skills = np.array(m_skills)
            t_reqs = np.array(t_reqs)
            m_caps = np.array(m_caps)
            
            # Run assignment
            results = assign_tasks_to_machines(t_reqs, m_skills, m_caps)
            
            asg_indices = np.argmax(results, axis=1)
            summary = pd.DataFrame({
                'Tasks': t_names,
                'Assigned Machines': [m_names[idx] for idx in asg_indices]
            })
            
            summary.to_csv(self.output_file, index=False)
            
            # Display results in a window
            self._show_results_window(summary)
            print(f"✓ Task assignment completed successfully!")
            print(f"Results saved to: {self.output_file}")
            
        except Exception as e:
            print(f"Error during task assignment: {e}")
            import traceback
            traceback.print_exc()

    def _show_results_window(self, summary_df):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
        from PyQt5.QtCore import Qt
        
        # Create results window
        results_window = QDialog(self)
        results_window.setWindowTitle('Résultats - Affectation des Tâches')
        results_window.setGeometry(600, 300, 600, 400)
        results_window.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                gridline-color: #3d3d3d;
                border: 1px solid rgba(78, 205, 196, 0.3);
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QHeaderView::section {
                background-color: #4ECDC4;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4ECDC4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3AADA5;
            }
        """)
        
        layout = QVBoxLayout(results_window)
        
        # Title
        title = QLabel('Résultats de l\'Optimisation')
        title_font = QFont('Segoe UI', 14, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #4ECDC4;")
        layout.addWidget(title)
        
        # Create table
        table = QTableWidget()
        table.setRowCount(len(summary_df))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(['Tâche', 'Machine Assignée'])
        table.horizontalHeader().setStretchLastSection(True)
        
        # Populate table
        for row, (task, machine) in enumerate(zip(summary_df['Tasks'], summary_df['Assigned Machines'])):
            task_item = QTableWidgetItem(str(task))
            task_item.setForeground(Qt.white)
            machine_item = QTableWidgetItem(str(machine))
            machine_item.setForeground(Qt.white)
            table.setItem(row, 0, task_item)
            table.setItem(row, 1, machine_item)
        
        table.setRowHeight(0, 40)
        layout.addWidget(table)
        
        # Close button
        close_btn = QPushButton('Fermer')
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(results_window.close)
        layout.addWidget(close_btn)
        
        results_window.exec_()
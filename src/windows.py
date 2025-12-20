import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton, QLabel, QLineEdit, QFileDialog
from PyQt5.QtGui import QFont, QValidator, QIntValidator
from affect import affect_interns
from affect_machines import assign_tasks_to_machines
from facility_location_gui import FacilityLocationGUI
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
            ActionButton(self.open_facility_location_window, 'Localisation de cliniques/hôpitaux', self)
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

    def open_facility_location_window(self):
        self.facility_win = FacilityLocationGUI()

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

        self.setFont(QFont('FiraCode Nerd Font', 12))
        self.m_data_file = None
        self.t_data_file = None
        self.output_file = None
        self.setup()

    def setup(self):
        general_label = QLabel('Veuillez fournir les données\n nécessaires en format CSV.', self)
        m_upload_label = QLabel('Données des machines:', self)
        t_upload_label = QLabel('Données des tâches:', self)
        dest_label = QLabel('Fichier des résultats:', self)

        m_upload_btn = ActionButton(self.machines_upload, 'Parcourir...', self)
        t_upload_btn = ActionButton(self.tasks_upload, 'Parcourir...', self) 
        
        default_output = getcwd() + '/task_results.csv'
        self.output_file = default_output
        dest_field = QLineEdit(default_output, self)
        dest_field.editingFinished.connect(lambda: self.update_output_loc(dest_field.text()))

        confirm_btn = ActionButton(self.assign_tasks, 'Confirmer', self)

        general_label.setFont(QFont('FiraCode Nerd Font', 14, weight=100))
        general_label.move(150, 100)

        m_upload_btn.setToolTip('Format:<br>- première colonne: noms des machines (nom de la colonne: Machines)<br>- deuxième colonne: capacités des machines (nom de la colonne: Capacities)<br>- le reste des colonnes spécifient les capacités/caractéristiques des machines')
        t_upload_btn.setToolTip('Format:<br>- première colonne: noms et identifiants des tâches (nom de la colonne: Tasks)<br>- le reste des colonnes spécifient les exigences/ressources nécessaires pour chaque tâche')

        m_upload_label.move(130, 200)
        m_upload_btn.move(350, 195)

        t_upload_label.move(130, 250)
        t_upload_btn.move(350, 245)

        dest_label.move(50, 325)
        dest_field.resize(250, dest_field.sizeHint().height())
        dest_field.move(300, 320)

        confirm_btn.resize(120, confirm_btn.sizeHint().height())
        confirm_btn.move(240, 375)

        self.setGeometry(690, 315, 600, 450)
        self.setWindowTitle('Affectation des tâches aux machines')
        self.show()

    def machines_upload(self):
        self.m_data_file,_ = QFileDialog.getOpenFileName(self, 'Données des machines')

    def tasks_upload(self):
        self.t_data_file,_ = QFileDialog.getOpenFileName(self, 'Données des tâches')

    def update_output_loc(self, path : str):
        self.output_file = path

    def assign_tasks(self):
        try:
            if not self.m_data_file or not self.t_data_file:
                print("Error: Please select both machines and tasks files")
                return
            
            m_data = pd.read_csv(self.m_data_file)
            t_data = pd.read_csv(self.t_data_file)

            assert 'Machines' in m_data
            assert 'Capacities' in m_data
            assert 'Tasks' in t_data
            assert len(m_data['Machines']) == len(m_data['Capacities'])
           
            m_titles = m_data['Machines'].to_numpy()
            m_caps = m_data['Capacities'].to_numpy()
            t_names = t_data['Tasks'].to_numpy()

            assert m_data.columns[2:].equals(t_data.columns[1:])

            m_capabilities = m_data.iloc[:, 2:].to_numpy()
            t_requirements = t_data.iloc[:, 1:].to_numpy()
            results = assign_tasks_to_machines(t_requirements, m_capabilities, m_caps)

            asg_indices = np.argmax(results, axis=1)
            summary = pd.DataFrame({
                'Tasks': t_names,
                'Assigned Machines': m_titles[asg_indices]
            })

            summary.to_csv(self.output_file, index=False)
            print(f"✓ Task assignment completed successfully!")
            print(f"Results saved to: {self.output_file}")
        except Exception as e:
            print(f"Error during task assignment: {e}")
            import traceback
            traceback.print_exc()

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton, QLabel, QLineEdit, QFileDialog, QDialog, QMessageBox
from PyQt5.QtGui import QFont, QValidator, QIntValidator
from affect import affect_interns
from affect_machines import assign_tasks_to_machines
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
            ActionButton(do_nothing, 'Button 3', self),
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

        try:
            results = affect_interns(s_skills, i_skills, i_caps)

            aff_indices = np.argmax(results, axis=1)
            summary = pd.DataFrame({
                'Students': s_names,
                'Affected Internships': i_titles[aff_indices]
            })

            summary.to_csv(self.output_file, index=False)
            
            dlg = QMessageBox(self,
                    "Succès!",
                    "Les étudiants ont été assignés à leurs stages avec succès!")
            dlg.setStandardButtons(QMessageBox.Ok)
            dlg.exec()

        except Exception:
            dlg = QMessageBox.critical(self,
                    "Erreur!",
                    f"Une erreur a été recontrée. Vérifier que les fichiers fournis sont dans le bon format.")
            dlg.setStandardButtons(QMessageBox.Ok)
            dlg.exec()


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

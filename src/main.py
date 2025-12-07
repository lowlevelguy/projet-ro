import sys
from PyQt5.QtWidgets import QApplication
from windows import MainWindow

app = QApplication([])
win = MainWindow()
sys.exit(app.exec_())

import sys
import logging
from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtGui import QIcon
from database import initialize_db
from windows.main_menu import MainMenu
from windows.lab_management import LabManagement
from windows.performance_monitor import PerformanceMonitor
from windows.import_export import ImportExport
from windows.questions_management import QuestionsManagement
from windows.server_control import ServerControl
from styles import MAIN_STYLE
import os

logging.basicConfig(
    filename='teacher_app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class App(QStackedWidget):
    def __init__(self):
        super().__init__()
        initialize_db()
        self.init_ui()

    def init_ui(self):
        self.main_menu = MainMenu(self.switch_window)
        self.lab_management = LabManagement(self.switch_window)
        self.performance_monitor = PerformanceMonitor(self.switch_window)
        self.import_export = ImportExport(self.switch_window)
        self.server_control = ServerControl(self.switch_window)

        self.addWidget(self.main_menu)
        self.addWidget(self.lab_management)
        self.addWidget(self.performance_monitor)
        self.addWidget(self.import_export)
        self.addWidget(self.server_control)

        self.current_student_id = None

        base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        self.setWindowIcon(QIcon(os.path.join(base_path, "app_icon.ico")))

        self.setWindowTitle("Pselp")
        self.showMaximized()  # Запускаем в полноэкранном режиме
        self.apply_style()
        self.show()

    def apply_style(self):
        self.setStyleSheet(MAIN_STYLE)

    def switch_window(self, window_name, data=None):
        if window_name == "main_menu":
            self.setCurrentWidget(self.main_menu)
        elif window_name == "lab_management":
            self.lab_management.load_data()
            self.setCurrentWidget(self.lab_management)
        elif window_name == "performance_monitor":
            self.performance_monitor.load_data()
            self.setCurrentWidget(self.performance_monitor)
        elif window_name == "import_export":
            self.setCurrentWidget(self.import_export)
        elif window_name == "questions_management" and data is not None:
            questions_window = QuestionsManagement(self.switch_window, data)
            self.addWidget(questions_window)
            self.setCurrentWidget(questions_window)
        elif window_name == "server_control":
            self.setCurrentWidget(self.server_control)

    def set_student_id(self, student_id):
        self.current_student_id = student_id

    def get_student_id(self):
        return self.current_student_id

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
    app.setWindowIcon(QIcon(os.path.join(base_path, "app_icon.ico")))
    sys.exit(app.exec())

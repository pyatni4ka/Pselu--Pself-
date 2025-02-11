"""
Pselu - Приложение для тестирования студентов

Главный модуль приложения, управляющий всеми окнами и их взаимодействием.
Реализует основную логику навигации между окнами и управление состоянием приложения.

Основные компоненты:
- Вход в систему
- Регистрация
- Выбор лабораторной работы
- Тестирование
- Просмотр результатов

Версия: 1.0.0
"""

import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt5.QtGui import QIcon
from windows.login import LoginWindow
from windows.registration import RegistrationWindow
from windows.lab_selection import LabSelectionWindow
from windows.testing import TestingWindow
from windows.result import ResultWindow
from styles import MAIN_STYLE
import logging
import os
from config_manager import ConfigManager
from logger_config import setup_logger
import codecs

# Добавляем корневую директорию в PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

class App(QStackedWidget):
    """
    Главный класс приложения, управляющий всеми окнами.
    
    Attributes:
        current_student_id (int): ID текущего студента
        login_window (LoginWindow): Окно входа
        registration_window (RegistrationWindow): Окно регистрации
        lab_selection_window (LabSelectionWindow): Окно выбора работы
        testing_window (TestingWindow): Окно тестирования
        result_window (ResultWindow): Окно результатов
    """
    def __init__(self):
        super().__init__()
        self.current_student_id = None
        self.init_ui()

    def init_ui(self):
        self.login_window = LoginWindow(self.switch_window)
        self.registration_window = RegistrationWindow(self.switch_window)
        self.lab_selection_window = LabSelectionWindow(self.switch_window, self.get_student_id)
        self.testing_window = TestingWindow(self.switch_window, self.get_student_id)
        self.result_window = ResultWindow(self.switch_window, self.get_student_id)

        self.addWidget(self.login_window)
        self.addWidget(self.registration_window)
        self.addWidget(self.lab_selection_window)
        self.addWidget(self.testing_window)
        self.addWidget(self.result_window)

        base_path = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        self.setWindowIcon(QIcon(os.path.join(base_path, "app_icon.ico")))

        self.setWindowTitle("Pselu")
        self.setGeometry(100, 100, 800, 600)
        self.apply_style()
        self.show()

    def apply_style(self):
        self.setStyleSheet(MAIN_STYLE)

    def switch_window(self, window_name, data=None):
        if window_name == "login":
            self.setCurrentWidget(self.login_window)
        elif window_name == "registration":
            self.setCurrentWidget(self.registration_window)
        elif window_name == "lab_selection":
            self.lab_selection_window.load_data()
            self.setCurrentWidget(self.lab_selection_window)
        elif window_name == "testing":
            if data:
                self.testing_window.load_questions(data)
            self.setCurrentWidget(self.testing_window)
        elif window_name == "result":
            if data:
                self.result_window.display_result(data)
            self.setCurrentWidget(self.result_window)
        elif window_name == "login_success":
            self.current_student_id = data.get('student_id')
            if not self.current_student_id:
                QMessageBox.critical(self, "Ошибка", "Не удалось получить student_id.")
                return
            self.lab_selection_window.load_data()
            self.setCurrentWidget(self.lab_selection_window)
        else:
            pass

    def set_student_id(self, student_id):
        self.current_student_id = student_id

    def get_student_id(self):
        return self.current_student_id

if __name__ == "__main__":
    # Принудительно устанавливаем кодировку
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    
    from logger_config import setup_logger
    logger = setup_logger()
    logger.info("Запуск приложения")
    
    app = QApplication(sys.argv)
    
    # Получаем путь к директории с исполняемым файлом
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано
        application_path = sys._MEIPASS
    else:
        # Если приложение запущено из исходников
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # Устанавливаем иконку приложения
    icon_path = os.path.join(application_path, 'app_icon.ico')
    app.setWindowIcon(QIcon(icon_path))
    
    # Если нужны настройки сервера:
    config = ConfigManager()
    server_host = config.get_server_host()
    server_port = config.get_server_port()
    
    ex = App()
    sys.exit(app.exec_())

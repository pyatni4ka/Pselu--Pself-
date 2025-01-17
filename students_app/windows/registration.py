from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtGui import QPixmap
import sys
import os
from .network_workers import Worker

class RegistrationWindow(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

    def init_ui(self):
        layout = QVBoxLayout()
        header = QLabel("Регистрация студента")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if hasattr(sys, '_MEIPASS'): 
            base_path = sys._MEIPASS
        else:
            # Получаем путь к корневой директории приложения
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        logo_path = os.path.join(base_path, "resources", "logo.png")
        
        # Добавляем логирование для отладки
        print(f"Путь к логотипу: {logo_path}")
        if not os.path.exists(logo_path):
            print(f"Файл логотипа не найден!")

        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(
                150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.logo_label.setText("Логотип отсутствует")

        layout.addWidget(self.logo_label)

        self.input_last_name = QLineEdit()
        self.input_last_name.setPlaceholderText("Фамилия")
        self.input_first_name = QLineEdit()
        self.input_first_name.setPlaceholderText("Имя")
        self.input_middle_name = QLineEdit()
        self.input_middle_name.setPlaceholderText("Отчество (не обязательно)")
        self.input_group = QLineEdit()
        self.input_group.setPlaceholderText("Группа")
        self.input_year = QLineEdit()
        self.input_year.setPlaceholderText("Год (например 2024)")

        layout.addWidget(self.input_last_name)
        layout.addWidget(self.input_first_name)
        layout.addWidget(self.input_middle_name)
        layout.addWidget(self.input_group)
        layout.addWidget(self.input_year)

        btn_layout = QHBoxLayout()
        btn_register = QPushButton("Зарегистрироваться")
        btn_back = QPushButton("Назад")
        btn_layout.addWidget(btn_register)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_register.clicked.connect(self.register)
        btn_back.clicked.connect(lambda: self.switch_window("login"))

        layout.setSpacing(15)
        layout.setContentsMargins(100, 50, 100, 50)
        self.setLayout(layout)
        self.setWindowTitle("Регистрация студента")
        self.resize(400, 600)

    def register(self):
        first_name = self.input_first_name.text().strip()
        last_name = self.input_last_name.text().strip()
        middle_name = self.input_middle_name.text().strip()
        group = self.input_group.text().strip()
        year_str = self.input_year.text().strip()

        if not first_name or not last_name or not group or not year_str:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все обязательные поля, включая год.")
            return

        try:
            year = int(year_str)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Год должен быть числом.")
            return

        request = {
            'action': 'register',
            'data': {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'group_name': group,
                'year': year
            }
        }

        worker = Worker(request)
        worker.signals.finished.connect(self.handle_register_response)
        worker.signals.error.connect(self.handle_register_error)
        self.thread_pool.start(worker)

    def handle_register_response(self, response):
        if response.get('status') == 'success':
            student_id = response['data']['student_id']
            QMessageBox.information(self, "Успех", "Регистрация прошла успешно!")
            self.switch_window("login_success", data={'student_id': student_id})
        else:
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Ошибка при регистрации'))

    def handle_register_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)

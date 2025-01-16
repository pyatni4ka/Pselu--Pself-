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


class LoginWindow(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

    def init_ui(self):
        layout = QVBoxLayout()
        header = QLabel("Вход студента")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if hasattr(sys, '_MEIPASS'):
            # Если приложение скомпилировано
            base_path = sys._MEIPASS
        else:
            # Если приложение запущено из исходников
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        logo_path = os.path.join(base_path, "resources", "logo.png")
        
        # Добавим отладочный вывод
        print(f"Путь к логотипу: {logo_path}")
        print(f"Файл существует: {os.path.exists(logo_path)}")

        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(
                150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.logo_label.setText("Логотип отсутствует")
            print(f"Ошибка загрузки логотипа: {logo_path}")

        layout.addWidget(self.logo_label)

        self.input_last_name = QLineEdit()
        self.input_last_name.setPlaceholderText("Фамилия")
        self.input_last_name.textChanged.connect(self.capitalize_input)

        self.input_first_name = QLineEdit()
        self.input_first_name.setPlaceholderText("Имя")
        self.input_first_name.textChanged.connect(self.capitalize_input)

        self.input_middle_name = QLineEdit()
        self.input_middle_name.setPlaceholderText("Отчество (не обязательно)")
        self.input_middle_name.textChanged.connect(self.capitalize_input)

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
        btn_login = QPushButton("Войти")
        btn_register = QPushButton("Зарегистрироваться")
        btn_layout.addWidget(btn_login)
        btn_layout.addWidget(btn_register)
        layout.addLayout(btn_layout)

        btn_login.clicked.connect(self.login)
        btn_register.clicked.connect(lambda: self.switch_window("registration"))

        layout.setSpacing(15)
        layout.setContentsMargins(100, 50, 100, 50)
        self.setLayout(layout)
        self.setWindowTitle("Вход студента")
        self.resize(400, 600)

    def capitalize_input(self):
        sender = self.sender()
        text = sender.text()
        sender.blockSignals(True)
        sender.setText(text.title())
        sender.blockSignals(False)

    def login(self):
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
            'action': 'login',
            'data': {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'group_name': group,
                'year': year
            }
        }

        worker = Worker(request)
        worker.signals.finished.connect(self.handle_login_response)
        worker.signals.error.connect(self.handle_login_error)
        self.thread_pool.start(worker)

    def handle_login_response(self, response):
        if response.get('status') == 'success':
            student_id = response['data']['student_id']
            QMessageBox.information(self, "Успех", "Успешный вход!")
            self.switch_window("login_success", data={'student_id': student_id})
        else:
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Ошибка при входе'))

    def handle_login_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QHBoxLayout,
    QDialog,
    QFrame
)
from PyQt5.QtCore import Qt, QThreadPool, QTimer
from PyQt5.QtGui import QPixmap, QColor, QPainter
import sys
import os
import socket
from network_workers import Worker
from config_manager import ConfigManager
from logger_config import get_logger

logger = get_logger('windows.login')


class ConnectionIndicator(QFrame):
    """Индикатор подключения к серверу."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)  # Уменьшаем размер
        self.setStyleSheet("background-color: red; border-radius: 5px; opacity: 0.7;")  # Добавляем прозрачность
        self.connected = False

    def set_connected(self, connected):
        """Устанавливает состояние подключения."""
        self.connected = connected
        self.setStyleSheet(f"background-color: {'green' if connected else 'red'}; border-radius: 5px; opacity: 0.7;")
        self.update()


class LoginWindow(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.thread_pool = QThreadPool.globalInstance()
        # Получаем настройки через ConfigManager
        config = ConfigManager()
        self.server_host = config.get_server_host()
        self.server_port = config.get_server_port()
        self.init_ui()
        self.check_connection()  # Запускаем проверку подключения после инициализации UI

    def init_ui(self):
        layout = QVBoxLayout()

        # Создаем верхний layout для индикатора подключения
        top_layout = QHBoxLayout()
        top_layout.addStretch()  # Добавляем растяжку, чтобы индикатор был справа

        # Индикатор подключения
        self.connection_indicator = ConnectionIndicator(self)
        top_layout.addWidget(self.connection_indicator)

        # Добавляем верхний layout в основной layout
        layout.addLayout(top_layout)

        # Заголовок
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

    def check_connection(self):
        """Проверяет подключение к серверу."""
        try:
            logger.debug(f"Проверка подключения к {self.server_host}:{self.server_port}")
            print(f"Попытка подключения к {self.server_host}:{self.server_port}")

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            logger.debug("Сокет создан, устанавливаем соединение...")
            sock.connect((self.server_host, self.server_port))
            logger.debug("Соединение установлено успешно")
            sock.close()
            self.connection_indicator.set_connected(True)
        except Exception as e:
            logger.error(f"Ошибка подключения к {self.server_host}:{self.server_port}: {e}")
            logger.exception("Подробная информация об ошибке:")
            self.connection_indicator.set_connected(False)
        finally:
            QTimer.singleShot(5000, self.check_connection)

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

    def show_settings(self):
        """Показывает окно настроек."""
        from .settings import SettingsDialog  # Импортируем класс окна настроек
        dialog = SettingsDialog(self)  # Создаем диалоговое окно
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self,
                "Настройки сохранены",
                "Настройки успешно сохранены. Перезапустите приложение для применения изменений."
            )

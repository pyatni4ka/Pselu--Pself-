from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
import configparser
import os
import sys

class ServerConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        header = QLabel("Настройка подключения к серверу")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Поле для ввода IP-адреса
        lbl_ip = QLabel("IP-адрес сервера:")
        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("Введите IP-адрес сервера")
        layout.addWidget(lbl_ip)
        layout.addWidget(self.input_ip)

        # Поле для ввода порта
        lbl_port = QLabel("Порт сервера:")
        self.input_port = QLineEdit()
        self.input_port.setPlaceholderText("Введите порт сервера")
        layout.addWidget(lbl_port)
        layout.addWidget(self.input_port)

        # Кнопка сохранения
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)

        # Загружаем текущие настройки
        self.load_config()

        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        self.setWindowTitle("Настройка сервера")
        self.resize(400, 200)

    def load_config(self):
        """Загружает текущие настройки из файла config.ini."""
        config = configparser.ConfigParser()
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            config.read(config_path)
            self.input_ip.setText(config.get('Server', 'host', fallback='localhost'))
            self.input_port.setText(str(config.getint('Server', 'port', fallback=9999)))

    def save_config(self):
        """Сохраняет настройки в файл config.ini."""
        ip = self.input_ip.text().strip()
        port = self.input_port.text().strip()

        if not ip or not port:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля.")
            return

        if not port.isdigit():
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом.")
            return

        config = configparser.ConfigParser()
        config['Server'] = {
            'host': ip,
            'port': port
        }

        try:
            with open(self.get_config_path(), 'w') as configfile:
                config.write(configfile)
            QMessageBox.information(self, "Успех", "Настройки успешно сохранены.")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")

    def get_config_path(self):
        """Возвращает путь к файлу конфигурации."""
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'config.ini')

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ServerConfigWindow()
    window.show()
    sys.exit(app.exec_())
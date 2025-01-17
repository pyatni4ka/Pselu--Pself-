"""
Окно настроек приложения.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
import configparser
import os
import sys

def get_config_path():
    """Получает путь к конфигурационному файлу."""
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано
        base_dir = os.path.dirname(sys.executable)
    else:
        # Если приложение запущено из исходников
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base_dir, 'config.ini')

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Настройки подключения")
        layout = QVBoxLayout()

        # IP адрес сервера
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP адрес сервера:")
        self.ip_input = QLineEdit()
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)

        # Порт сервера
        port_layout = QHBoxLayout()
        port_label = QLabel("Порт сервера:")
        self.port_input = QLineEdit()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)

        # Порт статического сервера
        static_port_layout = QHBoxLayout()
        static_port_label = QLabel("Порт статического сервера:")
        self.static_port_input = QLineEdit()
        static_port_layout.addWidget(static_port_label)
        static_port_layout.addWidget(self.static_port_input)
        layout.addLayout(static_port_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_settings(self):
        """Загружает настройки из файла конфигурации."""
        config = configparser.ConfigParser()
        config_path = get_config_path()
        
        if os.path.exists(config_path):
            config.read(config_path, encoding='utf-8')
            self.ip_input.setText(config.get('Server', 'host', fallback='localhost'))
            self.port_input.setText(config.get('Server', 'port', fallback='9999'))
            self.static_port_input.setText(config.get('Server', 'static_port', fallback='8080'))

    def save_settings(self):
        """Сохраняет настройки в файл конфигурации."""
        config = configparser.ConfigParser()
        config['Server'] = {
            'host': self.ip_input.text(),
            'port': self.port_input.text(),
            'static_port': self.static_port_input.text()
        }
        
        config_path = get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            self.accept()
            QMessageBox.information(self, "Успех", "Настройки сохранены. Перезапустите приложение для применения изменений.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")

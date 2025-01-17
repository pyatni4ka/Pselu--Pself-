from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt
from server.server import ServerThread
import logging
import socket

logging.basicConfig(
    filename='server_control.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ServerControl(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.server_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        header = QLabel("Управление веб-сервером")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Показ локального IP-адреса
        self.local_ip_label = QLabel(f"Локальный IP в сети: {self.get_network_ip()}")
        self.local_ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.local_ip_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(self.local_ip_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.hide()

        self.btn_show_logs = QPushButton("Показать логи")
        self.btn_show_logs.clicked.connect(self.toggle_logs)

        layout.addWidget(self.btn_show_logs, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Запустить сервер")
        self.btn_stop = QPushButton("Остановить сервер")
        self.btn_stop.setEnabled(False)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        btn_back = QPushButton("Назад")
        btn_back.setFixedHeight(40)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_start.clicked.connect(self.start_server)
        self.btn_stop.clicked.connect(self.stop_server)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))

        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        self.setLayout(layout)
        self.setWindowTitle("Управление веб-сервером")
        self.resize(600, 500)

    def toggle_logs(self):
        if self.log_text.isVisible():
            self.log_text.hide()
            self.btn_show_logs.setText("Показать логи")
        else:
            self.log_text.show()
            self.btn_show_logs.setText("Скрыть логи")

    def start_server(self):
        if self.server_thread and self.server_thread.isRunning():
            QMessageBox.warning(self, "Предупреждение", "Сервер уже запущен.")
            logger.warning("Попытка запустить сервер, который уже запущен.")
            return
        self.server_thread = ServerThread()
        self.server_thread.server_started.connect(self.on_server_started)
        self.server_thread.server_stopped.connect(self.on_server_stopped)
        self.server_thread.log_message.connect(self.append_log)
        self.server_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        logger.info("Запуск сервера по команде пользователя.")

    def stop_server(self):
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop_server()
            logger.info("Остановка сервера по команде пользователя.")
        else:
            QMessageBox.warning(self, "Предупреждение", "Сервер не запущен.")
            logger.warning("Попытка остановить сервер, который не запущен.")

    def on_server_started(self):
        self.append_log("Сервер успешно запущен.")
        logger.info("Сервер успешно запущен.")

    def on_server_stopped(self):
        self.append_log("Сервер успешно остановлен.")
        logger.info("Сервер успешно остановлен.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def append_log(self, message: str):
        logger.info(message)
        if "Клиент отключился: (" in message:
            message = "Неизвестный студент отключился"
        if (
            "подключился" in message
            or "лабораторную работу" in message
            or "Сервер" in message
        ):
            self.log_text.append(message)

    def get_network_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip.startswith(("192.168.", "10.", "172.")):
                    return local_ip
                else:
                    return "Не удалось определить локальный IP"
        except Exception as e:
            logger.error(f"Ошибка получения локального IP в сети: {e}")
            return "localhost"

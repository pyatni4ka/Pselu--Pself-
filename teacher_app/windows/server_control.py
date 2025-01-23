from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QDockWidget, QTextEdit, QHeaderView, QMessageBox,
    QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import logging
from datetime import datetime, timedelta
import time
import socket
from server.server import ServerThread

logging.basicConfig(
    filename='server_control.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ServerControl(QMainWindow):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.server_thread = None
        self.results_timestamps = {}
        self.setWindowTitle("Управление веб-сервером")
        self.resize(1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Верхняя панель с информацией о сервере
        server_info = QHBoxLayout()
        
        # Показ локального IP-адреса
        self.local_ip_label = QLabel(f"Локальный IP в сети: {self.get_network_ip()}")
        self.local_ip_label.setStyleSheet("""
            font-size: 14px;
            color: #2c3e50;
            padding: 5px;
            background-color: #f5f6fa;
            border-radius: 5px;
        """)
        server_info.addWidget(self.local_ip_label)
        
        # Статус сервера
        self.status_label = QLabel("Статус сервера: Неактивен")
        self.status_label.setStyleSheet("""
            color: #e74c3c;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f5f6fa;
            border-radius: 5px;
            margin-left: 10px;
        """)
        server_info.addWidget(self.status_label)
        
        # Добавляем счетчик активных подключений
        self.connections_label = QLabel("Активных подключений: 0")
        self.connections_label.setStyleSheet("""
            color: #2980b9;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f5f6fa;
            border-radius: 5px;
            margin-left: 10px;
        """)
        server_info.addWidget(self.connections_label)
        
        # Кнопки управления сервером
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Запустить сервер")
        self.btn_stop = QPushButton("Остановить сервер")
        self.btn_stop.setEnabled(False)
        
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        server_info.addLayout(btn_layout)
        
        server_info.addStretch()
        main_layout.addLayout(server_info)
        
        # Создаем вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #f5f6fa;
                border: 1px solid #dcdde1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
        """)
        
        # Вкладка активных сессий
        sessions_tab = QWidget()
        sessions_layout = QVBoxLayout(sessions_tab)
        
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(5)
        self.sessions_table.setHorizontalHeaderLabels([
            "ФИО", "Группа", "Лабораторная работа", 
            "Время работы", "Статус"
        ])
        
        # Настраиваем ширину столбцов
        self.sessions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # ФИО
        self.sessions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Группа
        self.sessions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)     # Лаб. работа
        self.sessions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Время
        self.sessions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Статус
        
        # Устанавливаем минимальную ширину для столбцов
        self.sessions_table.setColumnWidth(0, 200)  # ФИО
        self.sessions_table.setColumnWidth(1, 100)  # Группа
        self.sessions_table.setColumnWidth(3, 100)  # Время
        self.sessions_table.setColumnWidth(4, 100)  # Статус
        
        self.sessions_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
            }
            QHeaderView::section {
                background-color: #f5f6fa;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: #2c3e50;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        sessions_layout.addWidget(self.sessions_table)
        
        # Вкладка результатов
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Время", "ФИО", "Группа", "Лаб. работа", 
            "Результат", "Время выполнения"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
            }
            QHeaderView::section {
                background-color: #f5f6fa;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: #2c3e50;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        results_layout.addWidget(self.results_table)
        
        # Добавляем вкладки
        self.tab_widget.addTab(sessions_tab, "Активные сессии")
        self.tab_widget.addTab(results_tab, "Результаты тестирования")
        main_layout.addWidget(self.tab_widget)
        
        # Создаем док-виджет для логов внизу
        log_dock = QDockWidget("Системные сообщения", self)
        log_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | 
                           QDockWidget.DockWidgetFeature.DockWidgetMovable)
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2f3640;
                color: #dcdde1;
                font-family: Consolas, monospace;
                font-size: 10px;
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_dock.setWidget(log_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, log_dock)
        
        # Кнопка "Назад"
        btn_back = QPushButton("Назад")
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        main_layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Подключаем сигналы
        self.btn_start.clicked.connect(self.start_server)
        self.btn_stop.clicked.connect(self.stop_server)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))
        
        # Таймеры для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(1000)  # Обновление каждую секунду
        
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_old_results)
        self.cleanup_timer.start(7200000)  # Проверка каждые 2 часа
    
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
        self.status_label.setText("Статус сервера: Активен")
        self.status_label.setStyleSheet("""
            color: #27ae60;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f5f6fa;
            border-radius: 5px;
        """)
        self.append_log("Сервер успешно запущен.")
        logger.info("Сервер успешно запущен.")
    
    def on_server_stopped(self):
        self.status_label.setText("Статус сервера: Неактивен")
        self.status_label.setStyleSheet("""
            color: #e74c3c;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f5f6fa;
            border-radius: 5px;
        """)
        self.append_log("Сервер успешно остановлен.")
        logger.info("Сервер успешно остановлен.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
    
    def format_duration(self, duration):
        """Форматирует продолжительность в читаемый вид"""
        if isinstance(duration, str):
            if ':' in duration:  # Если уже в формате MM:SS
                return duration
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                return "00:00"
                
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
    
    def update_data(self):
        """Обновляет данные в таблицах"""
        if self.server_thread and self.server_thread.isRunning():
            # Получаем данные от сервера
            active_sessions = self.server_thread.get_active_sessions()
            
            # Обновляем таблицу активных сессий
            self.sessions_table.setRowCount(len(active_sessions))
            for row, session in enumerate(active_sessions):
                for col, value in enumerate(session):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Устанавливаем цвет фона для статуса
                    if col == 4:  # Колонка статуса
                        if value == "Активен":
                            item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
                        elif value == "Неактивен":
                            item.setBackground(QColor(255, 182, 193))  # Светло-красный
                    
                    # Форматируем время работы
                    if col == 3:  # Колонка времени работы
                        item.setText(value if ':' in str(value) else self.format_duration(value))
                    
                    self.sessions_table.setItem(row, col, item)
            
            # Обновляем счетчик подключений
            self.connections_label.setText(f"Активных подключений: {len(active_sessions)}")
            
            # Получаем новые результаты
            new_results = self.server_thread.get_new_results()
            if new_results:
                for result in new_results:
                    self.add_result(result)
    
    def add_result(self, data):
        """Добавляет результат в таблицу"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # Создаем и настраиваем элементы для каждой колонки
        time_item = QTableWidgetItem(data['time'])
        time_item.setTextAlignment(Qt.AlignCenter)
        
        name_item = QTableWidgetItem(data['name'])
        name_item.setTextAlignment(Qt.AlignCenter)
        
        group_item = QTableWidgetItem(data['group'])
        group_item.setTextAlignment(Qt.AlignCenter)
        
        lab_item = QTableWidgetItem(data['lab_work'])
        lab_item.setTextAlignment(Qt.AlignCenter)
        
        result_item = QTableWidgetItem(data['result'])
        result_item.setTextAlignment(Qt.AlignCenter)
        
        # Устанавливаем цвет фона для результата
        score = int(data['result'].split('/')[0])
        if score == 5:
            result_item.setBackground(QColor(144, 238, 144))  # Светло-зеленый
        elif score >= 3:
            result_item.setBackground(QColor(255, 255, 153))  # Светло-желтый
        else:
            result_item.setBackground(QColor(255, 182, 193))  # Светло-красный
            
        duration_item = QTableWidgetItem(data['duration'])
        duration_item.setTextAlignment(Qt.AlignCenter)
        
        # Добавляем элементы в таблицу
        self.results_table.setItem(row, 0, time_item)
        self.results_table.setItem(row, 1, name_item)
        self.results_table.setItem(row, 2, group_item)
        self.results_table.setItem(row, 3, lab_item)
        self.results_table.setItem(row, 4, result_item)
        self.results_table.setItem(row, 5, duration_item)
        
        # Прокручиваем к последней строке
        self.results_table.scrollToBottom()
    
    def cleanup_old_results(self):
        """Удаляет самый старый результат каждые 2 часа"""
        if self.results_table.rowCount() > 0:
            self.results_table.removeRow(0)
            # Перенумеровываем индексы в timestamps
            new_timestamps = {}
            for old_row, timestamp in self.results_timestamps.items():
                if old_row > 0:
                    new_timestamps[old_row - 1] = timestamp
            self.results_timestamps = new_timestamps
    
    def append_log(self, message):
        """Добавляет сообщение в лог"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{current_time}] {message}")
        # Прокручиваем до последней строки
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

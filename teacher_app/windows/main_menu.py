from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QApplication
from PyQt5.QtCore import Qt

class MainMenu(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)  # Увеличиваем расстояние между элементами
        layout.setContentsMargins(40, 40, 40, 40)  # Увеличиваем отступы от краев

        header = QLabel("Главное меню")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            margin: 30px;
            color: #2c3e50;
        """)
        layout.addWidget(header)

        # Создаем и стилизуем кнопки
        button_style = """
            QPushButton {
                font-size: 20px;
                padding: 20px 40px;
                min-width: 500px;
                margin: 10px;
                border-radius: 10px;
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2574a9;
            }
        """

        btn_lab_management = QPushButton("Управление лабораторными работами")
        btn_performance_monitor = QPushButton("Мониторинг успеваемости")
        btn_import_export = QPushButton("Импорт/Экспорт лабораторных работ")
        btn_server_control = QPushButton("Управление веб-сервером")
        btn_exit = QPushButton("Выход из приложения")

        # Применяем стили к кнопкам
        for btn in [btn_lab_management, btn_performance_monitor, btn_import_export, 
                   btn_server_control, btn_exit]:
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)  # Меняем курсор при наведении

        layout.addStretch(1)
        layout.addWidget(btn_lab_management, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_performance_monitor, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_import_export, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_server_control, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_exit, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)

        btn_lab_management.clicked.connect(lambda: self.switch_window("lab_management"))
        btn_performance_monitor.clicked.connect(lambda: self.switch_window("performance_monitor"))
        btn_import_export.clicked.connect(lambda: self.switch_window("import_export"))
        btn_server_control.clicked.connect(lambda: self.switch_window("server_control"))
        btn_exit.clicked.connect(self.close_application)

        self.setLayout(layout)
        self.setWindowTitle("Главное меню")
        
        self.resize(800, 600)

    def close_application(self):
        QApplication.quit()

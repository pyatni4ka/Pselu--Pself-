from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from PyQt5.QtCore import Qt

class LabDialog(QDialog):
    def __init__(self, theme="", time=""):
        super().__init__()
        self.init_ui(theme, time)
    
    def init_ui(self, theme, time):
        layout = QVBoxLayout()
    
        header = QLabel("Лабораторная работа")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)
    
        lbl_theme = QLabel("Тема ЛР:")
        self.input_theme = QLineEdit()
        self.input_theme.setText(theme)
        layout.addWidget(lbl_theme)
        layout.addWidget(self.input_theme)
    
        lbl_time = QLabel("Время на выполнение (мин):")
        self.input_time = QLineEdit()
        self.input_time.setText(str(time))
        layout.addWidget(lbl_time)
        layout.addWidget(self.input_time)
    
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")
        btn_save.setFixedHeight(40)
        btn_cancel.setFixedHeight(40)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    
        btn_save.clicked.connect(self.save)
        btn_cancel.clicked.connect(self.reject)
    
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
    
        self.setLayout(layout)
        self.setWindowTitle("Лабораторная работа")
        self.resize(400, 300)
    
    def save(self):
        try:
            theme = self.input_theme.text().strip()
            time_text = self.input_time.text().strip()
            
            if not theme:
                raise ValueError("Тема не может быть пустой.")
            if not time_text.isdigit() or int(time_text) <= 0:
                raise ValueError("Время должно быть положительным числом.")
            
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", f"Некорректный ввод: {e}")
    
    def get_data(self):
        return (
            self.input_theme.text().strip(),
            int(self.input_time.text().strip())
        )

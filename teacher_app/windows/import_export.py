from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QLabel,
    QFileDialog
)
from PyQt5.QtCore import Qt
import sqlite3
import json
import os

class ImportExport(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        header = QLabel("Импорт/Экспорт лабораторных работ")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        btn_import = QPushButton("Импортировать ЛР")
        btn_export = QPushButton("Экспортировать ЛР")
        btn_back = QPushButton("Назад")

        btn_import.setFixedHeight(40)
        btn_export.setFixedHeight(40)
        btn_back.setFixedHeight(40)

        layout.addStretch(1)
        layout.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_export, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_import.clicked.connect(self.import_lab_works)
        btn_export.clicked.connect(self.export_lab_works)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))

        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        self.setLayout(layout)
        self.setWindowTitle("Импорт/Экспорт ЛР")
        self.resize(500, 400)

    def import_lab_works(self):
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импортировать ЛР",
            "",
            "JSON Files (*.json)",
            options=options
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                conn = sqlite3.connect("mgtu_app.db")
                cursor = conn.cursor()
                for lab in data:
                    cursor.execute("""
                        INSERT INTO lab_works (theme, time, question_count)
                        VALUES (?, ?, ?)
                    """, (lab['theme'], lab['time'], lab['question_count']))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Успех", "Лабораторные работы успешно импортированы.")
            except sqlite3.IntegrityError as ie:
                QMessageBox.warning(self, "Ошибка целостности", f"Ошибка целостности данных: {ie}")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось импортировать ЛР:\n{e}")
            except json.JSONDecodeError as je:
                QMessageBox.critical(self, "Ошибка JSON", f"Некорректный формат JSON файла:\n{je}")
            except Exception as ex:
                QMessageBox.critical(self, "Ошибка", f"Произошла неизвестная ошибка:\n{ex}")

    def export_lab_works(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспортировать ЛР",
            "",
            "JSON Files (*.json)"
        )
        if file_name:
            if not file_name.lower().endswith('.json'):
                file_name += '.json'
            try:
                conn = sqlite3.connect("mgtu_app.db")
                cursor = conn.cursor()
                cursor.execute("SELECT theme, time, question_count FROM lab_works")
                records = cursor.fetchall()
                conn.close()
                data = []
                for row in records:
                    data.append({
                        'theme': row[0],
                        'time': row[1],
                        'question_count': row[2]
                    })
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Успех", "Лабораторные работы успешно экспортированы.")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось экспортировать ЛР:\n{e}")
            except IOError as ioe:
                QMessageBox.critical(self, "Ошибка файла", f"Не удалось записать в файл:\n{ioe}")
            except Exception as ex:
                QMessageBox.critical(self, "Ошибка", f"Произошла неизвестная ошибка:\n{ex}")

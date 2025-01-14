from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QLabel,
    QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
import sqlite3
from .lab_dialog import LabDialog
from database import DB_FILE  # Импортируем путь к базе данных

class LabManagement(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Управление лабораторными работами")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            margin: 20px;
            color: #2c3e50;
            padding: 20px;
        """)
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        
        # Создаем заголовки с переносом текста
        header_tema = QTableWidgetItem("Тема ЛР")
        header_time = QTableWidgetItem("Время\n(мин)")
        header_questions = QTableWidgetItem("Кол-во\nвопросов")
        header_id = QTableWidgetItem("ID")

        # Устанавливаем выравнивание для заголовков
        for header in [header_tema, header_time, header_questions, header_id]:
            header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Делаем заголовки некликабельными

        # Устанавливаем заголовки
        self.table.setHorizontalHeaderItem(0, header_tema)
        self.table.setHorizontalHeaderItem(1, header_time)
        self.table.setHorizontalHeaderItem(2, header_questions)
        self.table.setHorizontalHeaderItem(3, header_id)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Устанавливаем стиль таблицы
        self.table.setStyleSheet("""
            QTableWidget {
                font-size: 18px;
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f9f9f9;
                selection-background-color: #3498db;
                selection-color: white;
                border: 1px solid #d0d0d0;
            }
            QTableWidget::item {
                padding: 15px;
                border-bottom: 1px solid #d0d0d0;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                font-size: 18px;
                padding: 10px;
                font-weight: bold;
                border: none;
                min-height: 50px;
                border-right: 1px solid #34495e;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """)

        self.table.setColumnHidden(3, True)
        self.table.horizontalHeader().setStretchLastSection(False)

        # Настраиваем размеры колонок
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        
        # Устанавливаем фиксированные размеры для колонок
        self.table.setColumnWidth(1, 120)  # Уменьшаем ширину колонки "Время"
        self.table.setColumnWidth(2, 120)  # Уменьшаем ширину колонки "Кол-во вопросов"

        # Настраиваем заголовки
        header = self.table.horizontalHeader()
        header.setMinimumHeight(60)  # Увеличиваем минимальную высоту заголовка
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)  # Центрируем текст в заголовках

        # Устанавливаем высоту строк
        self.table.verticalHeader().setDefaultSectionSize(70)
        self.table.verticalHeader().setVisible(False)  # Скрываем номера строк
        
        # Устанавливаем чередующиеся цвета строк
        self.table.setAlternatingRowColors(True)

        # Добавляем отступы вокруг таблицы
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.addWidget(self.table)
        table_layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(table_container)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)  # Увеличиваем расстояние между кнопками
        
        # Стиль для кнопок
        button_style = """
            QPushButton {
                font-size: 16px;
                padding: 15px 30px;
                min-width: 180px;
                margin: 5px;
                border-radius: 8px;
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

        btn_add = QPushButton("Добавить ЛР")
        btn_edit = QPushButton("Редактировать ЛР")
        btn_delete = QPushButton("Удалить ЛР")
        btn_manage_questions = QPushButton("Управление вопросами")
        btn_back = QPushButton("Назад")

        # Применяем стили к кнопкам
        for btn in [btn_add, btn_edit, btn_delete, btn_manage_questions, btn_back]:
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Добавляем кнопки с выравниванием
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_manage_questions)
        btn_layout.addStretch()  # Добавляем растяжку между основными кнопками и кнопкой "Назад"
        btn_layout.addWidget(btn_back)

        layout.addLayout(btn_layout)

        btn_add.clicked.connect(self.add_lab)
        btn_edit.clicked.connect(self.edit_lab)
        btn_delete.clicked.connect(self.delete_lab)
        btn_manage_questions.clicked.connect(self.manage_questions)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))

        self.setLayout(layout)
        self.setWindowTitle("Управление лабораторными работами")
        self.resize(1280, 960)

    def load_data(self):
        try:
            conn = sqlite3.connect(DB_FILE)  # Используем правильный путь
            cursor = conn.cursor()
            cursor.execute("""
                SELECT lab_works.theme, lab_works.time,
                       COUNT(questions.id) as question_count, lab_works.id
                FROM lab_works
                LEFT JOIN questions ON lab_works.id = questions.lab_id
                GROUP BY lab_works.id
            """)
            records = cursor.fetchall()
            self.table.setRowCount(0)
            for row_number, row_data in enumerate(records):
                self.table.insertRow(row_number)
                for column_number in range(3):
                    self.table.setItem(
                        row_number,
                        column_number,
                        QTableWidgetItem(str(row_data[column_number]))
                    )
                self.table.setItem(row_number, 3, QTableWidgetItem(str(row_data[3])))
                self.table.setRowHeight(row_number, 70)
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке данных:\n{e}")

    def add_lab(self):
        dialog = LabDialog()
        if dialog.exec():
            theme, time = dialog.get_data()
            question_count = 0
            try:
                conn = sqlite3.connect(DB_FILE)  # Используем правильный путь
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO lab_works (theme, time, question_count) VALUES (?, ?, ?)",
                    (theme, time, question_count)
                )
                conn.commit()
                conn.close()
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось добавить лабораторную работу:\n{e}")

    def edit_lab(self):
        selected = self.table.currentRow()
        if selected >= 0:
            lab_id_item = self.table.item(selected, 3)
            if lab_id_item is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить идентификатор лабораторной работы.")
                return
            lab_id = lab_id_item.text()
            theme = self.table.item(selected, 0).text()
            time = self.table.item(selected, 1).text()

            dialog = LabDialog(theme, time)
            if dialog.exec():
                new_theme, new_time = dialog.get_data()
                try:
                    conn = sqlite3.connect(DB_FILE)  # Используем правильный путь
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE lab_works SET theme=?, time=? WHERE id=?",
                        (new_theme, new_time, lab_id)
                    )
                    conn.commit()
                    conn.close()
                    self.load_data()
                except sqlite3.Error as e:
                    QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось обновить лабораторную работу:\n{e}")
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите лабораторную работу для редактирования.")

    def delete_lab(self):
        selected = self.table.currentRow()
        if selected >= 0:
            lab_id_item = self.table.item(selected, 3)
            if lab_id_item is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить идентификатор лабораторной работы.")
                return
            lab_id = lab_id_item.text()
            theme = self.table.item(selected, 0).text()

            reply = QMessageBox.question(
                self,
                'Подтверждение',
                f"Вы уверены, что хотите удалить ЛР с ID '{lab_id}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    conn = sqlite3.connect(DB_FILE)  # Используем правильный путь
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM lab_works WHERE id=?", (lab_id,))
                    conn.commit()
                    conn.close()
                    self.load_data()
                except sqlite3.Error as e:
                    QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось удалить лабораторную работу:\n{e}")
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите лабораторную работу для удаления.")

    def manage_questions(self):
        selected = self.table.currentRow()
        if selected >= 0:
            lab_id_item = self.table.item(selected, 3)
            if lab_id_item is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить идентификатор лабораторной работы.")
                return
            lab_id = lab_id_item.text()
            self.switch_window("questions_management", data=lab_id)
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите лабораторную работу для управления вопросами.")

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

class LabManagement(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        header = QLabel("Управление лабораторными работами")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Тема ЛР", "Время (мин)", "Кол-во вопросов", "ID"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #FFE5B4;  /* Светло-персиковый фон при выделении */
                color: #000000;             /* Текст чёрный */
                border: 1px solid #FFA500;  /* Оранжевая рамка вокруг выделенной ячейки */
            }
        """)

        self.table.setColumnHidden(3, True)

        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 150)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить ЛР")
        btn_edit = QPushButton("Редактировать ЛР")
        btn_delete = QPushButton("Удалить ЛР")
        btn_manage_questions = QPushButton("Управление вопросами")
        btn_back = QPushButton("Назад")

        for btn in (btn_add, btn_edit, btn_delete, btn_manage_questions, btn_back):
            btn.setFixedHeight(40)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_manage_questions)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_add.clicked.connect(self.add_lab)
        btn_edit.clicked.connect(self.edit_lab)
        btn_delete.clicked.connect(self.delete_lab)
        btn_manage_questions.clicked.connect(self.manage_questions)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))

        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)

        self.setLayout(layout)
        self.setWindowTitle("Управление лабораторными работами")
        self.resize(800, 600)

    def load_data(self):
        try:
            conn = sqlite3.connect("mgtu_app.db")
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
                self.table.setRowHeight(row_number, 20)
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке данных:\n{e}")

    def add_lab(self):
        dialog = LabDialog()
        if dialog.exec():
            theme, time = dialog.get_data()
            question_count = 0
            try:
                conn = sqlite3.connect("mgtu_app.db")
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
                    conn = sqlite3.connect("mgtu_app.db")
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
                    conn = sqlite3.connect("mgtu_app.db")
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

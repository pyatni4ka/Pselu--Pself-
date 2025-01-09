from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QMessageBox, QLabel, QComboBox, QHeaderView, QInputDialog, QLineEdit, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class EditStudentDialog(QDialog):
    def __init__(self, first_name, last_name, middle_name, group_name, year):
        super().__init__()
        self.init_ui(first_name, last_name, middle_name, group_name, year)

    def init_ui(self, first_name, last_name, middle_name, group_name, year):
        layout = QVBoxLayout()

        lbl_first_name = QLabel("Имя:")
        self.edit_first_name = QLineEdit(first_name)
        layout.addWidget(lbl_first_name)
        layout.addWidget(self.edit_first_name)

        lbl_last_name = QLabel("Фамилия:")
        self.edit_last_name = QLineEdit(last_name)
        layout.addWidget(lbl_last_name)
        layout.addWidget(self.edit_last_name)

        lbl_middle_name = QLabel("Отчество (опционально):")
        self.edit_middle_name = QLineEdit(middle_name)
        layout.addWidget(lbl_middle_name)
        layout.addWidget(self.edit_middle_name)

        lbl_group_name = QLabel("Группа:")
        self.edit_group_name = QLineEdit(group_name)
        layout.addWidget(lbl_group_name)
        layout.addWidget(self.edit_group_name)

        lbl_year = QLabel("Год:")
        self.edit_year = QLineEdit(year)
        layout.addWidget(lbl_year)
        layout.addWidget(self.edit_year)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")
        btn_save.clicked.connect(self.save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        self.setWindowTitle("Изменение студента")
        self.resize(400, 300)

    def save(self):
        first_name = self.edit_first_name.text().strip()
        last_name = self.edit_last_name.text().strip()
        middle_name = self.edit_middle_name.text().strip()
        group_name = self.edit_group_name.text().strip()
        year = self.edit_year.text().strip()

        if not first_name or not last_name or not group_name or not year:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните обязательные поля (Имя, Фамилия, Группа, Год).")
            return

        if not year.isdigit():
            QMessageBox.warning(self, "Ошибка", "Год должен быть числом.")
            return

        self.accept()

    def get_data(self):
        return (
            self.edit_first_name.text().strip(),
            self.edit_last_name.text().strip(),
            self.edit_middle_name.text().strip(),
            self.edit_group_name.text().strip(),
            int(self.edit_year.text().strip())
        )

class PerformanceMonitor(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.load_years()
        self.load_groups()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        header = QLabel("Мониторинг успеваемости")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        year_layout = QHBoxLayout()
        lbl_year = QLabel("Год:")
        self.combo_year = QComboBox()
        self.combo_year.currentIndexChanged.connect(self.load_data)
        year_layout.addWidget(lbl_year)
        year_layout.addWidget(self.combo_year)
        year_layout.addStretch()
        layout.addLayout(year_layout)

        group_layout = QHBoxLayout()
        lbl_group = QLabel("Группа:")
        self.combo_group = QComboBox()
        self.combo_group.currentIndexChanged.connect(self.load_data)
        group_layout.addWidget(lbl_group)
        group_layout.addWidget(self.combo_group)
        group_layout.addStretch()
        layout.addLayout(group_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ФИО", "Группа", "Год", "Средний балл"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("Обновить")
        btn_show_chart = QPushButton("Показать график")
        btn_back = QPushButton("Назад")
        btn_refresh.setFixedHeight(40)
        btn_show_chart.setFixedHeight(40)
        btn_back.setFixedHeight(40)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_show_chart)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_manage_layout = QHBoxLayout()
        btn_edit_student = QPushButton("Изменить студента")
        btn_delete_student = QPushButton("Удалить студента")
        btn_delete_all_students = QPushButton("Удалить всех студентов")
        btn_edit_student.setFixedHeight(40)
        btn_delete_student.setFixedHeight(40)
        btn_delete_all_students.setFixedHeight(40)
        btn_manage_layout.addWidget(btn_edit_student)
        btn_manage_layout.addWidget(btn_delete_student)
        btn_manage_layout.addWidget(btn_delete_all_students)
        layout.addLayout(btn_manage_layout)

        btn_refresh.clicked.connect(self.load_data)
        btn_show_chart.clicked.connect(self.show_chart)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))
        btn_edit_student.clicked.connect(self.edit_student)
        btn_delete_student.clicked.connect(self.delete_student)
        btn_delete_all_students.clicked.connect(self.delete_all_students)

        self.figure = plt.figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.canvas.hide()

        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)
        self.setLayout(layout)
        self.setWindowTitle("Мониторинг успеваемости")
        self.resize(800, 600)

    def load_years(self):
        try:
            conn = sqlite3.connect("mgtu_app.db")
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT year FROM students ORDER BY year DESC")
            rows = cursor.fetchall()
            conn.close()

            self.combo_year.blockSignals(True)
            self.combo_year.clear()
            self.combo_year.addItem("Все годы")
            if rows:
                for r in rows:
                    self.combo_year.addItem(str(r[0]))
            else:
                print("Нет данных для отображения годов.")
            self.combo_year.blockSignals(False)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке списка лет: {e}")

    def load_groups(self):
        try:
            conn = sqlite3.connect("mgtu_app.db")
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT group_name FROM students ORDER BY group_name ASC")
            groups = cursor.fetchall()
            conn.close()

            self.combo_group.blockSignals(True)
            self.combo_group.clear()
            self.combo_group.addItem("Все группы")
            if groups:
                for group in groups:
                    self.combo_group.addItem(group[0])
            else:
                print("Нет данных для отображения групп.")
            self.combo_group.blockSignals(False)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке групп: {e}")

    def load_data(self):
        selected_year = self.combo_year.currentText()
        selected_group = self.combo_group.currentText()
        try:
            conn = sqlite3.connect("mgtu_app.db")
            cursor = conn.cursor()

            base_query = """
                SELECT
                    s.id,
                    s.last_name || ' ' || s.first_name || ' ' || COALESCE(s.middle_name, '') as full_name,
                    s.group_name,
                    s.year,
                    IFNULL(ROUND(AVG(r.score), 2), 'N/A') as average_score
                FROM students s
                LEFT JOIN results r ON s.id = r.student_id
            """
            where_clauses = []
            params = []

            if selected_year != "Все годы":
                where_clauses.append("s.year = ?")
                params.append(int(selected_year))
            if selected_group != "Все группы":
                where_clauses.append("s.group_name = ?")
                params.append(selected_group)

            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)

            base_query += """
                GROUP BY s.id
                ORDER BY s.year DESC, s.last_name ASC, s.first_name ASC
            """

            cursor.execute(base_query, params)
            records = cursor.fetchall()
            conn.close()

            self.table.setRowCount(0)
            if records:
                for row_number, row_data in enumerate(records):
                    student_id = row_data[0]
                    full_name = row_data[1]
                    group_name = row_data[2]
                    year = row_data[3] if row_data[3] is not None else ""
                    avg_score = row_data[4] if row_data[4] != 'N/A' else "N/A"

                    self.table.insertRow(row_number)
                    item = QTableWidgetItem(full_name)
                    item.setData(Qt.ItemDataRole.UserRole, student_id)  # Сохраняем ID
                    self.table.setItem(row_number, 0, item)
                    self.table.setItem(row_number, 1, QTableWidgetItem(group_name))
                    self.table.setItem(row_number, 2, QTableWidgetItem(str(year)))
                    self.table.setItem(row_number, 3, QTableWidgetItem(str(avg_score)))
            else:
                print("Нет данных для отображения студентов.")
            self.canvas.hide()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке данных: {e}")

    def show_chart(self):
        selected_year = self.combo_year.currentText()
        selected_group = self.combo_group.currentText()
        try:
            conn = sqlite3.connect("mgtu_app.db")
            cursor = conn.cursor()

            query = """
                SELECT s.year, ROUND(SUM(r.score) / NULLIF(COUNT(r.lab_id), 0), 2) as average_score
                FROM students s
                LEFT JOIN results r ON s.id = r.student_id
            """
            where_clauses = []
            params = []

            if selected_year != "Все годы":
                where_clauses.append("s.year = ?")
                params.append(int(selected_year))
            if selected_group != "Все группы":
                where_clauses.append("s.group_name = ?")
                params.append(selected_group)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += """
                GROUP BY s.year
                ORDER BY s.year DESC
            """

            cursor.execute(query, params)
            data = cursor.fetchall()
            conn.close()

            years = [row[0] for row in data if row[0] is not None]
            scores = [row[1] if row[1] is not None else 0 for row in data]

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            bars = ax.bar([str(y) for y in years], scores, color='skyblue')
            ax.set_xlabel('Год')
            ax.set_ylabel('Средний балл')
            ax.set_title('Средний балл по годам (фильтр по группе/году)')

            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height, f'{score:.2f}', ha='center', va='bottom')

            self.canvas.draw()
            self.canvas.show()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при загрузке данных для графика.\n{e}")

    def edit_student(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите студента для изменения.")
            return

        row = self.table.currentRow()
        student_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) 

        full_name = self.table.item(row, 0).text().split()
        group_name = self.table.item(row, 1).text()
        year = self.table.item(row, 2).text()

        first_name = full_name[1]
        last_name = full_name[0]
        middle_name = full_name[2] if len(full_name) > 2 else ""

        dialog = EditStudentDialog(first_name, last_name, middle_name, group_name, year)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_first_name, new_last_name, new_middle_name, new_group_name, new_year = dialog.get_data()
            try:
                conn = sqlite3.connect("mgtu_app.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE students
                    SET first_name = ?, last_name = ?, middle_name = ?, group_name = ?, year = ?
                    WHERE id = ?
                """, (new_first_name, new_last_name, new_middle_name, new_group_name, new_year, student_id))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Успех", "Данные студента успешно обновлены.")
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при обновлении данных студента.\n{e}")


    def delete_student(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите студента для удаления.")
            return

        row = self.table.currentRow()
        full_name = self.table.item(row, 0).text().split()
        group_name = self.table.item(row, 1).text()
        year = self.table.item(row, 2).text()

        first_name = full_name[1]
        last_name = full_name[0]

        confirmation = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить студента {last_name} {first_name} из группы {group_name} ({year})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect("mgtu_app.db")
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM students
                    WHERE first_name = ? AND last_name = ? AND group_name = ? AND year = ?
                """, (first_name, last_name, group_name, year))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Успех", "Студент успешно удален.")
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при удалении студента.\n{e}")

    def delete_all_students(self):
        confirmation = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить всех студентов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect("mgtu_app.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM students")
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Успех", "Все студенты успешно удалены.")
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при удалении всех студентов.\n{e}")

    def get_input(self, message, default_value="", optional=False, numeric=False):
        text, ok = QInputDialog.getText(self, "Изменение данных", message, QLineEdit.EchoMode.Normal, default_value)
        if ok:
            if numeric and not text.isdigit():
                QMessageBox.warning(self, "Ошибка", "Значение должно быть числом.")
                return None, False
            return text.strip(), True
        elif optional:
            return "", True
        return None, False


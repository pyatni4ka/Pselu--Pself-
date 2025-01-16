from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QMessageBox, QLabel, QLineEdit, QDialog, QHeaderView
)
from PyQt5.QtCore import Qt
import sqlite3
from database import get_connection

class AddStudentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        header = QLabel("Добавить студента")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Фамилия
        lbl_last_name = QLabel("Фамилия:")
        self.edit_last_name = QLineEdit()
        layout.addWidget(lbl_last_name)
        layout.addWidget(self.edit_last_name)

        # Имя
        lbl_first_name = QLabel("Имя:")
        self.edit_first_name = QLineEdit()
        layout.addWidget(lbl_first_name)
        layout.addWidget(self.edit_first_name)

        # Группа
        lbl_group = QLabel("Группа:")
        self.edit_group = QLineEdit()
        layout.addWidget(lbl_group)
        layout.addWidget(self.edit_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")
        
        btn_save.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.setWindowTitle("Добавить студента")
        self.setFixedWidth(400)

    def get_data(self):
        return {
            'first_name': self.edit_first_name.text().strip(),
            'last_name': self.edit_last_name.text().strip(),
            'group_name': self.edit_group.text().strip()
        }

class StudentManagement(QWidget):
    def __init__(self, switch_window):
        super().__init__()
        self.switch_window = switch_window
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Заголовок
        header = QLabel("Управление студентами")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Фамилия", "Имя", "Группа"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        
        self.table.setColumnWidth(2, 150)
        
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("Добавить")
        btn_edit = QPushButton("Редактировать")
        btn_delete = QPushButton("Удалить")
        btn_back = QPushButton("Назад")
        
        btn_add.clicked.connect(self.add_student)
        btn_edit.clicked.connect(self.edit_student)
        btn_delete.clicked.connect(self.delete_student)
        btn_back.clicked.connect(lambda: self.switch_window("main_menu"))
        
        for btn in [btn_add, btn_edit, btn_delete, btn_back]:
            btn.setFixedHeight(40)
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_data(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, last_name, first_name, group_name
                FROM students
                ORDER BY last_name, first_name
            """)
            students = cursor.fetchall()
            
            self.table.setRowCount(len(students))
            for i, student in enumerate(students):
                for j in range(1, 4):  # Пропускаем id
                    item = QTableWidgetItem(str(student[j]))
                    item.setData(Qt.UserRole, student[0])  # Сохраняем ID студента
                    self.table.setItem(i, j-1, item)

            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}")

    def add_student(self):
        dialog = AddStudentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['first_name'] or not data['last_name'] or not data['group_name']:
                QMessageBox.warning(self, "Ошибка", "Все поля обязательны для заполнения")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO students (first_name, last_name, group_name)
                    VALUES (?, ?, ?)
                """, (
                    data['first_name'],
                    data['last_name'],
                    data['group_name']
                ))
                conn.commit()
                conn.close()
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить студента: {str(e)}")

    def edit_student(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите студента для редактирования")
            return

        student_id = self.table.item(current_row, 0).data(Qt.UserRole)
        student_data = {
            'last_name': self.table.item(current_row, 0).text(),
            'first_name': self.table.item(current_row, 1).text(),
            'group_name': self.table.item(current_row, 2).text()
        }

        dialog = AddStudentDialog(self)
        dialog.edit_last_name.setText(student_data['last_name'])
        dialog.edit_first_name.setText(student_data['first_name'])
        dialog.edit_group.setText(student_data['group_name'])

        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            if not new_data['first_name'] or not new_data['last_name'] or not new_data['group_name']:
                QMessageBox.warning(self, "Ошибка", "Все поля обязательны для заполнения")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE students 
                    SET first_name = ?, last_name = ?, group_name = ?
                    WHERE id = ?
                """, (
                    new_data['first_name'],
                    new_data['last_name'],
                    new_data['group_name'],
                    student_id
                ))
                conn.commit()
                conn.close()
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить данные студента: {str(e)}")

    def delete_student(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите студента для удаления")
            return

        student_id = self.table.item(current_row, 0).data(Qt.UserRole)
        student_name = f"{self.table.item(current_row, 0).text()} {self.table.item(current_row, 1).text()}"

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите удалить студента {student_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Удаляем все связанные записи
                cursor.execute("DELETE FROM completed_labs WHERE student_id = ?", (student_id,))
                cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
                
                conn.commit()
                conn.close()
                self.load_data()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить студента: {str(e)}")

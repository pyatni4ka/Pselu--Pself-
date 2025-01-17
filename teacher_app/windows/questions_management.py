from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QHeaderView,
    QLabel,
    QComboBox,
    QLineEdit
)
from PyQt5.QtCore import Qt
import sqlite3
from .question_dialog import QuestionDialog
import logging
from database import DB_FILE

logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

class QuestionsManagement(QWidget):
    def __init__(self, switch_window, lab_id):
        super().__init__()
        self.switch_window = switch_window
        self.lab_id = lab_id
        self.last_used_category = "Вопрос 1"  # Значение по умолчанию
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Управление вопросами")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            margin: 20px;
            color: #2c3e50;
            padding: 20px;
        """)
        layout.addWidget(header)

        # Верхняя панель с фильтром и поиском
        top_panel = QHBoxLayout()

        # Левая часть - фильтр по типу
        filter_layout = QHBoxLayout()
        lbl_filter = QLabel("Фильтр по типу:")
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("Все")
        self.combo_filter.addItem("Вопрос 1")
        self.combo_filter.addItem("Вопрос 2")
        self.combo_filter.addItem("Вопрос 3")
        self.combo_filter.addItem("Вопрос 4")
        self.combo_filter.addItem("Вопрос 5")
        self.combo_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(lbl_filter)
        filter_layout.addWidget(self.combo_filter)
        
        # Правая часть - поиск
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по номеру или тексту вопроса...")
        self.search_input.textChanged.connect(self.filter_questions)
        self.search_input.setFixedWidth(300)  # Фиксированная ширина поля поиска
        search_layout.addWidget(self.search_input)
        search_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Добавляем фильтр и поиск в верхнюю панель
        top_panel.addLayout(filter_layout)
        top_panel.addStretch()  # Растягиваем пространство между фильтром и поиском
        top_panel.addLayout(search_layout)
        
        layout.addLayout(top_panel)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Номер\nвопроса", "Вопрос", "Категория", "Правильный\nответ", "ID"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnHidden(4, True)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить вопрос")
        btn_edit = QPushButton("Редактировать вопрос")
        btn_delete = QPushButton("Удалить вопрос")
        btn_back = QPushButton("Назад")

        btn_add.setFixedHeight(40)
        btn_edit.setFixedHeight(40)
        btn_delete.setFixedHeight(40)
        btn_back.setFixedHeight(40)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_back)

        layout.addLayout(btn_layout)

        btn_add.clicked.connect(self.add_question)
        btn_edit.clicked.connect(self.edit_question)
        btn_delete.clicked.connect(self.delete_question)
        btn_back.clicked.connect(lambda: self.switch_window("lab_management"))

        self.setLayout(layout)
        self.setWindowTitle("Управление вопросами")
        self.resize(900, 600)

    def load_data(self):
        selected_category = self.combo_filter.currentText()
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            query = """
                SELECT 
                    question_number,
                    question_text,
                    category,
                    correct_index,
                    id,
                    CAST(SUBSTR(question_number, INSTR(question_number, '.') + 1) AS INTEGER) as sort_number
                FROM questions
                WHERE lab_id=?
            """
            params = [self.lab_id]

            if selected_category != "Все":
                query += " AND category = ?"
                params.append(selected_category)

            query += " ORDER BY category ASC, sort_number ASC"
            cursor.execute(query, params)

            records = cursor.fetchall()
            self.table.setRowCount(0)
            for row_number, row_data in enumerate(records):
                self.table.insertRow(row_number)
                for column_number in range(4):
                    cell_data = row_data[column_number] if row_data[column_number] else ""
                    item = QTableWidgetItem(str(cell_data))
                    if column_number in [0, 2, 3]:  # номер вопроса, категория, правильный ответ
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_number, column_number, item)
                self.table.setItem(row_number, 4, QTableWidgetItem(str(row_data[4])))
                self.table.setRowHeight(row_number, 30)  # Устанавливаем высоту для каждой строки
            conn.close()
            logger.info(f"Загружены {len(records)} вопросов для ЛР ID {self.lab_id}.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Произошла ошибка при подключении к базе данных:\n{e}")
            logger.error("Ошибка при загрузке данных вопросов.", exc_info=True)

    def get_next_question_number(self, category):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT question_number
                FROM questions
                WHERE lab_id = ? AND category = ?
                ORDER BY CAST(SUBSTR(question_number, INSTR(question_number, '.') + 1) AS INTEGER) DESC
                LIMIT 1
            """, (self.lab_id, category))
            result = cursor.fetchone()
            conn.close()

            if result:
                # Если есть существующие вопросы, берем последний номер и увеличиваем на 1
                last_number = result[0]
                base_number = category.split()[-1]  # Получаем номер из категории (например, "1" из "Вопрос 1")
                current_number = int(last_number.split('.')[-1])  # Получаем число после точки
                return f"{base_number}.{current_number + 1}"
            else:
                # Если вопросов нет, начинаем с .1
                base_number = category.split()[-1]
                return f"{base_number}.1"
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении следующего номера вопроса: {e}", exc_info=True)
            return "1.1"  # Возвращаем значение по умолчанию в случае ошибки

    def add_question(self):
        # Используем последнюю категорию или текущий фильтр, если он не "Все"
        selected_category = self.combo_filter.currentText()
        if selected_category == "Все":
            selected_category = self.last_used_category
        
        next_number = self.get_next_question_number(selected_category)
        dialog = QuestionDialog(selected_category, next_number)
        dialog.parent_window = self
        if dialog.exec():
            category, question_number, question_text, a1, a2, a3, a4, correct_idx = dialog.get_data()
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO questions 
                    (lab_id, category, question_number, question_text, answer1, answer2, answer3, answer4, correct_index) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.lab_id, category, question_number, question_text, a1, a2, a3, a4, correct_idx))
                conn.commit()
                
                # Обновляем счетчик вопросов в лабораторной работе
                cursor.execute("SELECT COUNT(*) FROM questions WHERE lab_id=?", (self.lab_id,))
                count = cursor.fetchone()[0]
                cursor.execute("UPDATE lab_works SET question_count=? WHERE id=?", (count, self.lab_id))
                conn.commit()
                conn.close()
                
                # Сохраняем использованную категорию
                self.last_used_category = category
                
                # Всегда переключаем фильтр на категорию созданного вопроса
                index = self.combo_filter.findText(category)
                if index >= 0:
                    self.combo_filter.setCurrentIndex(index)
                    self.load_data()  # Обновляем данные после переключения фильтра
                else:
                    self.load_data()  # Если категория не найдена, просто обновляем данные
                
                logger.info(f"Добавлен новый вопрос в ЛР ID {self.lab_id}. Всего {count} вопросов.")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось добавить вопрос:\n{e}")
                logger.error("Ошибка при добавлении вопроса.", exc_info=True)

    def edit_question(self):
        selected = self.table.currentRow()
        if selected >= 0:
            id_item = self.table.item(selected, 4)
            if not id_item or not id_item.text():
                QMessageBox.warning(self, "Ошибка", "Не удалось получить идентификатор вопроса.")
                return
            question_id = id_item.text()
            conn = sqlite3.connect(DB_FILE)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, question_number, question_text, answer1, answer2, answer3, answer4, correct_index
                    FROM questions
                    WHERE id=?
                """, (question_id,))
                row = cursor.fetchone()
                conn.close()
                if not row:
                    QMessageBox.warning(self, "Ошибка", "Вопрос не найден в базе.")
                    return
                cat, qn, qt, ans1, ans2, ans3, ans4, cidx = row
                dialog = QuestionDialog(cat, qn, qt, ans1, ans2, ans3, ans4, cidx)  # Правильный порядок: категория, номер, текст, ответы, индекс
                if dialog.exec():
                    category, question_number, question_text, a1n, a2n, a3n, a4n, correct_idx = dialog.get_data()
                    conn2 = sqlite3.connect(DB_FILE)
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        UPDATE questions
                        SET category=?,
                            question_number=?,
                            question_text=?,
                            answer1=?,
                            answer2=?,
                            answer3=?,
                            answer4=?,
                            correct_index=?
                        WHERE id=?
                    """, (category, question_number, question_text, a1n, a2n, a3n, a4n, correct_idx, question_id))
                    conn2.commit()
                    conn2.close()
                    self.load_data()
                    logger.info(f"Вопрос ID {question_id} успешно обновлен.")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось загрузить/обновить вопрос:\n{e}")
                logger.error(f"Ошибка при обновлении вопроса ID {question_id}.", exc_info=True)
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите вопрос для редактирования.")

    def delete_question(self):
        selected = self.table.currentRow()
        if selected >= 0:
            id_item = self.table.item(selected, 4)
            if not id_item or not id_item.text():
                QMessageBox.warning(self, "Ошибка", "Не удалось получить идентификатор вопроса.")
                return
            question_id = int(id_item.text())
            question_text = self.table.item(selected, 1).text()
            reply = QMessageBox.question(
                self,
                'Подтверждение',
                f"Вы уверены, что хотите удалить вопрос:\n\"{question_text}\"?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM questions WHERE id=?", (question_id,))
                    conn.commit()
                    cursor.execute("SELECT COUNT(*) FROM questions WHERE lab_id=?", (self.lab_id,))
                    count = cursor.fetchone()[0]
                    cursor.execute("UPDATE lab_works SET question_count=? WHERE id=?", (count, self.lab_id))
                    conn.commit()
                    conn.close()
                    self.load_data()
                    logger.info(f"Вопрос ID {question_id} удален. Всего {count} вопросов осталось.")
                except sqlite3.Error as e:
                    QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось удалить вопрос:\n{e}")
                    logger.error(f"Ошибка при удалении вопроса ID {question_id}.", exc_info=True)
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите вопрос для удаления.")

    def filter_questions(self, search_text):
        search_text = search_text.lower()
        for row in range(self.table.rowCount()):
            show_row = False
            # Проверяем номер вопроса (колонка 0)
            question_number = self.table.item(row, 0).text().lower()
            # Проверяем текст вопроса (колонка 1)
            question_text = self.table.item(row, 1).text().lower()
            
            # Показываем строку, если текст поиска найден в номере или тексте вопроса
            if search_text in question_number or search_text in question_text:
                show_row = True
                
            self.table.setRowHidden(row, not show_row)

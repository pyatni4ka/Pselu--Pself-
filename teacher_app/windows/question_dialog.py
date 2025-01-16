from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFileDialog, QMessageBox, QLineEdit, QTextEdit, QVBoxLayout, QGridLayout
)
from PyQt6.QtCore import Qt, QStandardPaths, QMimeData
from PyQt6.QtGui import QGuiApplication, QDragEnterEvent, QDropEvent
import os
import uuid

class ImageTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source: QMimeData):
        if source.hasImage():
            image = source.imageData()
            if image:
                self._save_and_insert_image(image)
            else:
                super().insertFromMimeData(source)
        else:
            super().insertFromMimeData(source)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasImage():
            image = event.mimeData().imageData()
            if image:
                self._save_and_insert_image(image)
                event.acceptProposedAction()
            else:
                super().dropEvent(event)
        else:
            super().dropEvent(event)

    def _save_and_insert_image(self, qimage):
        unique_name = str(uuid.uuid4()) + ".png"
        temp_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, unique_name)
        if not qimage.save(file_path, "PNG"):
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить изображение.")
            return
        self.insertHtml(f'<br><img src="{file_path}" width="200"/><br>')
        self.insertPlainText(f'![image]({file_path})\n')

class QuestionDialog(QDialog):
    def __init__(self, category="", question_number="", question_text="", answer1="", answer2="", answer3="", answer4="", correct_idx=1):
        super().__init__()
        self.parent_window = None  # Будет установлено из QuestionsManagement
        self.init_ui(category, question_number, question_text, answer1, answer2, answer3, answer4, correct_idx)

    def init_ui(self, category, question_number, question_text, ans1, ans2, ans3, ans4, correct_idx):
        layout = QVBoxLayout()

        # Add question number input
        lbl_question_number = QLabel("Номер вопроса:")
        self.input_question_number = QLineEdit()
        self.input_question_number.setText(question_number)
        layout.addWidget(lbl_question_number)
        layout.addWidget(self.input_question_number)

        # Add category selection
        lbl_category = QLabel("Категория:")
        self.combo_category = QComboBox()
        categories = ["Вопрос 1", "Вопрос 2", "Вопрос 3", "Вопрос 4", "Вопрос 5"]
        self.combo_category.addItems(categories)
        idx = self.combo_category.findText(category)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)
        self.combo_category.currentTextChanged.connect(self.update_question_number)
        layout.addWidget(lbl_category)
        layout.addWidget(self.combo_category)

        lbl_question = QLabel("Вопрос:")
        self.text_question = ImageTextEdit()
        self.text_question.setPlainText(question_text)
        btn_paste_q = QPushButton("Вставить из буфера (вопрос)")
        btn_paste_q.clicked.connect(lambda: self.paste_image_into_textedit(self.text_question))
        layout.addWidget(lbl_question)
        layout.addWidget(self.text_question)
        layout.addWidget(btn_paste_q)

        lbl_answers = QLabel("Ответы:")
        answers_grid = QGridLayout()
        self.answers_edits = []

        for i, ans_text in enumerate([ans1, ans2, ans3, ans4], start=1):
            lbl_ans = QLabel(f"Вариант {i}:")
            text_ans = ImageTextEdit()
            text_ans.setPlainText(str(ans_text))
            btn_paste_a = QPushButton("Вставить из буфера")
            btn_paste_a.clicked.connect(self.create_paste_handler(text_ans))

            row, col = divmod(i - 1, 2)
            answers_grid.addWidget(lbl_ans, row * 3, col)
            answers_grid.addWidget(text_ans, row * 3 + 1, col)
            answers_grid.addWidget(btn_paste_a, row * 3 + 2, col)

            self.answers_edits.append(text_ans)

        layout.addWidget(lbl_answers)
        layout.addLayout(answers_grid)

        lbl_correct = QLabel("Правильный вариант (1-4):")
        self.combo_correct = QComboBox()
        self.combo_correct.addItems(["1", "2", "3", "4"])
        if 1 <= correct_idx <= 4:
            self.combo_correct.setCurrentIndex(correct_idx - 1)
        layout.addWidget(lbl_correct)
        layout.addWidget(self.combo_correct)

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
        self.setWindowTitle("Редактирование вопроса")
        self.resize(500, 700)

    def paste_image_into_textedit(self, text_edit):
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            img = clipboard.image()
            if not img.isNull():
                text_edit._save_and_insert_image(img)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить изображение из буфера.")
        else:
            QMessageBox.warning(self, "Ошибка", "В буфере нет изображения.")

    def create_paste_handler(self, text_edit):
        def handler():
            self.paste_image_into_textedit(text_edit)
        return handler

    def update_question_number(self, category_text):
        if hasattr(self, 'parent_window') and self.parent_window:
            next_number = self.parent_window.get_next_question_number(category_text)
            self.input_question_number.setText(next_number)

    def save(self):
        try:
            category = self.combo_category.currentText()
            question_text = self.text_question.toPlainText().strip()
            answers = [te.toPlainText().strip() for te in self.answers_edits]
            correct_idx = self.combo_correct.currentIndex() + 1
            question_number = self.input_question_number.text().strip()
            if not question_text:
                raise ValueError("Вопрос не может быть пустым.")
            if any(not a for a in answers):
                raise ValueError("Все 4 варианта ответов должны быть заполнены.")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def get_data(self):
        return (
            self.combo_category.currentText(),
            self.input_question_number.text().strip(),
            self.text_question.toPlainText().strip(),
            self.answers_edits[0].toPlainText().strip(),
            self.answers_edits[1].toPlainText().strip(),
            self.answers_edits[2].toPlainText().strip(),
            self.answers_edits[3].toPlainText().strip(),
            self.combo_correct.currentIndex() + 1
        )

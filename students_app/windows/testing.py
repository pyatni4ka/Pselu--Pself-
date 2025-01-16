"""
Модуль тестирования студентов.

Реализует интерфейс для прохождения тестирования по лабораторным работам.
Включает в себя таймер, навигацию по вопросам и отправку ответов.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, 
    QHBoxLayout, QRadioButton, QButtonGroup, QGridLayout, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThreadPool
from PyQt5.QtGui import QPixmap, QFont
import os
import random
import requests
import logging
from .network_workers import Worker
import re
import uuid

def parse_images(text: str, server_url: str = "http://localhost:8080/images") -> tuple[str, list[str]]:
    pattern = r'!\[image\]\((.*?)\)'
    matches = re.findall(pattern, text)
    text_without_images = re.sub(pattern, '', text).replace('\ufffc', '').strip()
    urls = [f"{server_url}/{match}" for match in matches]
    return text_without_images, urls

class ImageViewer(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Просмотр изображения")
        self.setMinimumSize(600, 600)
        layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(image_path).scaled(
            600, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(pixmap)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

class TestingWindow(QWidget):
    """
    Окно тестирования.
    
    Attributes:
        switch_window (function): Функция для переключения окон
        get_student_id (function): Функция получения ID студента
        questions (list): Список вопросов
        current_question (int): Индекс текущего вопроса
        answers (dict): Словарь ответов студента
        timer (QTimer): Таймер тестирования
        time_left (int): Оставшееся время
        thread_pool (QThreadPool): Пул потоков для асинхронных запросов
    """
    def __init__(self, switch_window, get_student_id):
        super().__init__()
        self.switch_window = switch_window
        self.get_student_id = get_student_id
        self.init_ui()
        self.questions = []
        self.selected_questions = []
        self.current_question = 0
        self.lab_id = None
        self.user_answers = {}
        self.time_limit = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.remaining_time = 0
        self.thread_pool = QThreadPool()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.header = QLabel("Тестирование")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.layout.addWidget(self.header)

        self.timer_label = QLabel("Оставшееся время: --:--")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.timer_label)

        self.question_label = QLabel()
        self.question_label.setWordWrap(True)
        self.layout.addWidget(self.question_label)

        self.answers_grid = QGridLayout()
        self.answer_group = QButtonGroup(self)
        self.answers_widgets = []
        
        self.setStyleSheet("""
            QRadioButton::indicator {
                width: 22px;
                height: 22px;
            }
            QRadioButton {
                font-size: 14px;
            }
        """)

        for i in range(4):
            rb = QRadioButton()
            self.answer_group.addButton(rb, i)
            txt_label = QLabel()
            txt_label.setWordWrap(True)
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.mousePressEvent = lambda e, img_label=img_label: self.open_image_viewer(img_label.pixmap())
            vbox = QVBoxLayout()
            vbox.addWidget(rb)
            vbox.addWidget(txt_label)
            vbox.addWidget(img_label)
            self.answers_widgets.append((rb, txt_label, img_label))

        self.answers_grid.addLayout(self._wrap_layout(self.answers_widgets[0]), 0, 0)
        self.answers_grid.addLayout(self._wrap_layout(self.answers_widgets[2]), 0, 1)
        self.answers_grid.addLayout(self._wrap_layout(self.answers_widgets[1]), 1, 0)
        self.answers_grid.addLayout(self._wrap_layout(self.answers_widgets[3]), 1, 1)
        self.layout.addLayout(self.answers_grid)

        self.nav_layout = QHBoxLayout()
        self.nav_buttons = []

        for i in range(5):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.setStyleSheet("border-radius: 15px; width: 30px; height: 30px;")
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
            self.nav_buttons.append(btn)
            self.nav_layout.addWidget(btn)

        self.layout.addLayout(self.nav_layout)

        btn_layout = QHBoxLayout()
        self.btn_next = QPushButton("Следующий")
        self.btn_submit = QPushButton("Завершить тестирование")
        btn_layout.addWidget(self.btn_next)
        btn_layout.addWidget(self.btn_submit)
        self.layout.addLayout(btn_layout)

        self.btn_next.clicked.connect(self.next_question)
        self.btn_submit.clicked.connect(self.submit_test)

        self.setLayout(self.layout)
        self.setWindowTitle("Тестирование")
        self.resize(700, 700)

    def go_to_question(self, index):
        chosen = self.answer_group.checkedId()
        if chosen >= 0:
            qid = str(self.selected_questions[self.current_question]['id'])
            self.user_answers[qid] = str(chosen + 1)
        self.current_question = index
        self.display_question()
        self.update_nav_buttons()
        
    def update_nav_buttons(self):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == self.current_question)

    def _wrap_layout(self, triple):
        vbox = QVBoxLayout()
        for w in triple:
            vbox.addWidget(w)
        return vbox
    
    def open_image_viewer(self, pixmap):
        if pixmap:
            temp_file = "temp_image.png"
            pixmap.save(temp_file)
            viewer = ImageViewer(temp_file)
            viewer.exec()

    def load_questions(self, lab_id):
        if not self.get_student_id():
            QMessageBox.critical(self, "Ошибка", "Не удалось получить student_id.")
            self.switch_window("lab_selection")
            return
        self.lab_id = lab_id
        request = {'action': 'get_questions', 'data': {'lab_id': lab_id}}
        worker = Worker(request)
        worker.signals.finished.connect(self.handle_load_questions_response)
        worker.signals.error.connect(self.handle_load_questions_error)
        self.thread_pool.start(worker)

    def handle_load_questions_response(self, response):
        if response.get('status') == 'success':
            all_questions = response['data']['questions']
            logging.debug(f"Получены вопросы: {all_questions}")
            
            if not all_questions:
                QMessageBox.warning(self, "Предупреждение", "В базе данных нет вопросов для этой лабораторной работы.")
                self.switch_window("lab_selection")
                return

            questions_1 = [q for q in all_questions if q.get('category') == 'Вопрос 1']
            questions_2 = [q for q in all_questions if q.get('category') == 'Вопрос 2']
            questions_3 = [q for q in all_questions if q.get('category') == 'Вопрос 3']
            questions_4 = [q for q in all_questions if q.get('category') == 'Вопрос 4']
            questions_5 = [q for q in all_questions if q.get('category') == 'Вопрос 5']

            logging.debug(f"Вопрос 1: {len(questions_1)}")
            logging.debug(f"Вопрос 2: {len(questions_2)}")
            logging.debug(f"Вопрос 3: {len(questions_3)}")
            logging.debug(f"Вопрос 4: {len(questions_4)}")
            logging.debug(f"Вопрос 5: {len(questions_5)}")

            missing_categories = []
            if len(questions_1) < 1:
                missing_categories.append(f"Вопрос 1 (нужно 1, есть {len(questions_1)})")
            if len(questions_2) < 1:
                missing_categories.append(f"Вопрос 2 (нужно 1, есть {len(questions_2)})")
            if len(questions_3) < 1:
                missing_categories.append(f"Вопрос 3 (нужно 1, есть {len(questions_3)})")
            if len(questions_4) < 1:
                missing_categories.append(f"Вопрос 4 (нужно 1, есть {len(questions_4)})")
            if len(questions_5) < 1:
                missing_categories.append(f"Вопрос 5 (нужно 1, есть {len(questions_5)})")

            if missing_categories:
                message = "Недостаточно вопросов в следующих категориях:\n- " + "\n- ".join(missing_categories)
                QMessageBox.warning(self, "Предупреждение", message)
                self.switch_window("lab_selection")
                return

            # Reset state before loading new questions
            self.selected_questions = []
            self.current_question = 0
            self.user_answers = {}

            # Select questions in strict order: Вопрос 1 -> 2 -> 3 -> 4 -> 5
            self.selected_questions.extend(random.sample(questions_1, 1))  # Вопрос 1
            self.selected_questions.extend(random.sample(questions_2, 1))  # Вопрос 2
            self.selected_questions.extend(random.sample(questions_3, 1))  # Вопрос 3
            self.selected_questions.extend(random.sample(questions_4, 1))  # Вопрос 4
            self.selected_questions.extend(random.sample(questions_5, 1))  # Вопрос 5

            logging.debug(f"Выбранные вопросы: {self.selected_questions}")

            # Set up timer
            if 'time_limit' not in response['data']:
                QMessageBox.critical(self, "Ошибка", "Не задано время для выполнения теста")
                self.switch_window("lab_selection")
                return
                
            self.remaining_time = response['data']['time_limit'] * 60
            self.timer.start(1000)  # Update every second
            self.update_timer_label()

            # Display first question
            self.current_question = 0
            self.user_answers.clear()
            self.display_question()
            self.update_navigation_buttons()
        else:
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Не удалось загрузить вопросы'))

    def update_navigation_buttons(self):
        for btn in self.nav_buttons:
            btn.deleteLater()
        self.nav_buttons.clear()

        for i in range(len(self.selected_questions)):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.setStyleSheet("border-radius: 15px; width: 30px; height: 30px;")
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
            self.nav_buttons.append(btn)
            self.nav_layout.addWidget(btn)
        self.update_nav_buttons()

    def handle_load_questions_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)
        logging.error(f"Ошибка при загрузке вопросов: {error_message}")

    def display_question(self):
        self.update_nav_buttons()

        if not (0 <= self.current_question < len(self.selected_questions)):
            self.submit_test()
            return

        self.answer_group.setExclusive(False)
        for rb, txt_label, img_label in self.answers_widgets:
            rb.setChecked(False)
            txt_label.setText("")
            img_label.clear()
        self.answer_group.setExclusive(True)
        self.remove_question_images_layout()

        q = self.selected_questions[self.current_question]
        text_only, img_urls = parse_images(q['question_text'])
        self.question_label.setText(f"Вопрос {self.current_question + 1}: {text_only}")

        if img_urls:
            question_images_layout = QHBoxLayout()
            question_images_layout.setObjectName("question_images_layout")
            for img_url in img_urls:
                img_label = QLabel()
                pixmap = QPixmap()
                pixmap.loadFromData(requests.get(img_url).content)
                pixmap = pixmap.scaled(
                    200,
                    200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                question_images_layout.addWidget(img_label)
            self.layout.insertLayout(3, question_images_layout)

        answers = q['answers']
        qid = str(q['id'])
        saved_answer = self.user_answers.get(qid)

        for i, (rb, txt_label, img_label) in enumerate(self.answers_widgets):
            rb.setText(f"Вариант {i + 1}")
            answer = answers[i]
            txt_label.setText(answer['text'])

            if saved_answer == str(i + 1):
                rb.setChecked(True)

            if answer['images']:
                img_url = answer['images'][0]
                pixmap = QPixmap()
                pixmap.loadFromData(requests.get(img_url).content)
                pixmap = pixmap.scaled(
                    120,
                    120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                img_label.setPixmap(pixmap)

    def remove_question_images_layout(self):
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if isinstance(item, QHBoxLayout) and item.objectName() == "question_images_layout":
                while item.count():
                    sub_item = item.takeAt(0)
                    w = sub_item.widget()
                    if w:
                        w.deleteLater()
                self.layout.removeItem(item)
                break

    def open_image_viewer_by_path(self, image_path):
        viewer = ImageViewer(image_path)
        viewer.exec()

    def next_question(self):
        chosen = self.answer_group.checkedId()
        if chosen < 0:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите вариант ответа.")
            return
        qid = str(self.selected_questions[self.current_question]['id'])
        self.user_answers[qid] = str(chosen + 1)
        self.current_question += 1
        if self.current_question < len(self.selected_questions):
            self.display_question()
        else:
            self.submit_test()

    def submit_test(self):
        if self.timer.isActive():
            self.timer.stop()

        # Сохраняем ответ на текущий вопрос, если он выбран
        chosen = self.answer_group.checkedId()
        if 0 <= self.current_question < len(self.selected_questions) and chosen >= 0:
            qid = str(self.selected_questions[self.current_question]['id'])
            self.user_answers[qid] = str(chosen + 1)

        # Проверяем наличие ID студента
        sid = self.get_student_id()
        if not sid:
            QMessageBox.critical(self, "Ошибка", "Не удалось получить данные студента.")
            self.switch_window("lab_selection")
            return

        # Проверяем наличие ID лабораторной работы
        if not self.lab_id:
            QMessageBox.critical(self, "Ошибка", "Не удалось определить лабораторную работу.")
            self.switch_window("lab_selection")
            return

        # Проверяем, что есть хотя бы один ответ
        if not self.user_answers:
            QMessageBox.warning(self, "Предупреждение", "Вы не ответили ни на один вопрос. Тест не может быть завершен.")
            return

        # Проверяем, что даны ответы на все вопросы
        if len(self.user_answers) < len(self.selected_questions):
            missing = len(self.selected_questions) - len(self.user_answers)
            result = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы ответили не на все вопросы (пропущено {missing}). Вы уверены, что хотите завершить тест?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.No:
                if not self.timer.isActive() and self.remaining_time > 0:
                    self.timer.start(1000)
                return

        # Отправляем данные на сервер
        request = {
            'action': 'submit_test',
            'data': {
                'student_id': sid,
                'lab_id': self.lab_id,
                'answers': self.user_answers
            }
        }
        worker = Worker(request)
        worker.signals.finished.connect(self.handle_submit_test_response)
        worker.signals.error.connect(self.handle_submit_test_error)
        self.thread_pool.start(worker)

    def handle_submit_test_response(self, response):
        if response.get('status') == 'success':
            score = response['data']['score']
            total = response['data']['total_questions']
            QMessageBox.information(self, "Результат", f"Тестирование завершено! Ваш результат: {score}/5")
            self.switch_window("result", data={'score': score, 'total': total, 'lab_id': self.lab_id, 'retake': False})
        elif response.get('status') == 'retake':
            score = response['data'].get('score', 0)
            total = response['data'].get('total_questions', 0)
            msg = response.get('message', f"Вы набрали {score}/5, что меньше 2 баллов. Необходимо пересдать.")
            self.switch_window("result", data={'score': score, 'total': total, 'lab_id': self.lab_id, 'retake': True, 'msg': msg})
        else:
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Ошибка при отправке результатов'))

    def handle_submit_test_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)
        logging.error(f"Ошибка при отправке результатов теста: {error_message}")

    def update_timer_label(self):
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_label.setText(f"Оставшееся время: {minutes:02d}:{seconds:02d}")

    def update_timer(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.update_timer_label()
        else:
            self.timer.stop()
            QMessageBox.warning(self, "Время вышло", "Время на выполнение теста закончилось!")
            self.submit_test()

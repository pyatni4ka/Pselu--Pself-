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
import sys
from logger_config import setup_logger

# Добавляем путь к корневой директории проекта в PYTHONPATH
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)

from config_manager import get_server_settings
from image_loader import get_cached_image

# Настраиваем логирование
logger = setup_logger()

def parse_images(text: str, server_url: str = None) -> tuple[str, list[str]]:
    if server_url is None:
        # Загружаем настройки сервера из конфигурационного файла
        settings = get_server_settings()
        server_url = f"http://{settings['host']}:{settings['static_port']}/images"
        logger.info(f"URL сервера изображений: {server_url}")
    
    pattern = r'!\[image\]\((.*?)\)'
    matches = re.findall(pattern, text)
    text_without_images = re.sub(pattern, '', text).replace('\ufffc', '').strip()
    
    # Обрабатываем URL изображений
    urls = []
    for match in matches:
        # Извлекаем только имя файла из полного пути
        filename = os.path.basename(match.replace('\\', '/'))
        url = f"{server_url}/{filename}"
        urls.append(url)
    
    logger.info(f"Найденные URL изображений: {urls}")
    return text_without_images, urls

def load_image_to_pixmap(url):
    """Загружает изображение и создает QPixmap."""
    logger.info(f"Попытка загрузки изображения: {url}")
    cached_path = get_cached_image(url)
    logger.info(f"Путь к кэшированному изображению: {cached_path}")
    if cached_path:
        pixmap = QPixmap(cached_path)
        if not pixmap.isNull():
            logger.info("Изображение успешно загружено")
            return pixmap
        else:
            logger.error("Ошибка: создан пустой QPixmap")
    else:
        logger.error("Ошибка: не удалось получить изображение из кэша")
    return None

class ImageViewer(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Просмотр изображения")
        self.setMinimumSize(600, 600)
        layout = QVBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Загружаем изображение
        try:
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        600, 600, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_label.setPixmap(pixmap)
                else:
                    self.image_label.setText("Ошибка: изображение повреждено")
            else:
                self.image_label.setText("Ошибка: файл не найден")
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {str(e)}")
            self.image_label.setText(f"Ошибка загрузки: {str(e)}")
        
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
        self.thread_pool = QThreadPool()
        self.selected_questions = []
        self.current_question = 0
        self.user_answers = {}
        self.nav_buttons = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()
        self.questions = []
        self.lab_id = None
        self.time_limit = 0
        self.remaining_time = 0
        self.images = {}  # Кэш для изображений
        
        # Настраиваем логирование
        self.logger = logging.getLogger(__name__)

    def init_ui(self):
        self.setWindowTitle("Тестирование")
        
        # Основной layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(20)
        
        # Layout для верхней панели (таймер и кнопка завершения)
        top_panel = QHBoxLayout()
        
        # Таймер
        self.timer_label = QLabel("Осталось времени: ")
        self.timer_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        top_panel.addWidget(self.timer_label)
        
        top_panel.addStretch()
        
        # Кнопка завершения теста
        self.submit_button = QPushButton("Завершить тест")
        self.submit_button.clicked.connect(self.submit_test)
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        top_panel.addWidget(self.submit_button)
        
        self.layout.addLayout(top_panel)
        
        # Заголовок текущего вопроса
        self.question_category_label = QLabel()
        self.question_category_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px;
        """)
        self.question_category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.question_category_label)
        
        # Текст вопроса
        self.question_label = QLabel()
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("""
            font-size: 14px;
            color: #34495e;
            margin: 10px;
        """)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.question_label)

        # Добавляем растяжку перед нижней панелью
        self.layout.addStretch()
        
        # Нижняя панель с навигацией
        bottom_panel = QHBoxLayout()
        
        # Кнопка "Предыдущий вопрос"
        self.prev_button = QPushButton("←")
        self.prev_button.clicked.connect(self.prev_question)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 20px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        bottom_panel.addWidget(self.prev_button)
        
        # Навигация по вопросам
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setSpacing(10)
        bottom_panel.addLayout(self.nav_layout)
        
        # Кнопка "Следующий вопрос"
        self.next_button = QPushButton("→")
        self.next_button.clicked.connect(self.next_question)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 20px;
                min-width: 40px;
                min-height: 40px;
                max-width: 40px;
                max-height: 40px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        bottom_panel.addWidget(self.next_button)
        
        self.layout.addLayout(bottom_panel)
        
        self.resize(800, 800)

    def go_to_question(self, index):
        """Переходит к вопросу с указанным индексом."""
        if 0 <= index < len(self.selected_questions):
            # Сохраняем текущий ответ пользователя
            chosen = self.answer_group.checkedId()
            if chosen >= 0:
                qid = str(self.selected_questions[self.current_question]['id'])
                self.user_answers[qid] = str(chosen)
            
            self.current_question = index
            self.display_question(self.selected_questions[index])
            self.update_navigation_buttons()
            
            # Обновляем состояние кнопки "Следующий вопрос"
            if index == len(self.selected_questions) - 1:
                self.next_button.setEnabled(False)
                self.next_button.setStyleSheet("""
                    QPushButton {
                        background-color: #bdc3c7;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-size: 20px;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                    }
                """)
            else:
                self.next_button.setEnabled(True)
                self.next_button.setStyleSheet("""
                    QPushButton {
                        background-color: #2ecc71;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-size: 20px;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                    }
                    QPushButton:hover {
                        background-color: #27ae60;
                    }
                """)
        
    def display_question(self, question_data):
        """Отображает вопрос и варианты ответов."""
        logger.debug(f"Данные вопроса: {question_data}")
        
        # Очищаем все предыдущие виджеты
        self.clear_question_widgets()
        
        # Обновляем заголовок вопроса
        self.question_category_label.setText(f"{question_data.get('category', '')} ({self.current_question + 1}/{len(self.selected_questions)})")
        
        # Отображаем текст вопроса
        question_text = question_data.get('question_text', '').strip()
        logger.debug(f"Текст вопроса: {question_text}")
        self.question_label.setText(question_text)
        
        # Отображаем изображения вопроса
        question_images = question_data.get('question_images', [])
        logger.debug(f"URL изображений вопроса: {question_images}")
        
        if question_images:
            logger.debug("Найдены изображения для отображения")
            question_images_layout = QHBoxLayout()
            
            for url in question_images:
                logger.debug(f"Обработка изображения: {url}")
                image_label = QLabel()
                image_label.setCursor(Qt.CursorShape.PointingHandCursor)
                pixmap = load_image_to_pixmap(url)
                if pixmap:
                    scaled_pixmap = pixmap.scaled(
                        400, 300,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                    cached_path = get_cached_image(url)
                    image_label.mousePressEvent = lambda _, path=cached_path: self.open_image_viewer(path)
                else:
                    image_label.setText("Ошибка загрузки изображения")
                question_images_layout.addWidget(image_label)
            
            self.layout.insertLayout(2, question_images_layout)
            self.question_images_layout = question_images_layout
        
        # Создаем группу для радиокнопок
        self.answer_group = QButtonGroup()
        
        # Создаем layout для ответов
        answers_layout = QVBoxLayout()
        answers_layout.setObjectName("answers_layout")
        
        # Создаем два горизонтальных ряда для вариантов ответов
        top_row = QHBoxLayout()
        bottom_row = QHBoxLayout()
        
        for i, answer in enumerate(question_data['answers'], 1):
            answer_container = QVBoxLayout()
            
            # Создаем горизонтальный контейнер для радиокнопки и заголовка
            header_container = QHBoxLayout()
            
            # Добавляем радиокнопку
            radio = QRadioButton()
            self.answer_group.addButton(radio, i-1)
            header_container.addWidget(radio)
            
            # Добавляем заголовок варианта ответа
            answer_header = QLabel(f"Вариант {i}")
            answer_header.setStyleSheet("font-weight: bold; color: #444;")
            header_container.addWidget(answer_header)
            header_container.addStretch()
            
            answer_container.addLayout(header_container)
            
            # Если есть текст ответа, добавляем его
            if answer['text']:
                text_label = QLabel(answer['text'])
                text_label.setWordWrap(True)
                answer_container.addWidget(text_label)
            
            # Добавляем изображения ответа
            for url in answer['images']:
                image_label = QLabel()
                image_label.setCursor(Qt.CursorShape.PointingHandCursor)
                pixmap = load_image_to_pixmap(url)
                if pixmap:
                    scaled_pixmap = pixmap.scaled(
                        300, 200,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                    cached_path = get_cached_image(url)
                    image_label.mousePressEvent = lambda _, path=cached_path: self.open_image_viewer(path)
                else:
                    image_label.setText("Ошибка загрузки изображения")
                answer_container.addWidget(image_label)
            
            # Добавляем варианты в соответствующие ряды
            if i <= 2:
                top_row.addLayout(answer_container)
            else:
                bottom_row.addLayout(answer_container)
            
            # Добавляем разделитель между вариантами в ряду
            if i == 1 or i == 3:
                spacer = QLabel()
                spacer.setFixedWidth(20)
                if i == 1:
                    top_row.addWidget(spacer)
                else:
                    bottom_row.addWidget(spacer)
        
        answers_layout.addLayout(top_row)
        answers_layout.addSpacing(20)  # Отступ между рядами
        answers_layout.addLayout(bottom_row)
        
        self.layout.insertLayout(3, answers_layout)
        self.answers_layout = answers_layout
        
        # Восстанавливаем ответ пользователя, если он был
        qid = str(question_data['id'])
        if qid in self.user_answers:
            answer_index = int(self.user_answers[qid])  # Преобразуем в int
            if 0 <= answer_index < len(question_data['answers']):
                self.answer_group.button(answer_index).setChecked(True)

    def clear_question_widgets(self):
        """Очищает все виджеты текущего вопроса."""
        # Очищаем изображения вопроса
        if hasattr(self, 'question_images_layout'):
            while self.question_images_layout.count():
                item = self.question_images_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.layout.removeItem(self.question_images_layout)
        
        # Очищаем варианты ответов
        if hasattr(self, 'answers_layout'):
            while self.answers_layout.count():
                item = self.answers_layout.takeAt(0)
                if item.layout():
                    while item.layout().count():
                        sub_item = item.layout().takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
                        elif sub_item.layout():
                            while sub_item.layout().count():
                                sub_sub_item = sub_item.layout().takeAt(0)
                                if sub_sub_item.widget():
                                    sub_sub_item.widget().deleteLater()
            self.layout.removeItem(self.answers_layout)
        
        # Очищаем группу радиокнопок
        if hasattr(self, 'answer_group'):
            for button in self.answer_group.buttons():
                self.answer_group.removeButton(button)
                button.deleteLater()

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

    def open_image_viewer(self, image_path):
        """Открывает окно просмотра изображения."""
        if os.path.exists(image_path):
            viewer = ImageViewer(image_path)
            viewer.exec()
        else:
            logger.error(f"Файл изображения не найден: {image_path}")
            QMessageBox.warning(self, "Ошибка", "Файл изображения не найден")

    def next_question(self):
        """Переходит к следующему вопросу или завершает тест."""
        # Сохраняем ответ на текущий вопрос, если он был
        chosen = self.answer_group.checkedId()
        if chosen >= 0:
            qid = str(self.selected_questions[self.current_question]['id'])
            self.user_answers[qid] = str(chosen)
        
        # Переходим к следующему вопросу
        self.current_question += 1
        if self.current_question < len(self.selected_questions):
            self.display_question(self.selected_questions[self.current_question])
            self.update_navigation_buttons()
            
            # Обновляем состояние кнопки "Следующий вопрос"
            if self.current_question == len(self.selected_questions) - 1:
                self.next_button.setEnabled(False)
                self.next_button.setStyleSheet("""
                    QPushButton {
                        background-color: #bdc3c7;
                        color: white;
                        border: none;
                        border-radius: 20px;
                        font-size: 20px;
                        min-width: 40px;
                        min-height: 40px;
                        max-width: 40px;
                        max-height: 40px;
                    }
                """)
        else:
            self.submit_test()

    def submit_test(self):
        if self.timer.isActive():
            self.timer.stop()

        # Сохраняем ответ на текущий вопрос, если он был
        chosen = self.answer_group.checkedId()
        if 0 <= self.current_question < len(self.selected_questions) and chosen >= 0:
            qid = str(self.selected_questions[self.current_question]['id'])
            self.user_answers[qid] = str(chosen)

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
        logger.error(f"Ошибка при отправке результатов теста: {error_message}")

    def update_timer_label(self):
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_label.setText(f"Осталось времени: {minutes:02d}:{seconds:02d}")

    def update_timer(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.update_timer_label()
        else:
            self.timer.stop()
            QMessageBox.warning(self, "Время вышло", "Время на выполнение теста закончилось!")
            self.submit_test()

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
            logger.debug(f"Получены вопросы: {all_questions}")
            
            if not all_questions:
                QMessageBox.warning(self, "Предупреждение", "В базе данных нет вопросов для этой лабораторной работы.")
                self.switch_window("lab_selection")
                return

            # Проверяем корректность формата данных
            for q in all_questions:
                if not isinstance(q, dict) or 'id' not in q or 'category' not in q:
                    logger.error(f"Некорректный формат вопроса: {q}")
                    QMessageBox.critical(self, "Ошибка", "Некорректный формат данных вопроса")
                    self.switch_window("lab_selection")
                    return

            questions_1 = [q for q in all_questions if q.get('category') == 'Вопрос 1']
            questions_2 = [q for q in all_questions if q.get('category') == 'Вопрос 2']
            questions_3 = [q for q in all_questions if q.get('category') == 'Вопрос 3']
            questions_4 = [q for q in all_questions if q.get('category') == 'Вопрос 4']
            questions_5 = [q for q in all_questions if q.get('category') == 'Вопрос 5']

            logger.debug(f"Вопрос 1: {len(questions_1)}")
            logger.debug(f"Вопрос 2: {len(questions_2)}")
            logger.debug(f"Вопрос 3: {len(questions_3)}")
            logger.debug(f"Вопрос 4: {len(questions_4)}")
            logger.debug(f"Вопрос 5: {len(questions_5)}")

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

            try:
                # Select questions in strict order: Вопрос 1 -> 2 -> 3 -> 4 -> 5
                self.selected_questions.extend(random.sample(questions_1, 1))  # Вопрос 1
                self.selected_questions.extend(random.sample(questions_2, 1))  # Вопрос 2
                self.selected_questions.extend(random.sample(questions_3, 1))  # Вопрос 3
                self.selected_questions.extend(random.sample(questions_4, 1))  # Вопрос 4
                self.selected_questions.extend(random.sample(questions_5, 1))  # Вопрос 5

                logger.debug(f"Выбранные вопросы: {self.selected_questions}")

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
                self.display_question(self.selected_questions[self.current_question])
                self.update_navigation_buttons()
            except Exception as e:
                logger.error(f"Ошибка при обработке вопросов: {str(e)}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке вопросов: {str(e)}")
                self.switch_window("lab_selection")
        else:
            error_msg = response.get('message', 'Не удалось загрузить вопросы')
            logger.error(f"Ошибка при загрузке вопросов: {error_msg}")
            QMessageBox.warning(self, "Ошибка", error_msg)
            self.switch_window("lab_selection")

    def update_navigation_buttons(self):
        """Обновляет кнопки навигации по вопросам."""
        for btn in self.nav_buttons:
            btn.deleteLater()
        self.nav_buttons.clear()

        for i in range(len(self.selected_questions)):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.setChecked(i == self.current_question)
            
            # Определяем стиль кнопки в зависимости от состояния
            if i == self.current_question:
                base_color = "#3498db"  # Текущий вопрос - синий
            elif str(self.selected_questions[i]['id']) in self.user_answers:
                base_color = "#27ae60"  # Отвеченный вопрос - зеленый
            else:
                base_color = "#bdc3c7"  # Неотвеченный вопрос - серый
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {base_color};
                    color: white;
                    border: none;
                    border-radius: 15px;
                    width: 30px;
                    height: 30px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {base_color if base_color == "#3498db" else "#2c3e50"};
                }}
            """)
            
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
            self.nav_buttons.append(btn)
            self.nav_layout.addWidget(btn)
            
        # Обновляем состояние кнопок prev/next
        self.prev_button.setEnabled(self.current_question > 0)
        self.next_button.setEnabled(self.current_question < len(self.selected_questions) - 1)

    def handle_load_questions_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)
        logger.error(f"Ошибка при загрузке вопросов: {error_message}")

    def prev_question(self):
        """Переходит к предыдущему вопросу."""
        if self.current_question > 0:
            self.go_to_question(self.current_question - 1)

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHBoxLayout,
    QHeaderView,
    QScrollArea,
    QFrame
)
from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtGui import QPixmap
import sys
import os
from network_workers import Worker
from config_manager import ConfigManager
from logger_config import get_logger
import json
import logging

class LabSelectionWindow(QWidget):
    def __init__(self, switch_window, get_student_id):
        super().__init__()
        self.switch_window = switch_window
        self.get_student_id = get_student_id
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

    def init_ui(self):
        layout = QVBoxLayout()

        header = QLabel("Выбор лабораторной работы")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Тема ЛР", "Время (мин)", "Статус"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.table.setColumnHidden(0, True)

        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)

        self.table.setColumnWidth(2, 150)  
        self.table.setColumnWidth(3, 150)
        

        btn_layout = QHBoxLayout()
        btn_start = QPushButton("Начать тестирование")
        btn_back = QPushButton("Назад")
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_back)
        layout.addLayout(btn_layout)

        btn_start.clicked.connect(self.start_testing)
        btn_back.clicked.connect(lambda: self.switch_window("login"))

        layout.setSpacing(15)
        layout.setContentsMargins(100, 50, 100, 50)
        self.setLayout(layout)
        self.setWindowTitle("Выбор лабораторной работы")
        self.resize(700, 600)

    def load_data(self):
        self.start_get_lab_works()

    def start_get_lab_works(self):
        request = {
            'action': 'get_lab_works',
            'data': {}
        }

        worker = Worker(request)
        worker.signals.finished.connect(self.handle_get_lab_works_response)
        worker.signals.error.connect(self.handle_get_lab_works_error)
        self.thread_pool.start(worker)

    def handle_get_lab_works_response(self, response):
        logging.debug(f"Ответ на get_lab_works: {response}")
        if response.get('status') == 'success':
            lab_works = response['data']['lab_works']
            student_id = self.get_student_id()
            logging.debug(f"Получен student_id: {student_id}")
            if not student_id:
                QMessageBox.critical(self, "Ошибка", "Не удалось получить student_id.")
                return
            self.table.setRowCount(0)
            for row_number, lab in enumerate(lab_works):
                self.table.insertRow(row_number)
                self.table.setItem(row_number, 0, QTableWidgetItem(str(lab['id'])))
                self.table.setItem(row_number, 1, QTableWidgetItem(lab['theme']))
                self.table.setItem(row_number, 2, QTableWidgetItem(str(lab['time'])))
                status_item = QTableWidgetItem("Проверяется...")
                self.table.setItem(row_number, 3, status_item)
                logging.debug(f"Отправка запроса check_lab_completed для student_id={student_id}, lab_id={lab['id']}")
                self.check_lab_status(student_id, lab['id'], status_item)
        else:
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Не удалось загрузить лабораторные работы'))


    def handle_get_lab_works_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить лабораторные работы: {error_message}")
        logging.error(f"Ошибка при загрузке лабораторных работ: {error_message}")

    def check_lab_status(self, student_id, lab_id, status_item):
        if not student_id or not lab_id:
            self.update_status(status_item, "Ошибка")
            logging.error("student_id или lab_id не установлены.")
            return

        request = {
            'action': 'check_lab_completed',
            'data': {
                'student_id': student_id,
                'lab_id': lab_id
            }
        }

        worker = Worker(request)
        worker.signals.finished.connect(lambda response: self.handle_check_status_response(response, status_item))
        worker.signals.error.connect(lambda error: self.handle_check_status_error(error, status_item))
        self.thread_pool.start(worker)

    def handle_check_status_response(self, response, status_item):
        if response.get('status') == 'success':
            completed = response['data'].get('completed', False)
            status_text = "Выполнено" if completed else "Не выполнено"
            self.update_status(status_item, status_text)
        else:
            self.update_status(status_item, "Ошибка")

    def handle_check_status_error(self, error_message, status_item):
        self.update_status(status_item, "Ошибка")
        logging.error(f"Ошибка проверки статуса ЛР: {error_message}")

    def update_status(self, status_item, text):
        status_item.setText(text)

    def start_testing(self):
        selected = self.table.currentRow()
        if selected >= 0:
            lab_id_item = self.table.item(selected, 0)
            status_item = self.table.item(selected, 3)
            if lab_id_item and status_item:
                status = status_item.text()
                if status == "Выполнено":
                    QMessageBox.information(self, "Информация", "Вы уже выполнили эту лабораторную работу.")
                    return
                elif status == "Ошибка":
                    QMessageBox.warning(self, "Ошибка", "Не удалось проверить статус лабораторной работы.")
                    return
                elif status == "Проверяется...":
                    QMessageBox.information(self, "Информация", "Проверка статуса лабораторной работы еще не завершена.")
                    return
                lab_id = lab_id_item.text()
                self.switch_window("testing", data=lab_id)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось получить данные лабораторной работы.")
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите лабораторную работу.")

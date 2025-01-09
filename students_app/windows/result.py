from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QThreadPool
import logging
from .network_workers import Worker

class ResultWindow(QWidget):
    def __init__(self, switch_window, get_student_id):
        super().__init__()
        self.switch_window = switch_window
        self.get_student_id = get_student_id
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

    def init_ui(self):
        layout = QVBoxLayout()
        header = QLabel("Результат тестирования")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        self.info_label = QLabel("ФИО: \nГруппа: \nРезультат: ")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        btn_back = QPushButton("Вернуться в главное меню")
        layout.addWidget(btn_back)
        btn_back.clicked.connect(lambda: self.switch_window("lab_selection"))
        layout.setSpacing(20)
        layout.setContentsMargins(100, 100, 100, 100)
        self.setLayout(layout)
        self.setWindowTitle("Результат тестирования")
        self.resize(400, 400)

    def display_result(self, data):
        score = data.get('score', 0)
        total = data.get('total', 0)
        retake = data.get('retake', False)
        msg = data.get('msg', '')
        sid = self.get_student_id()
        
        if not sid:
            self.info_label.setText(f"ФИО: Неизвестно\nГруппа: Неизвестно\nРезультат: {score}/5")
            QMessageBox.warning(self, "Ошибка", "Не удалось получить данные студента.")
            return
        
        req = {
            'action': 'get_student_info',
            'data': {'student_id': sid}
        }

        def process_response(response):
            if response.get('status') == 'success':
                student = response['data']['student']
                fn = student.get('first_name', '')
                ln = student.get('last_name', '')
                mn = student.get('middle_name', '')
                grp = student.get('group_name', '')
                full_name = f"{fn} {ln} {mn}".strip()
                if retake:
                    self.info_label.setText(f"ФИО: {full_name}\nГруппа: {grp}\nРезультат: {score}/5\nЛабораторная не засчитана. Необходимо пересдать.")
                    QMessageBox.warning(
                        self,
                        "Пересдача",
                        msg or f"Вы набрали {score}/5, что меньше 2 баллов. Пересдача."
                    )
                else:
                    self.info_label.setText(f"ФИО: {full_name}\nГруппа: {grp}\nРезультат: {score}/5")
            else:
                self.info_label.setText(f"ФИО: Неизвестно\nГруппа: Неизвестно\nРезультат: {score}/5")
                QMessageBox.warning(self, "Ошибка", response.get('message', 'Не удалось получить информацию о студенте.'))

        worker = Worker(req)
        worker.signals.finished.connect(process_response)
        worker.signals.error.connect(self.handle_get_student_info_error)
        self.thread_pool.start(worker)

    def handle_get_student_info_response(self, response, score, total):
        if response.get('status') == 'success':
            student = response['data']['student']
            fn = student.get('first_name', '')
            ln = student.get('last_name', '')
            mn = student.get('middle_name', '')
            grp = student.get('group_name', '')
            full_name = f"{fn} {ln} {mn}".strip()
            self.info_label.setText(f"ФИО: {full_name}\nГруппа: {grp}\nРезультат: {score}/5")
        else:
            self.info_label.setText(f"ФИО: Неизвестно\nГруппа: Неизвестно\nРезультат: {score}/5")
            QMessageBox.warning(self, "Ошибка", response.get('message', 'Не удалось получить информацию о студенте.'))

    def handle_get_student_info_error(self, error_message):
        self.info_label.setText("ФИО: Неизвестно\nГруппа: Неизвестно\nРезультат: Ошибка получения данных")
        QMessageBox.warning(self, "Ошибка", error_message)
        logging.error(f"Ошибка при получении информации о студенте: {error_message}")

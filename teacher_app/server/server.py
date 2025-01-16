import socketserver
import threading
import json
import logging
import sqlite3
import struct
import os
import http.server
from PyQt6.QtCore import QThread, pyqtSignal

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mgtu_app.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

logging.basicConfig(
    filename='server_control.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class StaticFileServer:
    def __init__(self, directory=STATIC_DIR, host="0.0.0.0", port=8080):
        self.directory = directory
        self.host = host
        self.port = port
        self.httpd = None
        self.thread = None

        os.makedirs(self.directory, exist_ok=True)

    def start(self):
        handler = http.server.SimpleHTTPRequestHandler
        os.chdir(self.directory)
        self.httpd = socketserver.TCPServer((self.host, self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"Static file server running at http://{self.host}:{self.port}")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("Static file server stopped")

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.increment_clients()
        try:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                try:
                    request = json.loads(data.decode('utf-8'))
                    response = self.process_request(request)
                except json.JSONDecodeError:
                    response = {'status': 'error', 'message': 'Неверный формат JSON'}
                    self.send_response(response)
                    continue
                self.send_response(response)
        except ConnectionResetError:
            pass
        finally:
            self.server.decrement_clients(self.client_address)

    def send_response(self, response):
        response_data = json.dumps(response).encode('utf-8')
        length_prefix = struct.pack('!I', len(response_data))
        self.request.sendall(length_prefix + response_data)


    def process_request(self, request):
        action = request.get('action')
        data = request.get('data', {})
        if action == 'login':
            return self.handle_login(data)
        elif action == 'register':
            return self.handle_register(data)
        elif action == 'get_lab_works':
            return self.handle_get_lab_works()
        elif action == 'get_questions':
            return self.handle_get_questions(data)
        elif action == 'submit_test':
            return self.handle_submit_test(data)
        elif action == 'get_student_info':
            return self.handle_get_student_info(data)
        elif action == 'import_lab_works':
            return self.handle_import_lab_works(data)
        elif action == 'export_results':
            return self.handle_export_results(data)
        elif action == 'check_lab_completed':
            return self.handle_check_lab_completed(data)
        return {'status': 'error', 'message': 'Неизвестное действие'}

    def handle_login(self, data):
        f = data.get('first_name')
        l = data.get('last_name')
        m = data.get('middle_name', '')
        g = data.get('group_name')
        y = data.get('year')
        if not f or not l or not g or not y:
            return {'status': 'error', 'message': 'Необходимо заполнить имя, фамилию, группу и год'}
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM students WHERE first_name=? AND last_name=? AND middle_name=? AND group_name=? AND year=?",
            (f, l, m, g, y)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            student_id = row[0]
            fio = f"{l} {f}"
            if m:
                fio += f" {m}"
            self.server.client_usernames[self.client_address] = fio
            msg = f"{fio} подключился"
            logger.info(msg)
            self.server.log_message.emit(msg)
            return {'status': 'success', 'data': {'student_id': student_id}}
        return {'status': 'error', 'message': 'Учетная запись не найдена'}

    def handle_register(self, data):
        f = data.get('first_name')
        l = data.get('last_name')
        m = data.get('middle_name', '')
        g = data.get('group_name')
        y = data.get('year')
        if not f or not l or not g or not y:
            return {'status': 'error', 'message': 'Необходимо заполнить имя, фамилию, группу и год'}
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        
        cur.execute(
            "SELECT id FROM students WHERE first_name=? AND last_name=? AND middle_name=? AND group_name=? AND year=?",
            (f, l, m, g, y)
        )
        existing_user = cur.fetchone()
        if existing_user:
            conn.close()
            return {'status': 'error', 'message': 'Пользователь с такими данными уже зарегистрирован'}
        
        try:
            cur.execute(
                "INSERT INTO students (first_name, last_name, middle_name, group_name, year) VALUES (?, ?, ?, ?, ?)",
                (f, l, m, g, y)
            )
            conn.commit()
            student_id = cur.lastrowid
            conn.close()
            fio = f"{l} {f}"
            if m:
                fio += f" {m}"
            self.server.client_usernames[self.client_address] = fio
            msg = f"{fio} подключился (новая регистрация)"
            logger.info(msg)
            self.server.log_message.emit(msg)
            return {'status': 'success', 'data': {'student_id': student_id}}
        except sqlite3.Error as e:
            conn.close()
            return {'status': 'error', 'message': f"Ошибка базы данных: {e}"}

    def handle_get_lab_works(self):
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, theme, time FROM lab_works")
            data = cursor.fetchall()
            conn.close()
            return {'status': 'success', 'data': {'lab_works': [{'id': x[0], 'theme': x[1], 'time': x[2]} for x in data]}}
        except sqlite3.Error as e:
            logger.error(f"Database error in handle_get_lab_works: {e}")
            return {'status': 'error', 'message': str(e)}

    def handle_get_questions(self, data):
        lid = data.get('lab_id')
        if not lid:
            return {'status': 'error', 'message': 'Не указан lab_id'}

        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            logger.debug(f"Загрузка вопросов для lab_id={lid}")
            
            cursor.execute("""
                SELECT
                    id,
                    category,
                    question_text,
                    answer1,
                    answer2,
                    answer3,
                    answer4,
                    correct_index
                FROM questions
                WHERE lab_id=?
            """, (lid,))
            questions = cursor.fetchall()
            
            logger.debug(f"Найдено вопросов: {len(questions)}")
            if not questions:
                logger.warning(f"Вопросы для lab_id={lid} не найдены")
                conn.close()
                return {'status': 'error', 'message': 'Для данной лабораторной работы не созданы вопросы'}

            cursor.execute("SELECT time FROM lab_works WHERE id=?", (lid,))
            lab_time = cursor.fetchone()
            logger.debug(f"Время на тест: {lab_time}")
            
            conn.close()

            time_limit = lab_time[0] if lab_time else None
            if time_limit is None:
                logger.error(f"Не найдено время для lab_id={lid}")
                return {'status': 'error', 'message': 'Не задано время для выполнения теста'}

            results = []
            for q in questions:
                q_id, category, q_text, a1, a2, a3, a4, correct_idx = q
                logger.debug(f"Обработка вопроса {q_id}, категория: {category}")

                q_text_parsed, q_image_urls = self.parse_images(q_text)
                a1_parsed, a1_image_urls = self.parse_images(a1)
                a2_parsed, a2_image_urls = self.parse_images(a2)
                a3_parsed, a3_image_urls = self.parse_images(a3)
                a4_parsed, a4_image_urls = self.parse_images(a4)

                results.append({
                    'id': q_id,
                    'category': category,
                    'question_text': q_text_parsed,
                    'question_images': q_image_urls,
                    'answers': [
                        {'text': a1_parsed, 'images': a1_image_urls},
                        {'text': a2_parsed, 'images': a2_image_urls},
                        {'text': a3_parsed, 'images': a3_image_urls},
                        {'text': a4_parsed, 'images': a4_image_urls}
                    ],
                    'correct_index': correct_idx
                })

            response_data = {
                'status': 'success',
                'data': {
                    'questions': results,
                    'time_limit': time_limit
                }
            }
            logger.debug(f"Отправка ответа: {response_data}")
            return response_data

        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            return {'status': 'error', 'message': 'Ошибка базы данных'}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {'status': 'error', 'message': 'Внутренняя ошибка сервера'}

    def parse_images(self, text: str, base_url: str = "http://localhost:8080/images") -> tuple[str, list[str]]:
        import re
        pattern = r'!\[image\]\((.*?)\)'
        matches = re.findall(pattern, text)
        cleaned_text = re.sub(pattern, '', text).strip()
        image_urls = [f"{base_url}/{match}" for match in matches]
        return cleaned_text, image_urls

    def handle_submit_test(self, data):
        sid = data.get('student_id')
        lid = data.get('lab_id')
        answers = data.get('answers', {})
        if not sid or not lid or not answers:
            return {'status': 'error', 'message': 'Необходимо предоставить student_id, lab_id и ответы'}
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT theme FROM lab_works WHERE id=?", (lid,))
        lab_row = cursor.fetchone()
        lab_theme = lab_row[0] if lab_row else "Неизвестно"

        cursor.execute("SELECT first_name, last_name, middle_name FROM students WHERE id=?", (sid,))
        student_row = cursor.fetchone()
        student_fio = f"{student_row[1]} {student_row[0]}"
        if student_row[2]:
            student_fio += f" {student_row[2]}"
        
        cursor.execute("SELECT id FROM results WHERE student_id=? AND lab_id=?", (sid, lid))
        if cursor.fetchone():
            conn.close()
            return {'status': 'error', 'message': 'Лабораторная работа уже выполнена'}
        
        cursor.execute("SELECT id, correct_index FROM questions WHERE lab_id=?", (lid,))
        rows = cursor.fetchall()
        correct_map = {str(r[0]): str(r[1]) for r in rows}
        total_questions = len(correct_map)
        score = sum(1 for q_id, user_answer in answers.items() if correct_map.get(q_id) == user_answer)

        if score < 3:
            msg = f"{student_fio} не прошел лабораторную работу '{lab_theme}'. Баллы: {score}/5"
            logger.info(msg)
            self.server.log_message.emit(msg)
            conn.close()
            return {
                'status': 'retake',
                'message': f'Вы набрали {score}/5, лабораторная не засчитана.',
                'data': {
                    'score': score,
                    'total_questions': total_questions
                }
            }
        
        cursor.execute("INSERT INTO results (student_id, lab_id, score) VALUES (?, ?, ?)", (sid, lid, score))
        conn.commit()
        conn.close()
        msg = f"{student_fio} прошел лабораторную работу '{lab_theme}' на {score} баллов из 5."
        logger.info(msg)
        self.server.log_message.emit(msg)
        return {
            'status': 'success',
            'data': {
                'score': score,
                'total_questions': total_questions
            }
        }

    def handle_check_lab_completed(self, data):
        sid = data.get('student_id')
        lid = data.get('lab_id')
        if not sid or not lid:
            return {'status': 'error', 'message': 'Необходимо предоставить student_id и lab_id'}
        c = sqlite3.connect(DATABASE_PATH)
        r = c.cursor()
        r.execute("SELECT id FROM results WHERE student_id=? AND lab_id=?", (sid, lid))
        rr = r.fetchone()
        c.close()
        if rr:
            return {'status': 'success', 'data': {'completed': True}}
        return {'status': 'success', 'data': {'completed': False}}

    def handle_get_student_info(self, data):
        sid = data.get('student_id')
        if not sid:
            return {'status': 'error', 'message': 'Не указан student_id'}
        c = sqlite3.connect(DATABASE_PATH)
        r = c.cursor()
        r.execute("SELECT first_name, last_name, middle_name, group_name FROM students WHERE id=?", (sid,))
        w = r.fetchone()
        c.close()
        if w:
            return {'status': 'success', 'data': {'student': {'first_name': w[0], 'last_name': w[1], 'middle_name': w[2], 'group_name': w[3]}}}
        return {'status': 'error', 'message': 'Студент не найден'}

    def handle_import_lab_works(self, data):
        lw = data.get('lab_works')
        if not lw:
            return {'status': 'error', 'message': 'Нет данных для импорта'}
        c = sqlite3.connect(DATABASE_PATH)
        r = c.cursor()
        try:
            for lab in lw:
                th = lab.get('theme')
                ti = lab.get('time')
                qc = lab.get('question_count', 0)
                r.execute("INSERT INTO lab_works (theme, time, question_count) VALUES (?, ?, ?)", (th, ti, qc))
            c.commit()
            c.close()
            return {'status': 'success'}
        except sqlite3.Error as e:
            c.close()
            return {'status': 'error', 'message': f"Ошибка базы данных: {e}"}

    def handle_export_results(self, data):
        c = sqlite3.connect(DATABASE_PATH)
        r = c.cursor()
        r.execute("SELECT s.first_name, s.last_name, s.middle_name, s.group_name, r.lab_id, r.score FROM results r JOIN students s ON r.student_id = s.id")
        rec = r.fetchall()
        c.close()
        out = []
        for row in rec:
            out.append({
                'first_name': row[0],
                'last_name': row[1],
                'middle_name': row[2],
                'group_name': row[3],
                'lab_id': row[4],
                'score': row[5]
            })
        return {'status': 'success', 'data': {'results': out}}

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.connected_clients = 0
        self.lock = threading.Lock()
        self.log_message = None
        self.client_usernames = {}
    def increment_clients(self):
        with self.lock:
            self.connected_clients += 1
            msg = f"Клиентов подключено: {self.connected_clients}"
            logger.info(msg)
            if self.log_message:
                self.log_message.emit(msg)
    def decrement_clients(self, client_address):
        with self.lock:
            self.connected_clients -= 1
            if self.connected_clients < 0:
                self.connected_clients = 0
            fio = self.client_usernames.pop(client_address, None)
            if fio:
                msg = f"{fio} отключился"
            else:
                msg = f"Клиент отключился: {client_address}"
            logger.info(f"Клиентов подключено: {self.connected_clients}")
            logger.info(msg)
            if self.log_message:
                self.log_message.emit(f"Клиентов подключено: {self.connected_clients}")
                self.log_message.emit(msg)

class ServerThread(QThread):
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    log_message = pyqtSignal(str)
    def __init__(self, host="0.0.0.0", port=9999, static_dir=STATIC_DIR, static_port=8080):
        super().__init__()
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.static_file_server = StaticFileServer(directory=static_dir, port=static_port)
    def run(self):
        try:
            self.static_file_server.start()
            self.log_message.emit("Static file server запущен")
            logger.info("Static file server запущен")
            self.server = ThreadedTCPServer((self.host, self.port), ThreadedTCPRequestHandler)
            self.server.log_message = self.log_message
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.log_message.emit("TCP-сервер запущен")
            logger.info("TCP-сервер запущен")
            self.server_started.emit()
            self.server_thread.join()
        except Exception as e:
            em = f"Ошибка при запуске серверов: {e}"
            self.log_message.emit(em)
            logger.error(em)
            self.server_stopped.emit()
    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.log_message.emit("TCP-сервер остановлен")
            logger.info("TCP-сервер остановлен")
        self.static_file_server.stop()
        self.log_message.emit("Static file server остановлен")
        logger.info("Static file server остановлен")

        self.server_stopped.emit()

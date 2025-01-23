import socketserver
import threading
import json
import logging
import sqlite3
import struct
import os
import http.server
import configparser
from PyQt5.QtCore import QThread, pyqtSignal
import uuid
import hashlib
import socket
import time
from datetime import datetime

# Настройка логгера
logging.basicConfig(
    filename='server_control.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mgtu_app.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Создаем директорию для статических файлов
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
    os.makedirs(os.path.join(STATIC_DIR, "images"))
    logger.info(f"Созданы директории для статических файлов: {STATIC_DIR}")
elif not os.path.exists(os.path.join(STATIC_DIR, "images")):
    os.makedirs(os.path.join(STATIC_DIR, "images"))
    logger.info(f"Создана директория для изображений: {os.path.join(STATIC_DIR, 'images')}")

# Загружаем конфигурацию
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.ini")
if not os.path.exists(config_path):
    config_path = "config.ini"  # Fallback для собранного приложения
config.read(config_path)

# Получаем настройки сервера
SERVER_HOST = config.get('Server', 'host', fallback='0.0.0.0')
SERVER_PORT = config.getint('Server', 'port', fallback=9999)
STATIC_PORT = config.getint('Server', 'static_port', fallback=8080)

class StaticFileServer:
    def __init__(self, directory=STATIC_DIR, host="0.0.0.0", port=8080):
        self.directory = directory
        self.host = host
        self.port = port
        self.httpd = None
        self.thread = None

        # Создаем директорию для статических файлов и изображений
        os.makedirs(self.directory, exist_ok=True)
        images_dir = os.path.join(self.directory, "images")
        os.makedirs(images_dir, exist_ok=True)

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
                # Читаем длину сообщения (4 байта)
                length_prefix = self.request.recv(4)
                if not length_prefix:
                    break
                
                # Распаковываем длину сообщения
                message_length = struct.unpack('!I', length_prefix)[0]
                
                # Читаем данные
                chunks = []
                bytes_recd = 0
                while bytes_recd < message_length:
                    chunk = self.request.recv(min(message_length - bytes_recd, 2048))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    bytes_recd += len(chunk)
                
                if not chunks:
                    break
                
                data = b''.join(chunks)
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
        elif action == 'upload_image':
            return self.handle_upload_image(data)
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

    def parse_images(self, text: str, base_url: str = None) -> tuple[str, list[str]]:
        """
        Извлекает изображения из текста в формате markdown и возвращает очищенный текст и список URL изображений.
        
        Args:
            text (str): Текст с markdown разметкой изображений
            base_url (str): Базовый URL для изображений
            
        Returns:
            tuple[str, list[str]]: Кортеж (очищенный текст, список URL изображений)
        """
        if base_url is None:
            # Используем IP-адрес сервера вместо localhost
            base_url = f"http://{SERVER_HOST}:{STATIC_PORT}/images"
            
        import re
        pattern = r'!\[image\]\((.*?)\)'
        matches = re.findall(pattern, text)
        cleaned_text = re.sub(pattern, '', text).strip()
        
        # Преобразуем имена файлов в полные URL
        image_urls = [f"{base_url}/{match}" for match in matches]
        
        return cleaned_text, image_urls

    def handle_submit_test(self, data):
        sid = data.get('student_id')
        lid = data.get('lab_id')
        answers = data.get('answers', {})
        duration = data.get('duration', 0)  # Получаем длительность выполнения
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
        
        cursor.execute("INSERT INTO results (student_id, lab_id, score, duration) VALUES (?, ?, ?, ?)", (sid, lid, score, duration))
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

    def handle_upload_image(self, image_data):
        try:
            # Создаем хэш содержимого изображения для проверки дубликатов
            image_hash = hashlib.md5(image_data).hexdigest()
            
            # Проверяем, существует ли уже такое изображение
            conn = sqlite3.connect(DATABASE_PATH)
            cur = conn.cursor()
            cur.execute("SELECT filename FROM images WHERE hash=?", (image_hash,))
            existing_file = cur.fetchone()
            
            if existing_file:
                # Если изображение уже существует, возвращаем существующий URL
                filename = existing_file[0]
                conn.close()
                return {'status': 'success', 'data': {'image_url': f"http://localhost:8080/images/{filename}"}}
            
            # Генерируем уникальное имя файла
            filename = f"{uuid.uuid4().hex}.png"
            image_path = os.path.join(STATIC_DIR, "images", filename)
            
            # Сохраняем изображение
            with open(image_path, "wb") as f:
                f.write(image_data)
            
            # Сохраняем информацию об изображении в базе данных
            cur.execute("INSERT INTO images (filename, hash) VALUES (?, ?)", (filename, image_hash))
            conn.commit()
            conn.close()
            
            return {'status': 'success', 'data': {'image_url': f"http://localhost:8080/images/{filename}"}}
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения: {e}")
            return {'status': 'error', 'message': str(e)}

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
    connection_status = pyqtSignal(str)  # Новый сигнал для статуса подключения
    
    def __init__(self):
        super().__init__()
        self.server = None
        self.static_server = None
        self.running = False
        self.active_sessions = {}
        self.test_results = []
        self._lock = threading.Lock()
        self.connected_clients = 0  # Счетчик подключенных клиентов
    
    def run(self):
        try:
            # Запускаем сервер статических файлов
            self.static_server = StaticFileServer(
                directory=STATIC_DIR,
                host=SERVER_HOST,
                port=STATIC_PORT
            )
            self.static_server.start()
            self.connection_status.emit("Сервер статических файлов запущен\nСервер успешно запущен.\nСервер запущен и ожидает подключений...")

            # Запускаем основной сервер
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(('0.0.0.0', 9999))
            self.server.listen(5)
            self.server.settimeout(1.0)
            self.running = True
            self.server_started.emit()
            
            while self.running:
                try:
                    client, address = self.server.accept()
                    with self._lock:
                        self.connected_clients += 1
                        self.connection_status.emit(f"Новое подключение с {address[0]}\nАктивных подключений: {self.connected_clients}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_message.emit(f"Ошибка при принятии подключения: {e}")
        except Exception as e:
            self.log_message.emit(f"Ошибка запуска сервера: {e}")
        finally:
            if self.server:
                self.server.close()
            if self.static_server:
                self.static_server.stop()
            self.running = False
            self.server_stopped.emit()

    def handle_client(self, client_socket, address):
        try:
            client_socket.settimeout(5.0)
            
            while self.running:
                try:
                    length_prefix = client_socket.recv(4)
                    if not length_prefix:
                        break
                    
                    message_length = struct.unpack('!I', length_prefix)[0]
                    
                    chunks = []
                    bytes_recd = 0
                    while bytes_recd < message_length:
                        chunk = client_socket.recv(min(message_length - bytes_recd, 2048))
                        if not chunk:
                            return
                        chunks.append(chunk)
                        bytes_recd += len(chunk)
                    
                    data = b''.join(chunks)
                    
                    try:
                        request_data = json.loads(data.decode('utf-8'))
                        action = request_data.get('action')
                        
                        if action == 'login':
                            self.handle_login(client_socket, address, request_data)
                        elif action == 'register':
                            self.handle_register(client_socket, address, request_data)
                        elif action == 'get_lab_works':
                            self.handle_get_lab_works(client_socket, address)
                        elif action == 'check_lab_completed':
                            self.handle_check_lab_completed(client_socket, address, request_data)
                        elif action == 'get_questions':
                            self.handle_get_questions(client_socket, address, request_data)
                        elif action == 'submit_test':
                            self.handle_submit_test(client_socket, address, request_data)
                        elif action == 'get_student_info':
                            self.handle_get_student_info(client_socket, address, request_data)
                        else:
                            response = {
                                'status': 'error',
                                'message': 'Неизвестное действие'
                            }
                            self.send_response(client_socket, response)
                    except json.JSONDecodeError as e:
                        self.log_message.emit(f"Ошибка декодирования JSON от {address[0]}: {e}")
                        self.send_response(client_socket, {
                            'status': 'error',
                            'message': 'Неверный формат данных'
                        })
                    except Exception as e:
                        self.log_message.emit(f"Ошибка обработки данных от {address[0]}: {e}")
                        self.send_response(client_socket, {
                            'status': 'error',
                            'message': 'Внутренняя ошибка сервера'
                        })
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_message.emit(f"Ошибка при обработке запроса от {address[0]}: {e}")
                    break
        finally:
            with self._lock:
                self.connected_clients = max(0, self.connected_clients - 1)
                if address in self.active_sessions:
                    client_info = self.active_sessions[address]['info']
                    self.log_message.emit(f"Клиент отключен: {client_info['name']} ({address[0]})")
                    del self.active_sessions[address]
                self.connection_status.emit(f"Активных подключений: {self.connected_clients}")
            client_socket.close()
    
    def send_response(self, client_socket, response):
        """Отправляет ответ клиенту"""
        try:
            response_data = json.dumps(response).encode('utf-8')
            length_prefix = struct.pack('!I', len(response_data))
            client_socket.sendall(length_prefix + response_data)
        except Exception as e:
            self.log_message.emit(f"Ошибка отправки ответа: {e}")

    def handle_login(self, client_socket, address, request_data):
        """Обрабатывает запрос на вход в систему"""
        try:
            data = request_data.get('data', {})
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            middle_name = data.get('middle_name', '')
            group_name = data.get('group_name')
            year = data.get('year')
            
            if not all([first_name, last_name, group_name, year]):
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Необходимо заполнить все обязательные поля'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Получаем информацию о студенте
            cursor.execute(
                "SELECT id, first_name, last_name, middle_name, group_name FROM students WHERE first_name=? AND last_name=? AND middle_name=? AND group_name=? AND year=?",
                (first_name, last_name, middle_name, group_name, year)
            )
            student_row = cursor.fetchone()
            conn.close()
            
            if not student_row:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Студент не найден'
                })
                return
            
            student_id = student_row[0]
            student_fio = f"{student_row[2]} {student_row[1]}"
            if student_row[3]:
                student_fio += f" {student_row[3]}"
            student_group = student_row[4]
            
            # Добавляем сессию в список активных
            with self._lock:
                session = {
                    'id': student_id,
                    'name': student_fio,
                    'group': student_group,
                    'lab_work': 'Не выбрана',
                    'start_time': datetime.now(),
                    'status': 'Авторизован'
                }
                self.active_sessions[student_id] = session
            
            msg = f"Студент {student_fio} (группа {student_group}) вошел в систему"
            self.log_message.emit(msg)
            
            self.send_response(client_socket, {
                'status': 'success',
                'data': {
                    'student_id': student_id,
                    'name': student_fio,
                    'group': student_group
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка при обработке входа: {str(e)}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Внутренняя ошибка сервера'
            })

    def handle_get_lab_works(self, client_socket, address):
        """Обрабатывает запрос на получение списка лабораторных работ"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, theme, time FROM lab_works")
            lab_works = cursor.fetchall()
            conn.close()
            
            response = {
                'status': 'success',
                'data': {
                    'lab_works': [
                        {'id': row[0], 'theme': row[1], 'time': row[2]}
                        for row in lab_works
                    ]
                }
            }
            self.send_response(client_socket, response)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка лабораторных работ: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Ошибка при получении списка лабораторных работ'
            })

    def handle_check_lab_completed(self, client_socket, address, request_data):
        """Обрабатывает запрос на проверку статуса выполнения лабораторной работы"""
        try:
            data = request_data.get('data', {})
            student_id = data.get('student_id')
            lab_id = data.get('lab_id')
            
            if not student_id or not lab_id:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Необходимо указать student_id и lab_id'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM results WHERE student_id=? AND lab_id=?",
                (student_id, lab_id)
            )
            result = cursor.fetchone()
            conn.close()
            
            self.log_message.emit(f"Проверка статуса лабораторной работы {lab_id} для студента {student_id}")
            self.send_response(client_socket, {
                'status': 'success',
                'data': {'completed': bool(result)}
            })
        except Exception as e:
            self.log_message.emit(f"Ошибка при проверке статуса лабораторной работы: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Ошибка при проверке статуса лабораторной работы'
            })

    def handle_get_questions(self, client_socket, address, request_data):
        """Обрабатывает запрос на получение вопросов для лабораторной работы"""
        try:
            data = request_data.get('data', {})
            lab_id = data.get('lab_id')
            student_id = data.get('student_id')
            
            if not lab_id or not student_id:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Необходимо предоставить lab_id и student_id'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Получаем информацию о лабораторной работе
            cursor.execute("SELECT theme, time FROM lab_works WHERE id=?", (lab_id,))
            lab_row = cursor.fetchone()
            
            if not lab_row:
                conn.close()
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Лабораторная работа не найдена'
                })
                return
            
            lab_theme = lab_row[0]
            lab_time = lab_row[1]
            
            # Обновляем информацию о текущей лабораторной работе в сессии
            with self._lock:
                if student_id in self.active_sessions:
                    self.active_sessions[student_id]['lab_work'] = lab_theme
                    self.active_sessions[student_id]['status'] = 'Выполняет тест'
            
            # Получаем вопросы для лабораторной работы
            cursor.execute("""
                SELECT id, category, question_text, answer1, answer2, answer3, answer4, correct_index 
                FROM questions 
                WHERE lab_id=? 
                ORDER BY RANDOM() 
                LIMIT 5
            """, (lab_id,))
            
            questions = []
            for q in cursor.fetchall():
                question = {
                    'id': q[0],
                    'category': q[1],
                    'question_text': q[2] if not q[2].startswith('![image]') else f"![image](http://{SERVER_HOST}:{STATIC_PORT}/images/{q[2][9:-1]})",
                    'answers': [
                        q[3] if not q[3].startswith('![image]') else f"![image](http://{SERVER_HOST}:{STATIC_PORT}/images/{q[3][9:-1]})",
                        q[4] if not q[4].startswith('![image]') else f"![image](http://{SERVER_HOST}:{STATIC_PORT}/images/{q[4][9:-1]})",
                        q[5] if not q[5].startswith('![image]') else f"![image](http://{SERVER_HOST}:{STATIC_PORT}/images/{q[5][9:-1]})",
                        q[6] if not q[6].startswith('![image]') else f"![image](http://{SERVER_HOST}:{STATIC_PORT}/images/{q[6][9:-1]})"
                    ],
                    'correct_index': q[7]
                }
                questions.append(question)
            
            conn.close()
            
            self.send_response(client_socket, {
                'status': 'success',
                'data': {
                    'questions': questions,
                    'time_limit': lab_time
                }
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении вопросов: {str(e)}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Внутренняя ошибка сервера'
            })

    def handle_submit_test(self, client_socket, address, request_data):
        """Обрабатывает запрос на отправку результатов теста"""
        try:
            data = request_data.get('data', {})
            student_id = data.get('student_id')
            lab_id = data.get('lab_id')
            answers = data.get('answers', {})
            duration = data.get('duration', 0)  # Получаем длительность выполнения
            
            if not student_id or not lab_id or not answers:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Необходимо предоставить student_id, lab_id и ответы'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Получаем информацию о лабораторной работе
            cursor.execute("SELECT theme FROM lab_works WHERE id=?", (lab_id,))
            lab_row = cursor.fetchone()
            lab_theme = lab_row[0] if lab_row else "Неизвестно"

            # Получаем информацию о студенте
            cursor.execute("SELECT first_name, last_name, middle_name, group_name FROM students WHERE id=?", (student_id,))
            student_row = cursor.fetchone()
            if not student_row:
                conn.close()
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Студент не найден'
                })
                return
                
            student_fio = f"{student_row[1]} {student_row[0]}"
            if student_row[2]:
                student_fio += f" {student_row[2]}"
            student_group = student_row[3]
            
            # Проверяем, не сдана ли уже работа
            cursor.execute("SELECT id FROM results WHERE student_id=? AND lab_id=?", (student_id, lab_id))
            if cursor.fetchone():
                conn.close()
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Лабораторная работа уже выполнена'
                })
                return
            
            # Проверяем ответы
            cursor.execute("SELECT id, correct_index FROM questions WHERE lab_id=? ORDER BY id", (lab_id,))
            rows = cursor.fetchall()
            total_questions = len(rows)
            score = 0
            
            # Проверяем каждый ответ
            for q_id, user_answer in answers.items():
                # Находим вопрос в списке
                for question in rows:
                    if str(question[0]) == str(q_id):
                        # Сравниваем ответ студента с правильным ответом
                        if str(user_answer) == str(question[1]):
                            score += 1
                            self.log_message.emit(f"Вопрос {q_id}: правильный ответ")
                        else:
                            self.log_message.emit(f"Вопрос {q_id}: неправильный ответ (ответ студента: {user_answer}, правильный: {question[1]})")
                        break

            # Если набрано меньше 3 баллов
            if score < 3:
                msg = f"{student_fio} не прошел лабораторную работу '{lab_theme}'. Баллы: {score}/5"
                self.log_message.emit(msg)
                
                # Добавляем результат в список для отображения
                with self._lock:
                    self.test_results.append({
                        'time': datetime.now().strftime("%H:%M:%S"),
                        'name': student_fio,
                        'group': student_group,
                        'lab_work': lab_theme,
                        'result': f"{score}/5",
                        'duration': f"{duration//60}:{duration%60:02d}"
                    })
                
                conn.close()
                self.send_response(client_socket, {
                    'status': 'retake',
                    'message': f'Вы набрали {score}/5, лабораторная не засчитана.',
                    'data': {
                        'score': score,
                        'total_questions': total_questions
                    }
                })
                return
            
            # Сохраняем результат
            cursor.execute(
                "INSERT INTO results (student_id, lab_id, score, duration) VALUES (?, ?, ?, ?)", 
                (student_id, lab_id, score, duration)
            )
            conn.commit()
            conn.close()
            
            # Добавляем результат в список для отображения
            with self._lock:
                self.test_results.append({
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'name': student_fio,
                    'group': student_group,
                    'lab_work': lab_theme,
                    'result': f"{score}/5",
                    'duration': f"{duration//60}:{duration%60:02d}"
                })
            
            msg = f"{student_fio} прошел лабораторную работу '{lab_theme}' на {score} баллов из 5."
            self.log_message.emit(msg)
            
            self.send_response(client_socket, {
                'status': 'success',
                'data': {
                    'score': score,
                    'total_questions': total_questions
                }
            })
            
        except Exception as e:
            self.log_message.emit(f"Ошибка при обработке результатов теста: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Ошибка при обработке результатов теста'
            })

    def handle_get_student_info(self, client_socket, address, request_data):
        """Обрабатывает запрос на получение информации о студенте"""
        try:
            data = request_data.get('data', {})
            student_id = data.get('student_id')
            
            if not student_id:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Не указан student_id'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT first_name, last_name, middle_name, group_name FROM students WHERE id=?",
                (student_id,)
            )
            student = cursor.fetchone()
            conn.close()
            
            if student:
                self.send_response(client_socket, {
                    'status': 'success',
                    'data': {
                        'student': {
                            'first_name': student[0],
                            'last_name': student[1],
                            'middle_name': student[2],
                            'group_name': student[3]
                        }
                    }
                })
            else:
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Студент не найден'
                })
        except Exception as e:
            self.log_message.emit(f"Ошибка при получении информации о студенте: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Ошибка при получении информации о студенте'
            })

    def process_client_message(self, address, message):
        """Обрабатывает сообщения от аутентифицированного клиента"""
        try:
            if message.get('type') == 'test_result':
                self.add_test_result(address, message.get('data', {}))
            elif message.get('type') == 'lab_selected':
                with self._lock:
                    if address in self.active_sessions:
                        self.active_sessions[address]['info']['lab_work'] = message.get('lab_name', 'Не выбрана')
        except Exception as e:
            self.log_message.emit(f"Ошибка обработки сообщения: {e}")
    
    def add_test_result(self, address, result_data):
        with self._lock:
            if address in self.active_sessions:
                result = {
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'name': self.active_sessions[address]['info']['name'],
                    'group': self.active_sessions[address]['info']['group'],
                    'lab_work': result_data['lab_work'],
                    'result': result_data['score'],
                    'duration': result_data['duration']
                }
                self.test_results.append(result)
    
    def get_active_sessions(self):
        """Возвращает список активных сессий"""
        with self._lock:
            sessions = []
            current_time = datetime.now()
            for student_id, session in self.active_sessions.items():
                # Вычисляем продолжительность в секундах
                duration_td = current_time - session['start_time']
                duration_seconds = int(duration_td.total_seconds())
                
                sessions.append([
                    session['name'],
                    session['group'],
                    session['lab_work'],
                    str(student_id),  # Используем student_id вместо IP
                    f"{duration_seconds//60}:{duration_seconds%60:02d}",
                    session['status']
                ])
            return sessions
    
    def get_new_results(self):
        with self._lock:
            results = self.test_results.copy()
            self.test_results.clear()
            return results
    
    def stop_server(self):
        self.running = False
        if self.static_server:
            self.static_server.stop()
            self.log_message.emit("Сервер статических файлов остановлен")

    def handle_register(self, client_socket, address, request_data):
        """Обрабатывает запрос на регистрацию нового студента"""
        try:
            data = request_data.get('data', {})
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            middle_name = data.get('middle_name', '')
            group_name = data.get('group_name')
            year = data.get('year')
            
            if not all([first_name, last_name, group_name, year]):
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Необходимо заполнить все обязательные поля'
                })
                return
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже такой студент
            cursor.execute(
                "SELECT id FROM students WHERE first_name=? AND last_name=? AND middle_name=? AND group_name=? AND year=?",
                (first_name, last_name, middle_name, group_name, year)
            )
            existing_student = cursor.fetchone()
            
            if existing_student:
                conn.close()
                self.send_response(client_socket, {
                    'status': 'error',
                    'message': 'Студент с такими данными уже зарегистрирован'
                })
                return
            
            # Регистрируем нового студента
            cursor.execute(
                "INSERT INTO students (first_name, last_name, middle_name, group_name, year) VALUES (?, ?, ?, ?, ?)",
                (first_name, last_name, middle_name, group_name, year)
            )
            conn.commit()
            student_id = cursor.lastrowid
            conn.close()
            
            # Формируем ФИО для логов
            student_name = f"{last_name} {first_name}"
            if middle_name:
                student_name += f" {middle_name}"
            
            # Добавляем сессию
            with self._lock:
                self.active_sessions[address] = {
                    'info': {
                        'name': student_name,
                        'group': group_name,
                        'lab_work': 'Не выбрана',
                        'student_id': student_id
                    },
                    'start_time': datetime.now(),
                    'status': 'Активен'
                }
            
            self.log_message.emit(f"Зарегистрирован новый студент: {student_name} ({address[0]})")
            self.send_response(client_socket, {
                'status': 'success',
                'data': {'student_id': student_id}
            })
            
        except Exception as e:
            self.log_message.emit(f"Ошибка при регистрации студента: {e}")
            self.send_response(client_socket, {
                'status': 'error',
                'message': 'Ошибка при регистрации студента'
            })

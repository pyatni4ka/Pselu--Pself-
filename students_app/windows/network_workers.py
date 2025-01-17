"""
Модуль для работы с сетевыми запросами.

Обеспечивает асинхронное взаимодействие с сервером через TCP-сокеты.
Использует QRunnable для выполнения запросов в отдельном потоке.
"""

from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
import socket
import json
import logging
import os
import struct

class WorkerSignals(QObject):
    """
    Определяет сигналы для Worker.
    
    Signals:
        finished (dict): Отправляется при успешном завершении запроса
        error (str): Отправляется при возникновении ошибки
    """
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class Worker(QRunnable):
    """
    Класс для асинхронного выполнения сетевых запросов.
    
    Attributes:
        request (dict): Запрос для отправки на сервер
        signals (WorkerSignals): Сигналы для коммуникации с основным потоком
    """
    def __init__(self, request):
        super().__init__()
        self.request = request
        self.signals = WorkerSignals()

    def run(self):
        ip_file = "server_ip.txt"
        HOST = self.get_server_ip(ip_file)
        PORT = 9999
        logging.info(f"Попытка подключения к {HOST}:{PORT}")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Устанавливаем таймаут в 5 секунд
                sock.settimeout(5)
                logging.info("Создан сокет, пытаемся подключиться...")
                sock.connect((HOST, PORT))
                logging.info("Подключение успешно установлено")
                
                # Отправляем данные
                data = json.dumps(self.request).encode('utf-8')
                logging.info(f"Отправляем данные: {self.request}")
                sock.sendall(data)

                length_prefix = sock.recv(4)
                if not length_prefix:
                    error_msg = "No length prefix received from server."
                    logging.error(error_msg)
                    self.signals.error.emit(error_msg)
                    return
                message_length = struct.unpack('!I', length_prefix)[0]
                logging.info(f"Получен префикс длины: {message_length} байт")

                chunks = []
                bytes_recd = 0
                while bytes_recd < message_length:
                    chunk = sock.recv(min(message_length - bytes_recd, 2048))
                    if not chunk:
                        error_msg = "Connection closed while receiving data."
                        logging.error(error_msg)
                        self.signals.error.emit(error_msg)
                        return
                    chunks.append(chunk)
                    bytes_recd += len(chunk)
                    logging.info(f"Получено {bytes_recd} из {message_length} байт")

                response = b''.join(chunks)
                try:
                    data = json.loads(response.decode('utf-8'))
                    logging.info("Данные успешно получены и декодированы")
                    self.signals.finished.emit(data)
                except json.JSONDecodeError as e:
                    error_msg = f"Decoding error: {e}"
                    logging.error(error_msg)
                    self.signals.error.emit(error_msg)
        except ConnectionRefusedError:
            error_msg = f"Could not connect to server at {HOST}:{PORT}. Connection refused."
            logging.error(error_msg)
            self.signals.error.emit(error_msg)
        except socket.timeout:
            error_msg = f"Connection timeout while connecting to {HOST}:{PORT}"
            logging.error(error_msg)
            self.signals.error.emit(error_msg)
        except Exception as e:
            error_msg = f"Error connecting to {HOST}:{PORT}: {str(e)}"
            logging.error(error_msg)
            self.signals.error.emit(error_msg)

    def get_server_ip(self, ip_file):
        try:
            if os.path.exists(ip_file):
                with open(ip_file, "r") as f:
                    custom_ip = f.read().strip()
                    if custom_ip:
                        return custom_ip
            return "localhost"
        except Exception as e:
            logging.error(f"Ошибка чтения IP из файла {ip_file}: {e}")
            return "localhost"

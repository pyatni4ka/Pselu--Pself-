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
import traceback
from logger_config import get_logger
from config_manager import ConfigManager

logger = get_logger('network')

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
        self.config = ConfigManager()

    def run(self):
        try:
            HOST = self.config.get_server_host()
            PORT = self.config.get_server_port()
            logger.info(f"Попытка подключения к {HOST}:{PORT}")
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    # Устанавливаем таймаут в 5 секунд
                    sock.settimeout(5)
                    logger.info("Создан сокет, пытаемся подключиться...")
                    sock.connect((HOST, PORT))
                    logger.info("Подключение успешно установлено")
                    
                    # Отправляем данные
                    request_data = json.dumps(self.request).encode('utf-8')
                    length_prefix = struct.pack('!I', len(request_data))
                    logger.info(f"Отправляем данные: {self.request}")
                    sock.sendall(length_prefix + request_data)

                    # Получаем длину ответа
                    length_prefix = sock.recv(4)
                    if not length_prefix:
                        error_msg = "No length prefix received from server."
                        logger.error(error_msg)
                        self.signals.error.emit(error_msg)
                        return
                    message_length = struct.unpack('!I', length_prefix)[0]
                    logger.info(f"Получен префикс длины: {message_length} байт")

                    # Получаем данные
                    chunks = []
                    bytes_recd = 0
                    while bytes_recd < message_length:
                        chunk = sock.recv(min(message_length - bytes_recd, 2048))
                        if not chunk:
                            error_msg = "Connection closed while receiving data."
                            logger.error(error_msg)
                            self.signals.error.emit(error_msg)
                            return
                        chunks.append(chunk)
                        bytes_recd += len(chunk)
                        logger.info(f"Получено {bytes_recd} из {message_length} байт")

                    # Обрабатываем ответ
                    response = b''.join(chunks)
                    try:
                        data = json.loads(response.decode('utf-8'))
                        logger.info(f"Получен ответ: {data}")
                        self.signals.finished.emit(data)
                    except json.JSONDecodeError as e:
                        error_msg = f"Ошибка декодирования JSON: {e}"
                        logger.error(f"{error_msg}. Полученные данные: {response}")
                        self.signals.error.emit(error_msg)

            except ConnectionRefusedError:
                error_msg = f"Could not connect to server at {HOST}:{PORT}. Connection refused."
                logger.error(error_msg)
                self.signals.error.emit(error_msg)
            except socket.timeout:
                error_msg = f"Connection timeout while connecting to {HOST}:{PORT}"
                logger.error(error_msg)
                self.signals.error.emit(error_msg)
            except Exception as e:
                error_msg = f"Error connecting to {HOST}:{PORT}: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                self.signals.error.emit(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self.signals.error.emit(error_msg) 
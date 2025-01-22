import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
import codecs

def setup_logger():
    """Настраивает логирование для приложения."""
    # Принудительно устанавливаем кодировку системы
    if sys.platform == 'win32':
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
            except locale.Error:
                pass
    
    # Создаем директорию для логов, если её нет
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Создаем отдельную директорию для текущей сессии
    session_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(log_dir, session_time)
    os.makedirs(session_dir, exist_ok=True)
    
    # Пути к файлам логов
    client_log = os.path.join(session_dir, 'client.log')
    network_log = os.path.join(session_dir, 'network.log')
    
    # Настраиваем корневой логгер
    logger = logging.getLogger('students_app')
    logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Создаем форматтеры
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Создаем обработчики с явным указанием кодировки
    class Utf8RotatingFileHandler(RotatingFileHandler):
        def __init__(self, *args, **kwargs):
            kwargs['encoding'] = 'utf-8'
            super().__init__(*args, **kwargs)
        
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                if not isinstance(msg, bytes):
                    msg = msg.encode('utf-8')
                stream.write(msg.decode('utf-8'))
                stream.write(self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
    
    client_handler = Utf8RotatingFileHandler(
        client_log,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    client_handler.setLevel(logging.DEBUG)
    client_handler.setFormatter(detailed_formatter)
    
    network_handler = Utf8RotatingFileHandler(
        network_log,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    network_handler.setLevel(logging.DEBUG)
    network_handler.setFormatter(detailed_formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Добавляем фильтры для разделения логов
    class NetworkFilter(logging.Filter):
        def filter(self, record):
            return 'network' in record.name.lower()
            
    class ClientFilter(logging.Filter):
        def filter(self, record):
            return 'network' not in record.name.lower()
    
    client_handler.addFilter(ClientFilter())
    network_handler.addFilter(NetworkFilter())
    
    # Добавляем обработчики
    logger.addHandler(client_handler)
    logger.addHandler(network_handler)
    logger.addHandler(console_handler)
    
    # Устанавливаем propagate в False
    logger.propagate = False
    
    # Записываем тестовое сообщение для проверки кодировки
    logger.info("Логгер инициализирован. Проверка кодировки: русский текст")
    
    return logger

def get_logger(name):
    """Получает логгер для конкретного модуля."""
    logger = logging.getLogger(f'students_app.{name}')
    logger.setLevel(logging.DEBUG)
    return logger

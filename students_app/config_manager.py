"""
Модуль для работы с конфигурационным файлом.
"""

import os
import sys
import configparser
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        self._config = configparser.ConfigParser()
        
        # Определяем возможные пути к конфигурации
        paths = [
            'config.ini',  # В текущей директории
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini'),  # В корне проекта
            os.path.join(os.path.dirname(__file__), 'config.ini'),  # В директории приложения
        ]
        
        # Добавляем отладочную информацию
        logger.debug(f"Текущая директория: {os.getcwd()}")
        logger.debug(f"Проверяемые пути конфигурации: {paths}")
        
        # Если приложение скомпилировано
        if getattr(sys, 'frozen', False):
            exe_path = os.path.join(os.path.dirname(sys.executable), 'config.ini')
            paths.insert(0, exe_path)
            logger.debug(f"Путь к exe: {exe_path}")

        # Пробуем загрузить конфигурацию из всех возможных путей
        config_loaded = False
        for path in paths:
            logger.debug(f"Проверка пути: {path}")
            if os.path.exists(path):
                try:
                    self._config.read(path)
                    logger.info(f"Загружена конфигурация из {path}")
                    logger.debug(f"Содержимое конфигурации: {dict(self._config['Server'])}")
                    print(f"Загружена конфигурация из {path}")
                    config_loaded = True
                    break
                except Exception as e:
                    logger.error(f"Ошибка при загрузке конфигурации из {path}: {e}")

        if not config_loaded:
            logger.error("Не удалось загрузить конфигурацию")
            raise FileNotFoundError("Файл конфигурации не найден")

    def get_server_host(self):
        return self._config.get('Server', 'host', fallback='localhost')

    def get_server_port(self):
        return self._config.getint('Server', 'port', fallback=9999)

    def get_static_port(self):
        return self._config.getint('Server', 'static_port', fallback=8080)

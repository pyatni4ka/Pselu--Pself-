"""
Модуль для работы с конфигурационным файлом.
"""

import configparser
import os
import sys

DEFAULT_CONFIG = """[Server]
# IP-адрес сервера в локальной сети
# Измените на IP-адрес вашего сервера, например: 192.168.1.100
host = localhost

# Порт для основного сервера
port = 9999

# Порт для статического сервера (изображения)
static_port = 8080
"""

def get_config_path():
    """Получает путь к конфигурационному файлу."""
    if getattr(sys, 'frozen', False):
        # Если приложение скомпилировано, используем папку с exe файлом
        base_dir = os.path.dirname(sys.executable)
    else:
        # Если приложение запущено из исходников
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_dir, 'config.ini')

def create_default_config():
    """Создает конфигурационный файл со значениями по умолчанию."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG)
        print(f"Создан файл конфигурации: {config_path}")
    except Exception as e:
        print(f"Ошибка при создании файла конфигурации: {str(e)}")

def load_config():
    """Загружает конфигурацию из файла."""
    config = configparser.ConfigParser()
    config_path = get_config_path()
    
    # Если файл конфигурации не существует, создаем его
    if not os.path.exists(config_path):
        create_default_config()
    
    config.read(config_path, encoding='utf-8')
    return config

def get_server_settings():
    """Получает настройки сервера."""
    config = load_config()
    return {
        'host': config.get('Server', 'host', fallback='localhost'),
        'port': config.getint('Server', 'port', fallback=9999),
        'static_port': config.getint('Server', 'static_port', fallback=8080)
    }

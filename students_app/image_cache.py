"""
Модуль для кэширования изображений на клиенте.
"""

import os
import sys
import hashlib
import logging
from PIL import Image
from io import BytesIO
import requests
from urllib.parse import urlparse
import warnings
import urllib3

logger = logging.getLogger(__name__)

# Отключаем предупреждения о небезопасных запросах для локальной сети
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ImageCache:
    """Класс для кэширования изображений."""
    
    def __init__(self, cache_dir='image_cache'):
        """
        Инициализация кэша изображений.
        
        Args:
            cache_dir (str): Путь к директории кэша
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.cache_dir = os.path.join(base_dir, cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Инициализирован кэш изображений в {self.cache_dir}")
    
    def _get_cache_path(self, url):
        """Получает путь к кэшированному файлу."""
        # Создаем хэш URL для имени файла
        filename = hashlib.md5(url.encode()).hexdigest() + '.png'
        return os.path.join(self.cache_dir, filename)
    
    def get(self, url):
        """
        Получает изображение из кэша.
        
        Args:
            url (str): URL изображения
            
        Returns:
            QPixmap: Закэшированное изображение или None
        """
        cache_path = self._get_cache_path(url)
        if os.path.exists(cache_path):
            try:
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    return pixmap
            except Exception as e:
                logger.error(f"Ошибка при загрузке изображения из кэша: {str(e)}")
        return None
    
    def save(self, url, image):
        """
        Сохраняет изображение в кэш.
        
        Args:
            url (str): URL изображения
            image: PIL.Image или bytes
        """
        try:
            cache_path = self._get_cache_path(url)
            if isinstance(image, Image.Image):
                image.save(cache_path, format='PNG')
            else:
                with open(cache_path, 'wb') as f:
                    f.write(image)
            logger.info(f"Изображение сохранено в кэш: {url}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {str(e)}")

def get_cached_image(url):
    """
    Получает изображение из кэша или загружает его с сервера.
    
    Args:
        url (str): URL изображения
        
    Returns:
        str: Путь к локальному файлу изображения
    """
    # Создаем хэш URL для имени файла
    filename = hashlib.md5(url.encode()).hexdigest() + '.png'
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image_cache')
    os.makedirs(cache_dir, exist_ok=True)
    cached_path = os.path.join(cache_dir, filename)
    
    # Если файл уже есть в кэше, возвращаем его
    if os.path.exists(cached_path):
        logger.info(f"Изображение найдено в кэше: {url}")
        return cached_path
    
    # Если файла нет, пробуем загрузить его
    try:
        logger.info(f"Загрузка изображения: {url}")
        # Для локальной сети отключаем проверку SSL
        parsed_url = urlparse(url)
        if parsed_url.hostname in ['localhost', '127.0.0.1'] or parsed_url.hostname.startswith('192.168.'):
            response = requests.get(url, verify=False)
        else:
            response = requests.get(url)
        response.raise_for_status()
        
        # Сохраняем изображение в кэш
        with open(cached_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"Изображение сохранено в кэш: {url}")
        return cached_path
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения {url}: {str(e)}")
        return None

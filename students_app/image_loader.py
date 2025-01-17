"""
Модуль для загрузки и кэширования изображений.
"""

import os
import requests
import logging
from PIL import Image
from io import BytesIO
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, QByteArray
from PyQt5.QtGui import QPixmap
from image_cache import ImageCache

logger = logging.getLogger(__name__)

class WorkerSignals(QObject):
    """Определяет сигналы, доступные для Worker."""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    """Worker для загрузки изображений в отдельном потоке."""

    def __init__(self, url, cache_dir='image_cache', max_size=(800, 600)):
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()
        self.cache = ImageCache(cache_dir)
        self.max_size = max_size

    @pyqtSlot()
    def run(self):
        """Основной метод для загрузки и обработки изображения."""
        try:
            # Проверяем кэш
            cached_image = self.cache.get(self.url)
            if cached_image:
                logger.info(f"Изображение найдено в кэше: {self.url}")
                self.signals.result.emit(cached_image)
                self.signals.finished.emit()
                return

            # Загружаем изображение
            logger.info(f"Загрузка изображения: {self.url}")
            response = requests.get(self.url)
            response.raise_for_status()

            # Открываем изображение с помощью PIL
            image = Image.open(BytesIO(response.content))

            # Изменяем размер, если необходимо
            if image.size[0] > self.max_size[0] or image.size[1] > self.max_size[1]:
                image.thumbnail(self.max_size, Image.Resampling.LANCZOS)

            # Сохраняем в кэш
            self.cache.save(self.url, image)

            # Конвертируем в QPixmap
            pixmap = self._pil_to_pixmap(image)
            
            self.signals.result.emit(pixmap)

        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {str(e)}")
            self.signals.error.emit((str(e), None))
        
        finally:
            self.signals.finished.emit()

    def _pil_to_pixmap(self, pil_image):
        """Конвертирует PIL Image в QPixmap."""
        # Сохраняем во временный буфер
        buffer = BytesIO()
        pil_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Создаем QPixmap из данных буфера
        pixmap = QPixmap()
        data = QByteArray(buffer.getvalue())
        pixmap.loadFromData(data)
        
        return pixmap

def get_cached_image(url: str, cache_dir: str = 'image_cache') -> str:
    """
    Получает изображение из кэша или загружает его с сервера.
    
    Args:
        url (str): URL изображения
        cache_dir (str): Директория для кэширования
        
    Returns:
        str: Путь к изображению в кэше
    """
    cache = ImageCache(cache_dir)
    return cache.get_image(url)

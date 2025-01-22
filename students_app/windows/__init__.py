"""
Пакет с окнами приложения.
"""

import os
import sys

# Добавляем путь к корневой директории проекта в PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Пустой файл, чтобы Python распознал windows как пакет

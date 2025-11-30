#!/usr/bin/env python3
"""
Image Data Annotator
Приложение для автоматического добавления данных из Excel на скриншоты.

Запуск: python main.py
"""
import sys
import os

# Добавляем путь к src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui.main_window import MainWindow


def main():
    """Точка входа в приложение."""
    # Включаем High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Image Data Annotator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ImageDataAnnotator")
    
    # Устанавливаем стиль
    app.setStyle("Fusion")
    
    # Устанавливаем шрифт
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Создаём и показываем главное окно
    window = MainWindow()
    window.show()
    
    # Запускаем event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt6.QtGui import QAction, QColor, QIcon, QImage, QPixmap, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSlider, QSplitter, QWidget, QMessageBox,
    QScrollArea, QGroupBox, QFrame, QToolBar, QLineEdit
)

from PIL import Image, ImageEnhance

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

class ImageLabel(QLabel):
    """Виджет для отображения изображения с возможностью выделения."""
    selection_changed = pyqtSignal(QRect)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setMouseTracking(True)
        self._pixmap: Optional[QPixmap] = None
        self._selection_rect: Optional[QRect] = None
        self._is_selecting = False
        self._start_pos: Optional[QPoint] = None
        
        # Стилизация курсора
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.setPixmap(pixmap)
        self._selection_rect = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            self._is_selecting = True
            self._start_pos = event.pos()
            self._selection_rect = QRect(self._start_pos, self._start_pos)
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_selecting and self._start_pos:
            self._selection_rect = QRect(self._start_pos, event.pos()).normalized()
            # Ограничиваем выделение размерами изображения
            if self._pixmap:
                rect = self._selection_rect.intersected(self._pixmap.rect())
                self._selection_rect = rect
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            if self._selection_rect and self._selection_rect.isValid():
                # Проверяем минимальный размер
                if self._selection_rect.width() > 10 and self._selection_rect.height() > 10:
                    self.selection_changed.emit(self._selection_rect)
                else:
                    self._selection_rect = None
                    self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._selection_rect:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(34, 139, 230), 2, Qt.PenStyle.SolidLine)) # Синяя рамка
            painter.setBrush(QBrush(QColor(34, 139, 230, 50))) # Полупрозрачная заливка
            painter.drawRect(self._selection_rect)


class StampEditor(QDialog):
    """Редактор печатей."""
    stamp_saved = pyqtSignal(str) # Сигнал отправляет путь к сохраненному файлу

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор печатей")
        self.resize(1000, 700)
        
        self._source_image_path: Optional[str] = None
        self._pil_image: Optional[Image.Image] = None
        self._crop_rect: Optional[tuple] = None # (left, top, right, bottom)
        self._preview_image: Optional[Image.Image] = None
        
        self._setup_ui()
        
        # Создаем папку для печатей если нет
        self.stamps_dir = Path("stamps")
        self.stamps_dir.mkdir(exist_ok=True)

    def _setup_ui(self):
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Тулбар
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { background-color: #f8f9fa; border-bottom: 1px solid #dee2e6; padding: 5px; }")
        
        load_action = QAction("Загрузить файл", self)
        load_action.triggered.connect(self._load_file)
        toolbar.addAction(load_action)
        
        main_layout.addWidget(toolbar)

        # Рабочая область
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Левая часть: Исходное изображение
        source_group = QGroupBox("Исходный документ")
        source_layout = QVBoxLayout(source_group)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.source_label = ImageLabel()
        self.source_label.selection_changed.connect(self._on_selection_changed)
        self.scroll_area.setWidget(self.source_label)
        
        source_layout.addWidget(self.scroll_area)
        
        # Правая часть: Настройки и превью
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Превью
        preview_group = QGroupBox("Предпросмотр печати")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("Выделите область на изображении")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #fff; border: 1px solid #dee2e6; border-radius: 4px;")
        self.preview_label.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_label)
        right_layout.addWidget(preview_group)
        
        # Настройки
        settings_group = QGroupBox("Обработка")
        settings_layout = QVBoxLayout(settings_group)

        # Размер выделения
        self.selection_size_label = QLabel("Размер выделения: не выбрано")
        self.selection_size_label.setStyleSheet("color: #495057; font-weight: bold;")
        settings_layout.addWidget(self.selection_size_label)

        settings_layout.addSpacing(10)

        settings_layout.addWidget(QLabel("Порог удаления фона:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(200)
        self.threshold_slider.valueChanged.connect(self._update_preview)
        settings_layout.addWidget(self.threshold_slider)

        self.threshold_value_label = QLabel("200")
        self.threshold_slider.valueChanged.connect(lambda v: self.threshold_value_label.setText(str(v)))
        settings_layout.addWidget(self.threshold_value_label)
        
        settings_layout.addSpacing(10)
        
        self.invert_colors_btn = QPushButton("Инвертировать цвета (если печать светлая)")
        self.invert_colors_btn.setCheckable(True)
        self.invert_colors_btn.clicked.connect(self._update_preview)
        settings_layout.addWidget(self.invert_colors_btn)
        
        right_layout.addWidget(settings_group)

        # Название печати
        name_group = QGroupBox("Название печати")
        name_layout = QVBoxLayout(name_group)

        name_layout.addWidget(QLabel("Введите название:"))
        self.stamp_name_edit = QLineEdit()
        self.stamp_name_edit.setPlaceholderText("Например: Печать ООО Компания")
        self.stamp_name_edit.setText(f"Печать_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        name_layout.addWidget(self.stamp_name_edit)

        right_layout.addWidget(name_group)

        right_layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Сохранить печать")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("background-color: #228be6; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self._save_stamp)
        
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        
        right_layout.addLayout(buttons_layout)
        
        content_layout.addWidget(source_group, 1)
        content_layout.addWidget(right_panel)
        
        main_layout.addWidget(content_widget)

    def _load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Images/PDF (*.png *.jpg *.jpeg *.pdf)"
        )
        if not file_path:
            return

        try:
            if file_path.lower().endswith('.pdf'):
                if not HAS_PDF2IMAGE:
                    QMessageBox.critical(self, "Ошибка", "Библиотека pdf2image или poppler не установлены.\nЗагрузка PDF недоступна.")
                    return
                
                # Конвертируем первую страницу PDF в изображение
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if images:
                    self._pil_image = images[0]
                else:
                    raise Exception("Не удалось прочитать PDF")
            else:
                self._pil_image = Image.open(file_path)

            # Конвертируем для отображения в Qt
            self._display_source_image()
            
            self.preview_label.setText("Выделите область с печатью")
            self.save_btn.setEnabled(False)
            self._crop_rect = None

        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))

    def _display_source_image(self):
        if not self._pil_image:
            return
            
        # Конвертация PIL -> QPixmap
        im = self._pil_image.convert("RGBA")
        data = im.tobytes("raw", "RGBA")
        qim = QImage(data, im.width, im.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qim)
        
        self.source_label.set_image(pixmap)
        self.source_label.adjustSize()

    def _on_selection_changed(self, rect: QRect):
        # Конвертируем координаты QRect в координаты PIL Image
        # (здесь они 1 к 1, так как мы не масштабируем изображение в QLabel,
        # но оно прокручивается в ScrollArea)
        self._crop_rect = (rect.left(), rect.top(), rect.right(), rect.bottom())

        # Обновляем размер выделения
        width = rect.width()
        height = rect.height()
        self.selection_size_label.setText(f"Размер выделения: {width} x {height} px")

        self._update_preview()
        self.save_btn.setEnabled(True)

    def _update_preview(self):
        if not self._pil_image or not self._crop_rect:
            return

        # 1. Crop
        cropped = self._pil_image.crop(self._crop_rect)
        
        # 2. Invert (if needed)
        if self.invert_colors_btn.isChecked():
            # Для инверсии нужно RGB
            if cropped.mode == 'RGBA':
                r, g, b, a = cropped.split()
                rgb_image = Image.merge('RGB', (r, g, b))
                inverted_image = Image.eval(rgb_image, lambda x: 255 - x)
                r2, g2, b2 = inverted_image.split()
                cropped = Image.merge('RGBA', (r2, g2, b2, a))
            else:
                cropped = Image.eval(cropped, lambda x: 255 - x)

        # 3. Remove background
        threshold = self.threshold_slider.value()
        cropped = cropped.convert("RGBA")
        datas = cropped.getdata()
        
        new_data = []
        for item in datas:
            # item = (R, G, B, A)
            # Если пиксель светлый (близкий к белому)
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                new_data.append((255, 255, 255, 0)) # Transparent
            else:
                new_data.append(item)
        
        cropped.putdata(new_data)
        
        self._preview_image = cropped
        
        # Display preview
        data = cropped.tobytes("raw", "RGBA")
        qim = QImage(data, cropped.width, cropped.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qim)
        
        # Масштабируем для превью если нужно
        if pixmap.width() > self.preview_label.width() or pixmap.height() > self.preview_label.height():
             pixmap = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
             
        self.preview_label.setPixmap(pixmap)

    def _save_stamp(self):
        if not self._preview_image:
            return

        try:
            # Получаем название от пользователя
            stamp_name = self.stamp_name_edit.text().strip()
            if not stamp_name:
                stamp_name = f"stamp_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

            # Очищаем название от недопустимых символов
            stamp_name = "".join(c for c in stamp_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not stamp_name:
                stamp_name = f"stamp_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

            filename = f"{stamp_name}.png"
            save_path = self.stamps_dir / filename

            # Проверяем, существует ли файл
            if save_path.exists():
                reply = QMessageBox.question(
                    self,
                    "Файл существует",
                    f"Файл с названием '{filename}' уже существует.\nПерезаписать?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            self._preview_image.save(save_path, "PNG")

            QMessageBox.information(self, "Успех", f"Печать сохранена:\n{save_path}")
            self.stamp_saved.emit(str(save_path.absolute()))
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))
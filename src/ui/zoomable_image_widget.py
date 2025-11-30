"""Виджет для масштабируемого просмотра изображений."""
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPixmap, QWheelEvent, QMouseEvent, QPainter
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel
)


class ZoomableImageView(QGraphicsView):
    """QGraphicsView с поддержкой масштабирования."""

    zoomChanged = pyqtSignal(float)  # Сигнал об изменении масштаба

    def __init__(self, parent=None):
        super().__init__(parent)

        # Настройка сцены
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Элемент изображения
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # Параметры масштабирования
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._zoom_step = 0.1

        # Настройки отображения
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)

        # Переменные для перетаскивания
        self._is_panning = False
        self._pan_start_pos = QPoint()

    def setPixmap(self, pixmap: QPixmap):
        """Установить изображение для отображения."""
        if pixmap and not pixmap.isNull():
            self.pixmap_item.setPixmap(pixmap)
            self.pixmap_item.setTransformationMode(
                Qt.TransformationMode.SmoothTransformation
            )
            # Подгоняем размер сцены под изображение
            self.setSceneRect(QRectF(pixmap.rect()))
            # Сбрасываем масштаб
            self.fitInView()

    def fitInView(self):
        """Подогнать изображение под размер окна."""
        if not self.pixmap_item.pixmap().isNull():
            self.resetTransform()
            self._zoom = 1.0
            # Вписываем в видимую область с сохранением пропорций
            rect = QRectF(self.pixmap_item.pixmap().rect())
            if not rect.isNull():
                self.setSceneRect(rect)
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(
                    viewrect.width() / scenerect.width(),
                    viewrect.height() / scenerect.height()
                )
                self.scale(factor, factor)
                self._zoom = factor
                self.zoomChanged.emit(self._zoom * 100)

    def setZoom(self, zoom_percent: float):
        """Установить масштаб в процентах (100 = оригинальный размер)."""
        zoom_factor = zoom_percent / 100.0
        if self._min_zoom <= zoom_factor <= self._max_zoom:
            # Сбрасываем трансформацию и применяем новый масштаб
            self.resetTransform()
            self.scale(zoom_factor, zoom_factor)
            self._zoom = zoom_factor
            self.zoomChanged.emit(zoom_percent)

    def zoomIn(self):
        """Увеличить масштаб."""
        new_zoom = self._zoom * (1 + self._zoom_step)
        if new_zoom <= self._max_zoom:
            factor = 1 + self._zoom_step
            self.scale(factor, factor)
            self._zoom = new_zoom
            self.zoomChanged.emit(self._zoom * 100)

    def zoomOut(self):
        """Уменьшить масштаб."""
        new_zoom = self._zoom / (1 + self._zoom_step)
        if new_zoom >= self._min_zoom:
            factor = 1 / (1 + self._zoom_step)
            self.scale(factor, factor)
            self._zoom = new_zoom
            self.zoomChanged.emit(self._zoom * 100)

    def resetZoom(self):
        """Сбросить масштаб до 100%."""
        self.resetTransform()
        self._zoom = 1.0
        self.scale(1.0, 1.0)
        self.zoomChanged.emit(100)

    def wheelEvent(self, event: QWheelEvent):
        """Обработка прокрутки колеса мыши для масштабирования."""
        # Масштабируем при прокрутке с зажатым Ctrl
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Получаем направление прокрутки
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn()
            else:
                self.zoomOut()
            event.accept()
        else:
            # Обычная прокрутка
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия мыши."""
        if event.button() == Qt.MouseButton.MiddleButton:
            # Средняя кнопка - режим панорамирования
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка перемещения мыши."""
        if self._is_panning:
            # Панорамирование изображения
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Обработка отпускания мыши."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ZoomableImageWidget(QWidget):
    """Виджет с элементами управления масштабированием."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Виджет просмотра
        self.image_view = ZoomableImageView()
        main_layout.addWidget(self.image_view)

        # Панель управления масштабом
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(5, 5, 5, 5)

        # Кнопка "Вписать в окно"
        self.fit_button = QPushButton("По размеру окна")
        self.fit_button.setMaximumWidth(120)
        self.fit_button.clicked.connect(self.image_view.fitInView)
        controls_layout.addWidget(self.fit_button)

        # Кнопка "100%"
        self.reset_button = QPushButton("100%")
        self.reset_button.setMaximumWidth(60)
        self.reset_button.clicked.connect(self.image_view.resetZoom)
        controls_layout.addWidget(self.reset_button)

        # Кнопка уменьшения
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.clicked.connect(self.image_view.zoomOut)
        controls_layout.addWidget(self.zoom_out_button)

        # Слайдер масштаба
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)  # 10%
        self.zoom_slider.setMaximum(1000)  # 1000%
        self.zoom_slider.setValue(100)  # 100%
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(100)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        controls_layout.addWidget(self.zoom_slider)

        # Кнопка увеличения
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.clicked.connect(self.image_view.zoomIn)
        controls_layout.addWidget(self.zoom_in_button)

        # Метка со значением масштаба
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.zoom_label)

        # Подсказка
        self.hint_label = QLabel("💡 Ctrl + колесо мыши для масштабирования")
        self.hint_label.setStyleSheet("color: gray; font-size: 10px;")
        controls_layout.addWidget(self.hint_label)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # Подключаем сигналы
        self.image_view.zoomChanged.connect(self._on_zoom_changed)

    def setPixmap(self, pixmap: QPixmap):
        """Установить изображение для отображения."""
        self.image_view.setPixmap(pixmap)

    def setText(self, text: str):
        """Установить текст (для совместимости с QLabel)."""
        # Можно добавить отображение текста при отсутствии изображения
        pass

    def _on_slider_changed(self, value: int):
        """Обработка изменения слайдера."""
        # Отключаем обновление при программном изменении
        self.image_view.zoomChanged.disconnect(self._on_zoom_changed)
        self.image_view.setZoom(value)
        self.zoom_label.setText(f"{value}%")
        self.image_view.zoomChanged.connect(self._on_zoom_changed)

    def _on_zoom_changed(self, zoom_percent: float):
        """Обработка изменения масштаба."""
        zoom_int = int(zoom_percent)
        self.zoom_slider.setValue(zoom_int)
        self.zoom_label.setText(f"{zoom_int}%")

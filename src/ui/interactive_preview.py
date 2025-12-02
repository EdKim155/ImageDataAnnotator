"""Интерактивное превью с возможностью перемещения элементов."""
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPixmap, QColor, QPen, QBrush, QFont, QPainter, QImage,
    QWheelEvent, QMouseEvent
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem,
    QGraphicsTextItem, QGraphicsRectItem, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QSlider, QLabel, QGroupBox, QCheckBox,
    QSizePolicy
)


class DraggableTextItem(QGraphicsTextItem):
    """Перетаскиваемый текстовый элемент."""

    positionChanged = pyqtSignal(str, float, float)  # name, x, y

    def __init__(self, text: str, name: str, parent=None):
        super().__init__(text, parent)
        self.item_name = name
        self.original_pos = QPointF(0, 0)

        # Настройка флагов (Context7 best practice)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Визуальное выделение при наведении
        self.setAcceptHoverEvents(True)
        self._is_hovered = False

    def itemChange(self, change, value):
        """Отслеживание изменений позиции (Context7 best practice)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.positionChanged.emit(self.item_name, pos.x(), pos.y())
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        """Визуальная подсказка при наведении."""
        self._is_hovered = True
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        # Добавляем полупрозрачный фон
        self.setDefaultTextColor(QColor(33, 150, 243))  # Синий цвет
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Убираем подсветку."""
        self._is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setDefaultTextColor(QColor(0, 0, 0))  # Черный цвет
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Изменение курсора при захвате."""
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Восстановление курсора."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def boundingRect(self):
        """Расширяем границы для корректной отрисовки рамки выделения."""
        return super().boundingRect().adjusted(-2, -2, 2, 2)

    def paint(self, painter, option, widget=None):
        """Кастомная отрисовка с рамкой при выделении."""
        super().paint(painter, option, widget)
        if self.isSelected() or self._is_hovered:
            # Рисуем пунктирную рамку
            rect = self.boundingRect()
            pen = QPen(QColor(33, 150, 243), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)


class PixmapItemSignals(QObject):
    """Вспомогательный класс для сигналов QGraphicsPixmapItem."""
    positionChanged = pyqtSignal(str, float, float)  # name, x, y


class DraggablePixmapItem(QGraphicsPixmapItem):
    """Перетаскиваемое изображение (печать)."""

    def __init__(self, pixmap: QPixmap, name: str, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)

        # Создаем объект для сигналов (композиция вместо множественного наследования)
        self._signals = PixmapItemSignals()
        self.positionChanged = self._signals.positionChanged

        self.item_name = name
        self.original_pos = QPointF(0, 0)

        # Настройка флагов (Context7 best practice)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Визуальное выделение
        self.setAcceptHoverEvents(True)
        self._is_hovered = False
        self._selection_rect = None

    def itemChange(self, change, value):
        """Отслеживание изменений позиции."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.positionChanged.emit(self.item_name, pos.x(), pos.y())
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        """Визуальная подсказка при наведении."""
        self._is_hovered = True
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Убираем подсветку."""
        self._is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Изменение курсора при захвате."""
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Восстановление курсора."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def boundingRect(self):
        """Расширяем границы для корректной отрисовки рамки выделения."""
        return super().boundingRect().adjusted(-2, -2, 2, 2)

    def paint(self, painter, option, widget=None):
        """Кастомная отрисовка с рамкой при выделении."""
        QGraphicsPixmapItem.paint(self, painter, option, widget)
        if self.isSelected() or self._is_hovered:
            # Рисуем рамку вокруг печати
            rect = self.boundingRect()
            pen = QPen(QColor(76, 175, 80), 3, Qt.PenStyle.DashLine)  # Зеленый
            painter.setPen(pen)
            painter.drawRect(rect)


class InteractivePreviewView(QGraphicsView):
    """QGraphicsView для интерактивного редактирования превью."""

    zoomChanged = pyqtSignal(float)
    elementsChanged = pyqtSignal(dict)  # Словарь со смещениями элементов

    def __init__(self, parent=None):
        super().__init__(parent)

        # Настройка сцены
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Фоновое изображение (не перемещаемое)
        self.background_item = QGraphicsPixmapItem()
        self.scene.addItem(self.background_item)

        # Интерактивные элементы
        self.draggable_items = {}  # {name: item}
        self.element_offsets = {}  # {name: (dx, dy)}

        # Параметры масштабирования
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._zoom_step = 0.1

        # Настройки отображения
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)  # Включаем выделение рамкой
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(200, 200, 200))

        # Режим редактирования
        self._edit_mode = True

    def setBackgroundPixmap(self, pixmap: QPixmap):
        """Установить фоновое изображение."""
        if pixmap and not pixmap.isNull():
            self.background_item.setPixmap(pixmap)
            self.setSceneRect(QRectF(pixmap.rect()))
            self.fitInView()

    def addDraggableText(self, text: str, name: str, x: float, y: float, font: QFont, color: QColor):
        """Добавить перетаскиваемый текст."""
        item = DraggableTextItem(text, name)
        item.setFont(font)
        item.setDefaultTextColor(color)
        item.setPos(x, y)
        item.original_pos = QPointF(x, y)
        item.positionChanged.connect(self._on_item_moved)

        self.scene.addItem(item)
        self.draggable_items[name] = item

        return item

    def addDraggablePixmap(self, pixmap: QPixmap, name: str, x: float, y: float):
        """Добавить перетаскиваемое изображение (печать)."""
        item = DraggablePixmapItem(pixmap, name)
        item.setPos(x, y)
        item.original_pos = QPointF(x, y)
        item.positionChanged.connect(self._on_item_moved)

        self.scene.addItem(item)
        self.draggable_items[name] = item

        return item

    def _on_item_moved(self, name: str, x: float, y: float):
        """Обработка перемещения элемента."""
        if name in self.draggable_items:
            item = self.draggable_items[name]
            # Вычисляем смещение от исходной позиции
            dx = x - item.original_pos.x()
            dy = y - item.original_pos.y()
            self.element_offsets[name] = (dx, dy)
            # Уведомляем об изменениях
            self.elementsChanged.emit(self.element_offsets)

    def getOffsets(self) -> Dict[str, Tuple[float, float]]:
        """Получить смещения всех элементов."""
        return self.element_offsets.copy()

    def resetOffsets(self):
        """Сбросить все смещения к исходным позициям."""
        for name, item in self.draggable_items.items():
            item.setPos(item.original_pos)
        self.element_offsets.clear()
        self.elementsChanged.emit(self.element_offsets)

    def clearDraggableItems(self):
        """Очистить все перетаскиваемые элементы."""
        for item in self.draggable_items.values():
            self.scene.removeItem(item)
        self.draggable_items.clear()
        self.element_offsets.clear()

    def setEditMode(self, enabled: bool):
        """Включить/выключить режим редактирования."""
        self._edit_mode = enabled
        # Включаем выделение рамкой в режиме редактирования
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag if enabled else QGraphicsView.DragMode.NoDrag)
        
        for item in self.draggable_items.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, enabled)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, enabled)

    # Методы масштабирования (аналогично ZoomableImageView)
    def fitInView(self):
        """Подогнать изображение под размер окна."""
        if not self.background_item.pixmap().isNull():
            self.resetTransform()
            self._zoom = 1.0
            rect = QRectF(self.background_item.pixmap().rect())
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
        """Установить масштаб в процентах."""
        zoom_factor = zoom_percent / 100.0
        if self._min_zoom <= zoom_factor <= self._max_zoom:
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
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn()
            else:
                self.zoomOut()
            event.accept()
        else:
            super().wheelEvent(event)


class InteractivePreviewWidget(QWidget):
    """Виджет интерактивного превью с элементами управления."""

    offsetsChanged = pyqtSignal(dict)
    updatePreviewRequested = pyqtSignal()  # Сигнал для обновления превью

    def __init__(self, parent=None):
        super().__init__(parent)

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Виджет просмотра
        self.preview_view = InteractivePreviewView()
        main_layout.addWidget(self.preview_view)

        # Панель управления
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(8, 4, 8, 4)
        controls_layout.setSpacing(12)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # --- ЛЕВАЯ ЧАСТЬ: Редактирование ---
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Режим редактирования
        self.edit_mode_checkbox = QCheckBox("Режим редактирования")
        self.edit_mode_checkbox.setChecked(True)
        self.edit_mode_checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.edit_mode_checkbox.stateChanged.connect(self._on_edit_mode_changed)
        left_layout.addWidget(self.edit_mode_checkbox)

        # Кнопка сброса позиций
        self.reset_positions_btn = QPushButton("Сбросить позиции")
        self.reset_positions_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.reset_positions_btn.clicked.connect(self.preview_view.resetOffsets)
        left_layout.addWidget(self.reset_positions_btn)
        
        controls_layout.addLayout(left_layout)
        controls_layout.addStretch()

        # --- ЦЕНТР: Масштабирование ---
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(6)
        zoom_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Кнопка "Вписать в окно"
        self.fit_button = QPushButton("По размеру окна")
        self.fit_button.setMaximumWidth(120)
        self.fit_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.fit_button.clicked.connect(self.preview_view.fitInView)
        zoom_layout.addWidget(self.fit_button)

        # Кнопка "100%"
        self.reset_button = QPushButton("100%")
        self.reset_button.setMaximumWidth(60)
        self.reset_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.reset_button.clicked.connect(self.preview_view.resetZoom)
        zoom_layout.addWidget(self.reset_button)

        # Кнопка уменьшения
        self.zoom_out_button = QPushButton("-")
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.zoom_out_button.clicked.connect(self.preview_view.zoomOut)
        zoom_layout.addWidget(self.zoom_out_button)

        # Слайдер масштаба
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(1000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.zoom_slider.setTickInterval(100)
        self.zoom_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        zoom_layout.addWidget(self.zoom_slider)

        # Кнопка увеличения
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.zoom_in_button.clicked.connect(self.preview_view.zoomIn)
        zoom_layout.addWidget(self.zoom_in_button)

        # Метка со значением масштаба
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        zoom_layout.addWidget(self.zoom_label)

        controls_layout.addLayout(zoom_layout)
        controls_layout.addStretch()
        
        # --- ПРАВАЯ ЧАСТЬ: Обновление (заполнитель) ---
        self.right_layout = QHBoxLayout()
        self.right_layout.setSpacing(8)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        controls_layout.addLayout(self.right_layout)

        main_layout.addLayout(controls_layout)

        # Подключаем сигналы
        self.preview_view.zoomChanged.connect(self._on_zoom_changed)
        self.preview_view.elementsChanged.connect(self.offsetsChanged)
        
    def addRightWidget(self, widget: QWidget):
        """Добавить виджет в правую часть панели управления."""
        widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.right_layout.addWidget(widget)

    def _on_slider_changed(self, value: int):
        """Обработка изменения слайдера."""
        self.preview_view.zoomChanged.disconnect(self._on_zoom_changed)
        self.preview_view.setZoom(value)
        self.zoom_label.setText(f"{value}%")
        self.preview_view.zoomChanged.connect(self._on_zoom_changed)

    def _on_zoom_changed(self, zoom_percent: float):
        """Обработка изменения масштаба."""
        zoom_int = int(zoom_percent)
        self.zoom_slider.setValue(zoom_int)
        self.zoom_label.setText(f"{zoom_int}%")

    def _on_edit_mode_changed(self, state):
        """Переключение режима редактирования."""
        enabled = state == Qt.CheckState.Checked.value
        self.preview_view.setEditMode(enabled)
        self.reset_positions_btn.setEnabled(enabled)

    def getOffsets(self) -> Dict[str, Tuple[float, float]]:
        """Получить смещения всех элементов."""
        return self.preview_view.getOffsets()

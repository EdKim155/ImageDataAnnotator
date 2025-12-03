"""Главное окно приложения Image Data Annotator."""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QThreadPool, pyqtSlot, QTimer, QPoint
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPixmap, QImage, QPalette, QCursor
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSpinBox, QStatusBar, QSystemTrayIcon, QMenu,
    QVBoxLayout, QWidget, QTabWidget, QTextEdit, QSizePolicy, QButtonGroup
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.excel_reader import ExcelReader
from core.image_processor import ImageProcessor, get_image_files
from core.worker import ProcessingWorker, ProcessingTask
from utils.settings import Settings
from utils.checkpoint import CheckpointManager
from ui.stamp_editor import StampEditor
from ui.zoomable_image_widget import ZoomableImageWidget
from ui.interactive_preview import InteractivePreviewWidget


class StampPreviewLabel(QLabel):
    """Всплывающее окно с превью печати."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #228be6;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(200, 200)
        self.setMaximumSize(400, 400)
        self.hide()


class StampComboBox(QComboBox):
    """ComboBox с превью печатей при наведении."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_label = StampPreviewLabel(parent)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._show_preview)
        self.current_hover_index = -1
        self.setMouseTracking(True)

        # Подключаемся к событию открытия выпадающего списка
        self.view().viewport().installEventFilter(self)
        self.view().viewport().setMouseTracking(True)

    def eventFilter(self, obj, event):
        """Фильтр событий для отслеживания наведения на элементы."""
        if obj == self.view().viewport():
            if event.type() == event.Type.MouseMove:
                # Получаем индекс элемента под курсором
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    row = index.row()
                    if row != self.current_hover_index and row > 0:  # Пропускаем первый элемент
                        self.current_hover_index = row
                        self.preview_timer.start(500)  # Задержка 500мс перед показом
                    elif row == 0:
                        self.preview_label.hide()
                        self.preview_timer.stop()
            elif event.type() == event.Type.Leave:
                self.preview_label.hide()
                self.preview_timer.stop()
                self.current_hover_index = -1

        return super().eventFilter(obj, event)

    def _show_preview(self):
        """Показать превью изображения печати."""
        if self.current_hover_index <= 0:
            return

        stamp_path = self.itemData(self.current_hover_index)
        if not stamp_path or not Path(stamp_path).exists():
            return

        try:
            # Загружаем изображение
            pixmap = QPixmap(stamp_path)
            if pixmap.isNull():
                return

            # Масштабируем для превью
            scaled_pixmap = pixmap.scaled(
                350, 350,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.adjustSize()

            # Получаем главное окно и координаты курсора
            main_window = self.window()
            cursor_pos = QCursor.pos()
            
            # Переводим глобальные координаты курсора в локальные координаты главного окна
            local_pos = main_window.mapFromGlobal(cursor_pos)

            # Начальная позиция (справа снизу от курсора)
            x = local_pos.x() + 20
            y = local_pos.y() + 20

            # Размеры
            preview_w = self.preview_label.width()
            preview_h = self.preview_label.height()
            window_w = main_window.width()
            window_h = main_window.height()

            # Проверка границ справа
            if x + preview_w > window_w:
                # Сдвигаем влево от курсора
                x = local_pos.x() - preview_w - 20

            # Проверка границ снизу
            if y + preview_h > window_h:
                # Сдвигаем вверх от курсора
                y = local_pos.y() - preview_h - 20

            # Финальная проверка на левую и верхнюю границы
            x = max(10, x)
            y = max(10, y)

            self.preview_label.move(x, y)
            self.preview_label.show()
            self.preview_label.raise_()

        except Exception as e:
            print(f"Ошибка показа превью: {e}")

    def hidePopup(self):
        """Переопределяем скрытие выпадающего списка."""
        self.preview_label.hide()
        self.preview_timer.stop()
        self.current_hover_index = -1
        super().hidePopup()


# Стили для светлой темы
LIGHT_THEME = """
QMainWindow {
    background-color: #f8f9fa;
    color: #212529;
}

QGroupBox {
    font-weight: bold;
    font-size: 11px;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    padding-left: 8px;
    padding-right: 8px;
    padding-bottom: 8px;
    background-color: #ffffff;
    color: #495057;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 6px;
    background-color: #ffffff;
    color: #495057;
}

QLineEdit {
    padding: 4px 8px;
    border: 1px solid #ced4da;
    border-radius: 6px;
    background-color: #ffffff;
    color: #000000;
    font-size: 11px;
    min-height: 20px;
}

QLineEdit:focus {
    border: 2px solid #4dabf7;
    background-color: #ffffff;
}

QLineEdit:disabled {
    background-color: #e9ecef;
    color: #adb5bd;
}

QPushButton {
    padding: 6px 12px;
    border: 1px solid #ced4da;
    border-radius: 6px;
    background-color: #ffffff;
    color: #000000;
    font-size: 11px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #e9ecef;
    border-color: #adb5bd;
}

QPushButton:pressed {
    background-color: #dee2e6;
}

QPushButton:disabled {
    background-color: #e9ecef;
    color: #adb5bd;
}

QPushButton#primaryButton {
    background-color: #228be6;
    color: white;
    border: none;
    font-weight: bold;
    padding: 10px 20px;
}

QPushButton#primaryButton:hover {
    background-color: #1c7ed6;
}

QPushButton#primaryButton:pressed {
    background-color: #1971c2;
}

QPushButton#dangerButton {
    background-color: #fa5252;
    color: white;
    border: none;
}

QPushButton#dangerButton:hover {
    background-color: #f03e3e;
}

QSpinBox {
    padding: 4px 8px;
    border: 1px solid #ced4da;
    border-radius: 6px;
    background-color: #ffffff;
    color: #000000;
    min-height: 20px;
}

QSpinBox:focus {
    border: 2px solid #4dabf7;
}

QCheckBox {
    font-size: 11px;
    spacing: 8px;
    color: #212529;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #ced4da;
}

QCheckBox::indicator:checked {
    background-color: #228be6;
    border-color: #228be6;
}

QRadioButton {
    font-size: 11px;
    spacing: 8px;
    color: #212529;
}

QTabWidget::pane {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    background-color: #ffffff;
    padding: 10px;
}

QTabBar::tab {
    padding: 10px 20px;
    margin-right: 4px;
    border: 1px solid #dee2e6;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background-color: #e9ecef;
    color: #495057;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 1px solid #ffffff;
    color: #212529;
}

QTabBar::tab:hover:!selected {
    background-color: #f1f3f4;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    background-color: #e9ecef;
    height: 24px;
    text-align: center;
    font-weight: bold;
    color: #000000;
}

QProgressBar::chunk {
    background-color: #51cf66;
    border-radius: 8px;
}

QTextEdit {
    border: 1px solid #dee2e6;
    border-radius: 6px;
    background-color: #f8f9fa;
    color: #000000;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QLabel {
    font-size: 11px;
    color: #495057;
}

QLabel#titleLabel {
    font-size: 14px;
    font-weight: bold;
    color: #212529;
}

QLabel#subtitleLabel {
    font-size: 11px;
    color: #868e96;
}

QStatusBar {
    background-color: #f1f3f5;
    border-top: 1px solid #dee2e6;
    color: #000000;
}

/* Специальные классы для контейнеров в скроллах */
QWidget#tabContainer {
    background-color: #ffffff;
}
"""

# Стили для темной темы
DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QGroupBox {
    font-weight: bold;
    font-size: 11px;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    padding-left: 8px;
    padding-right: 8px;
    padding-bottom: 8px;
    background-color: #252526;
    color: #e0e0e0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 6px;
    background-color: #252526;
    color: #e0e0e0;
}

QLineEdit {
    padding: 4px 8px;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    background-color: #333337;
    color: #f0f0f0;
    font-size: 11px;
    min-height: 20px;
}

QLineEdit:focus {
    border: 2px solid #228be6;
    background-color: #3e3e42;
}

QLineEdit:disabled {
    background-color: #2d2d30;
    color: #666666;
    border: 1px solid #3e3e42;
}

QPushButton {
    padding: 6px 12px;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    background-color: #333337;
    color: #f0f0f0;
    font-size: 11px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #3e3e42;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #252526;
}

QPushButton:disabled {
    background-color: #2d2d30;
    color: #666666;
    border: 1px solid #3e3e42;
}

QPushButton#primaryButton {
    background-color: #1971c2;
    color: white;
    border: none;
    font-weight: bold;
    padding: 10px 20px;
}

QPushButton#primaryButton:hover {
    background-color: #1c7ed6;
}

QPushButton#primaryButton:pressed {
    background-color: #1864ab;
}

QPushButton#dangerButton {
    background-color: #c92a2a;
    color: white;
    border: none;
}

QPushButton#dangerButton:hover {
    background-color: #e03131;
}

QSpinBox {
    padding: 4px 8px;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    background-color: #333337;
    color: #f0f0f0;
    min-height: 20px;
}

QSpinBox:focus {
    border: 2px solid #228be6;
}

QCheckBox {
    font-size: 11px;
    spacing: 8px;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3e3e42;
    background-color: #333337;
}

QCheckBox::indicator:checked {
    background-color: #228be6;
    border-color: #228be6;
}

QRadioButton {
    font-size: 11px;
    spacing: 8px;
    color: #e0e0e0;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 10px;
    border: 1px solid #3e3e42;
    background-color: #333337;
}

QRadioButton::indicator:checked {
    background-color: #228be6;
    border-color: #228be6;
}

QTabWidget::pane {
    border: 1px solid #3e3e42;
    border-radius: 8px;
    background-color: #252526;
    padding: 10px;
}

QTabBar::tab {
    padding: 10px 20px;
    margin-right: 4px;
    border: 1px solid #3e3e42;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background-color: #2d2d30;
    color: #aaaaaa;
}

QTabBar::tab:selected {
    background-color: #252526;
    border-bottom: 1px solid #252526;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #333337;
}

QProgressBar {
    border: none;
    border-radius: 8px;
    background-color: #2d2d30;
    height: 24px;
    text-align: center;
    font-weight: bold;
    color: #e0e0e0;
}

QProgressBar::chunk {
    background-color: #2f9e44;
    border-radius: 8px;
}

QTextEdit {
    border: 1px solid #3e3e42;
    border-radius: 6px;
    background-color: #1e1e1e;
    color: #f0f0f0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 10px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QLabel {
    font-size: 11px;
    color: #e0e0e0;
}

QLabel#titleLabel {
    font-size: 14px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#subtitleLabel {
    font-size: 11px;
    color: #aaaaaa;
}

QStatusBar {
    background-color: #252526;
    border-top: 1px solid #3e3e42;
    color: #e0e0e0;
}

/* Специальные классы для контейнеров в скроллах */
QWidget#tabContainer {
    background-color: #252526;
}
"""


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self):
        super().__init__()
        
        self.settings = Settings()
        self.excel_reader: Optional[ExcelReader] = None
        self.current_worker: Optional[ProcessingWorker] = None
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.thread_pool = QThreadPool()
        
        self._image_files: List[str] = []
        self._is_processing = False
        self._bg_color = "#FFFFFF"
        self._is_dark_mode = False
        
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()  # Подключаем сигналы ДО загрузки настроек
        self._load_settings()
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        self.setWindowTitle("Image Data Annotator")
        self.setMinimumSize(800, 700)
        self.resize(900, 800)
        self._apply_theme()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Вкладки с настройками
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_files_tab(), "Файлы")
        self.tabs.addTab(self._create_data_tab(), "Данные")
        self.tabs.addTab(self._create_output_tab(), "Вывод")
        self.tabs.addTab(self._create_preview_tab(), "Предпросмотр")
        main_layout.addWidget(self.tabs)
        
        # Блок статуса и прогресса
        main_layout.addWidget(self._create_status_panel())
        
        # Кнопки управления
        main_layout.addWidget(self._create_buttons_panel())
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
    
    def _create_header(self) -> QWidget:
        """Создание заголовка с переключателем темы."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(4)
        
        # Левая часть (Заголовки)
        titles_widget = QWidget()
        titles_layout = QVBoxLayout(titles_widget)
        titles_layout.setContentsMargins(0, 0, 0, 0)
        titles_layout.setSpacing(4)
        
        title = QLabel("Image Data Annotator")
        title.setObjectName("titleLabel")
        titles_layout.addWidget(title)
        
        subtitle = QLabel("Автоматическое добавление данных из Excel на скриншоты")
        subtitle.setObjectName("subtitleLabel")
        titles_layout.addWidget(subtitle)
        
        layout.addWidget(titles_widget)
        layout.addStretch()
        
        # Правая часть (Тема)
        self.theme_switch = QCheckBox("Тёмная тема")
        self.theme_switch.toggled.connect(self._toggle_theme)
        layout.addWidget(self.theme_switch)
        
        return widget
    
    def _create_files_tab(self) -> QWidget:
        """Вкладка выбора файлов."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Папка источник
        group1 = QGroupBox("Исходные изображения")
        g1_layout = QVBoxLayout(group1)
        
        h1 = QHBoxLayout()
        self.source_folder_edit = QLineEdit()
        self.source_folder_edit.setPlaceholderText("Путь к папке с исходными изображениями...")
        h1.addWidget(self.source_folder_edit)
        self.source_folder_btn = QPushButton("Обзор")
        self.source_folder_btn.setFixedWidth(100)
        self.source_folder_btn.clicked.connect(lambda: self._browse_folder(self.source_folder_edit))
        h1.addWidget(self.source_folder_btn)
        g1_layout.addLayout(h1)
        
        self.source_info = QLabel("Файлов не найдено")
        self.source_info.setObjectName("subtitleLabel")
        g1_layout.addWidget(self.source_info)
        
        layout.addWidget(group1)
        
        # Папка результат
        group2 = QGroupBox("Папка для результатов")
        g2_layout = QVBoxLayout(group2)
        
        h2 = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Путь для сохранения обработанных файлов...")
        h2.addWidget(self.output_folder_edit)
        self.output_folder_btn = QPushButton("Обзор")
        self.output_folder_btn.setFixedWidth(100)
        self.output_folder_btn.clicked.connect(lambda: self._browse_folder(self.output_folder_edit))
        h2.addWidget(self.output_folder_btn)
        g2_layout.addLayout(h2)
        
        layout.addWidget(group2)
        
        # Excel файл
        group3 = QGroupBox("Файл Excel с данными")
        g3_layout = QVBoxLayout(group3)
        
        h3 = QHBoxLayout()
        self.excel_file_edit = QLineEdit()
        self.excel_file_edit.setPlaceholderText("Путь к файлу Excel...")
        h3.addWidget(self.excel_file_edit)
        self.excel_file_btn = QPushButton("Обзор")
        self.excel_file_btn.setFixedWidth(100)
        self.excel_file_btn.clicked.connect(self._browse_excel)
        h3.addWidget(self.excel_file_btn)
        g3_layout.addLayout(h3)
        
        self.excel_info = QLabel("Файл не выбран")
        self.excel_info.setObjectName("subtitleLabel")
        g3_layout.addWidget(self.excel_info)
        
        layout.addWidget(group3)
        
        # Печать/подпись
        group4 = QGroupBox("Изображение печати/подписи (опционально)")
        g4_layout = QVBoxLayout(group4)

        # Выпадающий список сохранённых печатей
        h4a = QHBoxLayout()
        h4a.addWidget(QLabel("Быстрый выбор:"))
        self.stamps_combo = StampComboBox(self)
        self.stamps_combo.setMaximumWidth(250)
        self.stamps_combo.addItem("-- Выберите печать --", "")
        self.stamps_combo.currentIndexChanged.connect(self._on_stamp_selected)
        h4a.addWidget(self.stamps_combo)

        # Кнопка удаления печати
        delete_stamp_btn = QPushButton("🗑")
        delete_stamp_btn.setFixedSize(40, 30)
        delete_stamp_btn.setStyleSheet("QPushButton { font-size: 18px; }")
        delete_stamp_btn.setToolTip("Удалить выбранную печать")
        delete_stamp_btn.clicked.connect(self._delete_stamp)
        h4a.addWidget(delete_stamp_btn)
        g4_layout.addLayout(h4a)

        h4 = QHBoxLayout()
        self.stamp_file_edit = QLineEdit()
        self.stamp_file_edit.setPlaceholderText("Путь к изображению печати...")
        h4.addWidget(self.stamp_file_edit)

        self.stamp_editor_btn = QPushButton("Редактор")
        self.stamp_editor_btn.setFixedWidth(80)
        self.stamp_editor_btn.clicked.connect(self._open_stamp_editor)
        h4.addWidget(self.stamp_editor_btn)

        self.stamp_file_btn = QPushButton("Обзор")
        self.stamp_file_btn.setFixedWidth(80)
        self.stamp_file_btn.clicked.connect(self._browse_stamp)
        h4.addWidget(self.stamp_file_btn)
        g4_layout.addLayout(h4)

        layout.addWidget(group4)
        
        layout.addStretch()
        return widget

    def _open_stamp_editor(self):
        """Открытие редактора печатей."""
        editor = StampEditor(self)
        editor.stamp_saved.connect(lambda path: self.stamp_file_edit.setText(path))
        editor.stamp_saved.connect(lambda _: self._refresh_stamps_list())
        editor.exec()
    
    def _create_data_tab(self) -> QWidget:
        """Вкладка настройки данных."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Поля из Excel
        group1 = QGroupBox("Поля из Excel")
        g1_layout = QVBoxLayout(group1)
        
        # ИНН
        row1 = QHBoxLayout()
        self.inn_checkbox = QCheckBox("ИНН организации")
        self.inn_checkbox.setChecked(True)
        row1.addWidget(self.inn_checkbox)
        row1.addStretch()
        row1.addWidget(QLabel("Столбец:"))
        self.inn_column = QSpinBox()
        self.inn_column.setRange(0, 100)
        self.inn_column.setValue(22)
        self.inn_column.setFixedWidth(80)
        row1.addWidget(self.inn_column)
        g1_layout.addLayout(row1)
        
        # КПП
        row2 = QHBoxLayout()
        self.kpp_checkbox = QCheckBox("КПП организации")
        self.kpp_checkbox.setChecked(True)
        row2.addWidget(self.kpp_checkbox)
        row2.addStretch()
        row2.addWidget(QLabel("Столбец:"))
        self.kpp_column = QSpinBox()
        self.kpp_column.setRange(0, 100)
        self.kpp_column.setValue(21)
        self.kpp_column.setFixedWidth(80)
        row2.addWidget(self.kpp_column)
        g1_layout.addLayout(row2)
        
        # Поставщик
        row3 = QHBoxLayout()
        self.supplier_checkbox = QCheckBox("Наименование поставщика")
        self.supplier_checkbox.setChecked(True)
        row3.addWidget(self.supplier_checkbox)
        row3.addStretch()
        row3.addWidget(QLabel("Столбец:"))
        self.supplier_column = QSpinBox()
        self.supplier_column.setRange(0, 100)
        self.supplier_column.setValue(19)
        self.supplier_column.setFixedWidth(80)
        row3.addWidget(self.supplier_column)
        g1_layout.addLayout(row3)
        
        # Гиперссылка
        row4 = QHBoxLayout()
        self.hyperlink_checkbox = QCheckBox("Гиперссылка")
        row4.addWidget(self.hyperlink_checkbox)
        row4.addStretch()
        row4.addWidget(QLabel("Столбец:"))
        self.hyperlink_column = QSpinBox()
        self.hyperlink_column.setRange(0, 100)
        self.hyperlink_column.setValue(23)
        self.hyperlink_column.setFixedWidth(80)
        row4.addWidget(self.hyperlink_column)
        g1_layout.addLayout(row4)

        layout.addWidget(group1)
        
        # Фиксированные тексты
        group2 = QGroupBox("Фиксированные тексты")
        g2_layout = QVBoxLayout(group2)
        
        # Текст 1
        t1_layout = QHBoxLayout()
        self.text1_checkbox = QCheckBox()
        self.text1_checkbox.setChecked(True)
        self.text1_checkbox.setFixedWidth(24)
        t1_layout.addWidget(self.text1_checkbox)
        self.text1_edit = QLineEdit("Цена с НДС с учетом доставки")
        t1_layout.addWidget(self.text1_edit)
        g2_layout.addLayout(t1_layout)
        
        # Текст 2
        t2_layout = QHBoxLayout()
        self.text2_checkbox = QCheckBox()
        self.text2_checkbox.setChecked(True)
        self.text2_checkbox.setFixedWidth(24)
        t2_layout.addWidget(self.text2_checkbox)
        self.text2_edit = QLineEdit("КП от 13.11.2024")
        t2_layout.addWidget(self.text2_edit)
        g2_layout.addLayout(t2_layout)
        
        # Текст 3
        t3_layout = QHBoxLayout()
        self.text3_checkbox = QCheckBox()
        self.text3_checkbox.setChecked(True)
        self.text3_checkbox.setFixedWidth(24)
        t3_layout.addWidget(self.text3_checkbox)
        self.text3_edit = QLineEdit("Адрес склада: г. СПб")
        t3_layout.addWidget(self.text3_edit)
        g2_layout.addLayout(t3_layout)
        
        # Печать
        self.stamp_checkbox = QCheckBox("Добавить печать/подпись на изображение")
        self.stamp_checkbox.setChecked(True)
        g2_layout.addWidget(self.stamp_checkbox)
        
        layout.addWidget(group2)
        
        layout.addStretch()
        return widget
    
    def _create_output_tab(self) -> QWidget:
        """Вкладка настроек вывода."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        widget = QWidget()
        widget.setObjectName("tabContainer") # Для стилизации
        # Стиль будет установлен через qss
        
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Формат вывода
        group1 = QGroupBox("Формат сохранения")
        g1_layout = QHBoxLayout(group1)
        g1_layout.setContentsMargins(16, 16, 16, 16)
        
        self.format_group = QButtonGroup(self)
        self.format_png = QRadioButton("PNG")
        self.format_jpg = QRadioButton("JPG")
        self.format_pdf = QRadioButton("PDF")
        self.format_pdf.setChecked(True)
        self.format_group.addButton(self.format_png)
        self.format_group.addButton(self.format_jpg)
        self.format_group.addButton(self.format_pdf)
        g1_layout.addWidget(self.format_png)
        g1_layout.addWidget(self.format_jpg)
        g1_layout.addWidget(self.format_pdf)
        g1_layout.addStretch()
        
        layout.addWidget(group1)
        
        # Расположение
        group2 = QGroupBox("Расположение панели данных")
        g2_layout = QHBoxLayout(group2)
        g2_layout.setContentsMargins(16, 16, 16, 16)
        
        self.position_group = QButtonGroup(self)
        self.position_left = QRadioButton("Слева от изображения")
        self.position_left.setChecked(True)
        self.position_bottom = QRadioButton("Снизу изображения")
        self.position_group.addButton(self.position_left)
        self.position_group.addButton(self.position_bottom)
        g2_layout.addWidget(self.position_left)
        g2_layout.addWidget(self.position_bottom)
        g2_layout.addStretch()
        
        layout.addWidget(group2)
        
        # Параметры оформления
        group3 = QGroupBox("Параметры оформления")
        g3_layout = QGridLayout(group3)
        g3_layout.setContentsMargins(20, 20, 20, 20)
        g3_layout.setVerticalSpacing(15)
        g3_layout.setHorizontalSpacing(20)
        g3_layout.setColumnStretch(2, 1)  # Растягиваем последнюю колонку

        # Ширина панели
        g3_layout.addWidget(QLabel("Ширина панели:"), 0, 0)
        self.panel_width = QSpinBox()
        self.panel_width.setRange(100, 800)
        self.panel_width.setValue(300)
        self.panel_width.setSuffix(" px")
        self.panel_width.setFixedWidth(80)
        g3_layout.addWidget(self.panel_width, 0, 1)

        # Цвет фона
        g3_layout.addWidget(QLabel("Цвет фона:"), 1, 0)
        self.bg_color_btn = QPushButton("Выбрать")
        self.bg_color_btn.setStyleSheet(f"background-color: {self._bg_color}; border: 1px solid #ced4da; border-radius: 4px;")
        self.bg_color_btn.setFixedWidth(100)
        self.bg_color_btn.clicked.connect(self._choose_bg_color)
        g3_layout.addWidget(self.bg_color_btn, 1, 1)

        # Размер шрифта
        g3_layout.addWidget(QLabel("Размер шрифта:"), 2, 0)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 36)
        self.font_size.setValue(12)
        self.font_size.setSuffix(" pt")
        self.font_size.setFixedWidth(80)
        g3_layout.addWidget(self.font_size, 2, 1)
        
        layout.addWidget(group3)
        
        # Производительность
        group4 = QGroupBox("Производительность")
        g4_layout = QGridLayout(group4)
        g4_layout.setContentsMargins(20, 20, 20, 20)
        g4_layout.setVerticalSpacing(15)
        g4_layout.setHorizontalSpacing(20)
        g4_layout.setColumnStretch(3, 1)

        # Потоки
        g4_layout.addWidget(QLabel("Количество потоков:"), 0, 0)
        self.thread_count = QSpinBox()
        self.thread_count.setRange(0, 16)
        self.thread_count.setValue(0)
        self.thread_count.setSpecialValueText("Авто")
        self.thread_count.setFixedWidth(80)
        g4_layout.addWidget(self.thread_count, 0, 1)
        g4_layout.addWidget(QLabel("(0 = авто)"), 0, 2)

        # Размер пакета
        g4_layout.addWidget(QLabel("Размер пакета обработки:"), 1, 0)
        self.batch_size = QSpinBox()
        self.batch_size.setRange(10, 500)
        self.batch_size.setValue(50)
        self.batch_size.setFixedWidth(80)
        g4_layout.addWidget(self.batch_size, 1, 1)
        g4_layout.addWidget(QLabel("файлов"), 1, 2)

        # Автосохранение
        self.auto_save_checkbox = QCheckBox("Автосохранение каждые:")
        self.auto_save_checkbox.setChecked(True)
        g4_layout.addWidget(self.auto_save_checkbox, 2, 0)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(50, 500)
        self.auto_save_interval.setValue(100)
        self.auto_save_interval.setFixedWidth(80)
        g4_layout.addWidget(self.auto_save_interval, 2, 1)
        g4_layout.addWidget(QLabel("файлов"), 2, 2)

        # Трей
        self.minimize_to_tray = QCheckBox("Сворачивать в трей при обработке")
        self.minimize_to_tray.setChecked(True)
        g4_layout.addWidget(self.minimize_to_tray, 3, 0, 1, 3)
        
        layout.addWidget(group4)
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_preview_tab(self) -> QWidget:
        """Вкладка предпросмотра."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Превью изображения
        group1 = QGroupBox("Предпросмотр результата")
        g1_layout = QVBoxLayout(group1)

        # Интерактивный виджет (по умолчанию)
        self.interactive_preview = InteractivePreviewWidget()
        self.interactive_preview.offsetsChanged.connect(self._on_offsets_changed)
        
        # Добавляем кнопку обновления прямо в панель управления виджета
        self.preview_btn = QPushButton("Обновить предпросмотр")
        self.preview_btn.clicked.connect(self._update_preview)
        self.interactive_preview.addRightWidget(self.preview_btn)
        
        g1_layout.addWidget(self.interactive_preview)

        layout.addWidget(group1, 3)  # Даем больший вес для растягивания

        # Журнал
        group2 = QGroupBox("Журнал обработки")
        g2_layout = QVBoxLayout(group2)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        # Убираем максимальную высоту, устанавливаем политику размера
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        g2_layout.addWidget(self.log_text)

        layout.addWidget(group2, 1)  # Меньший вес, чем у превью
        
        return widget
    
    def _create_status_panel(self) -> QWidget:
        """Панель статуса."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Статистика
        stats_layout = QHBoxLayout()
        self.files_found_label = QLabel("Найдено: 0")
        self.files_processed_label = QLabel("Обработано: 0")
        self.files_errors_label = QLabel("Ошибок: 0")
        self.speed_label = QLabel("Скорость: -")
        self.time_remaining_label = QLabel("Осталось: -")
        
        stats_layout.addWidget(self.files_found_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.files_processed_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.files_errors_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.time_remaining_label)
        layout.addLayout(stats_layout)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(28)
        layout.addWidget(self.progress_bar)
        
        return widget
    
    def _create_buttons_panel(self) -> QWidget:
        """Панель кнопок."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_btn_main = QPushButton("Предпросмотр")
        self.preview_btn_main.clicked.connect(self._update_preview)
        layout.addWidget(self.preview_btn_main)
        
        layout.addStretch()
        
        self.pause_btn = QPushButton("Пауза")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_processing)
        layout.addWidget(self.cancel_btn)
        
        self.start_btn = QPushButton("ЗАПУСТИТЬ ОБРАБОТКУ")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self._start_processing)
        layout.addWidget(self.start_btn)
        
        return widget
    
    def _setup_tray(self):
        """Настройка системного трея."""
        self.tray_icon = QSystemTrayIcon(self)
        
        tray_menu = QMenu()
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        pause_action = QAction("Пауза/Продолжить", self)
        pause_action.triggered.connect(self._toggle_pause)
        tray_menu.addAction(pause_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#228be6"))
        self.tray_icon.setIcon(QIcon(pixmap))
    
    def _connect_signals(self):
        """Подключение сигналов."""
        self.source_folder_edit.textChanged.connect(self._on_source_changed)
        self.excel_file_edit.textChanged.connect(self._on_excel_changed)
    
    def _load_settings(self):
        """Загрузка настроек в UI."""
        try:
            s = self.settings

            # Тема (загружаем только если виджет существует)
            if hasattr(self, 'theme_switch') and hasattr(self, '_apply_theme'):
                self._is_dark_mode = s.get("ui", "dark_mode", default=False)
                self.theme_switch.setChecked(self._is_dark_mode)
                self._apply_theme()
            else:
                self._is_dark_mode = False

            self.source_folder_edit.setText(s.get("paths", "source_folder", default=""))
            self.output_folder_edit.setText(s.get("paths", "output_folder", default=""))
            self.excel_file_edit.setText(s.get("paths", "excel_file", default=""))
            self.stamp_file_edit.setText(s.get("paths", "stamp_file", default=""))

            self.inn_checkbox.setChecked(s.get("excel_fields", "inn", "enabled", default=True))
            self.inn_column.setValue(s.get("excel_fields", "inn", "column", default=22))
            self.kpp_checkbox.setChecked(s.get("excel_fields", "kpp", "enabled", default=True))
            self.kpp_column.setValue(s.get("excel_fields", "kpp", "column", default=21))
            self.supplier_checkbox.setChecked(s.get("excel_fields", "supplier", "enabled", default=True))
            self.supplier_column.setValue(s.get("excel_fields", "supplier", "column", default=19))
            self.hyperlink_checkbox.setChecked(s.get("excel_fields", "hyperlink", "enabled", default=False))
            self.hyperlink_column.setValue(s.get("excel_fields", "hyperlink", "column", default=23))

            self.text1_checkbox.setChecked(s.get("fixed_texts", "text1", "enabled", default=True))
            self.text1_edit.setText(s.get("fixed_texts", "text1", "value", default="Цена с НДС с учетом доставки"))
            self.text2_checkbox.setChecked(s.get("fixed_texts", "text2", "enabled", default=True))
            self.text2_edit.setText(s.get("fixed_texts", "text2", "value", default="КП от 13.11.2024"))
            self.text3_checkbox.setChecked(s.get("fixed_texts", "text3", "enabled", default=True))
            self.text3_edit.setText(s.get("fixed_texts", "text3", "value", default="Адрес склада: г. СПб"))
            self.stamp_checkbox.setChecked(s.get("fixed_texts", "stamp_enabled", default=True))

            output_format = s.get("output", "format", default="pdf")
            if output_format == "png":
                self.format_png.setChecked(True)
            elif output_format == "jpg":
                self.format_jpg.setChecked(True)
            else:
                self.format_pdf.setChecked(True)

            if s.get("output", "position", default="left") == "left":
                self.position_left.setChecked(True)
            else:
                self.position_bottom.setChecked(True)

            self.panel_width.setValue(s.get("output", "panel_width", default=300))
            self._bg_color = s.get("output", "background_color", default="#FFFFFF")
            self.bg_color_btn.setStyleSheet(f"background-color: {self._bg_color}; border: 1px solid #ced4da; border-radius: 4px;")
            self.font_size.setValue(s.get("output", "font_size", default=12))

            self.thread_count.setValue(s.get("performance", "thread_count", default=0))
            self.batch_size.setValue(s.get("performance", "batch_size", default=50))
            self.auto_save_checkbox.setChecked(s.get("performance", "auto_save", default=True))
            self.auto_save_interval.setValue(s.get("performance", "auto_save_interval", default=100))
            self.minimize_to_tray.setChecked(s.get("performance", "minimize_to_tray", default=True))

            # Загружаем список сохранённых печатей
            self._refresh_stamps_list()

            print("DEBUG: Настройки загружены успешно")
        except Exception as e:
            print(f"DEBUG: Ошибка при загрузке настроек: {e}")
            import traceback
            traceback.print_exc()

    def _save_settings(self):
        """Сохранение настроек из UI."""
        try:
            s = self.settings

            # Сохраняем тему только если виджет существует
            if hasattr(self, 'theme_switch'):
                s.set("ui", "dark_mode", self.theme_switch.isChecked())

            s.set("paths", "source_folder", self.source_folder_edit.text())
            s.set("paths", "output_folder", self.output_folder_edit.text())
            s.set("paths", "excel_file", self.excel_file_edit.text())
            s.set("paths", "stamp_file", self.stamp_file_edit.text())

            s.set("excel_fields", "inn", "enabled", self.inn_checkbox.isChecked())
            s.set("excel_fields", "inn", "column", self.inn_column.value())
            s.set("excel_fields", "kpp", "enabled", self.kpp_checkbox.isChecked())
            s.set("excel_fields", "kpp", "column", self.kpp_column.value())
            s.set("excel_fields", "supplier", "enabled", self.supplier_checkbox.isChecked())
            s.set("excel_fields", "supplier", "column", self.supplier_column.value())
            s.set("excel_fields", "hyperlink", "enabled", self.hyperlink_checkbox.isChecked())
            s.set("excel_fields", "hyperlink", "column", self.hyperlink_column.value())

            s.set("fixed_texts", "text1", "enabled", self.text1_checkbox.isChecked())
            s.set("fixed_texts", "text1", "value", self.text1_edit.text())
            s.set("fixed_texts", "text2", "enabled", self.text2_checkbox.isChecked())
            s.set("fixed_texts", "text2", "value", self.text2_edit.text())
            s.set("fixed_texts", "text3", "enabled", self.text3_checkbox.isChecked())
            s.set("fixed_texts", "text3", "value", self.text3_edit.text())
            s.set("fixed_texts", "stamp_enabled", self.stamp_checkbox.isChecked())

            if self.format_png.isChecked():
                s.set("output", "format", "png")
            elif self.format_jpg.isChecked():
                s.set("output", "format", "jpg")
            else:
                s.set("output", "format", "pdf")

            s.set("output", "position", "left" if self.position_left.isChecked() else "bottom")
            s.set("output", "panel_width", self.panel_width.value())
            s.set("output", "background_color", self._bg_color)
            s.set("output", "font_size", self.font_size.value())

            s.set("performance", "thread_count", self.thread_count.value())
            s.set("performance", "batch_size", self.batch_size.value())
            s.set("performance", "auto_save", self.auto_save_checkbox.isChecked())
            s.set("performance", "auto_save_interval", self.auto_save_interval.value())
            s.set("performance", "minimize_to_tray", self.minimize_to_tray.isChecked())

            s.save()
            print("DEBUG: Настройки сохранены успешно")
        except Exception as e:
            print(f"DEBUG: Ошибка при сохранении настроек: {e}")
            import traceback
            traceback.print_exc()
    
    def _browse_folder(self, line_edit: QLineEdit):
        """Выбор папки."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            line_edit.setText(folder)
    
    def _browse_excel(self):
        """Выбор Excel файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Excel файл", "", "Excel файлы (*.xlsx *.xls)"
        )
        if file_path:
            self.excel_file_edit.setText(file_path)
    
    def _browse_stamp(self):
        """Выбор файла печати."""
        # Открываем папку stamps по умолчанию, если она существует
        stamps_dir = Path("stamps")
        start_dir = str(stamps_dir) if stamps_dir.exists() else ""

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение печати", start_dir, "Изображения (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.stamp_file_edit.setText(file_path)

    def _refresh_stamps_list(self):
        """Обновление списка сохранённых печатей."""
        self.stamps_combo.clear()
        self.stamps_combo.addItem("-- Выберите печать --", "")

        stamps_dir = Path("stamps")
        if not stamps_dir.exists():
            return

        # Получаем список PNG файлов, сортируем по дате изменения (новые первыми)
        stamp_files = sorted(
            stamps_dir.glob("*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for stamp_file in stamp_files:
            # Отображаем только имя файла, храним полный путь
            self.stamps_combo.addItem(stamp_file.name, str(stamp_file.absolute()))

    def _on_stamp_selected(self, index: int):
        """Обработчик выбора печати из списка."""
        if index > 0:  # Пропускаем "-- Выберите печать --"
            stamp_path = self.stamps_combo.currentData()
            if stamp_path:
                self.stamp_file_edit.setText(stamp_path)

    def _delete_stamp(self):
        """Удаление выбранной печати."""
        current_index = self.stamps_combo.currentIndex()
        if current_index <= 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите печать для удаления")
            return

        stamp_path = self.stamps_combo.currentData()
        stamp_name = self.stamps_combo.currentText()

        if not stamp_path or not Path(stamp_path).exists():
            QMessageBox.warning(self, "Предупреждение", "Файл печати не найден")
            return

        # Подтверждение удаления
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы действительно хотите удалить печать:\n{stamp_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем файл
                Path(stamp_path).unlink()

                # Очищаем поле пути, если там был путь к удаленной печати
                if self.stamp_file_edit.text() == stamp_path:
                    self.stamp_file_edit.clear()

                # Обновляем список
                self._refresh_stamps_list()

                QMessageBox.information(self, "Успех", f"Печать '{stamp_name}' удалена")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить печать:\n{str(e)}")

    def _choose_bg_color(self):
        """Выбор цвета фона."""
        color = QColorDialog.getColor(QColor(self._bg_color), self, "Выберите цвет фона")
        if color.isValid():
            self._bg_color = color.name()
            self.bg_color_btn.setStyleSheet(
                f"background-color: {self._bg_color}; border: 1px solid #ced4da; border-radius: 4px;"
            )
    
    def _on_source_changed(self, path: str):
        """Обработчик изменения папки источника."""
        print(f"DEBUG: _on_source_changed вызван с путём: '{path}'")
        if path and Path(path).exists():
            print(f"DEBUG: Папка существует, сканируем файлы...")
            self._image_files = get_image_files(path)
            count = len(self._image_files)
            print(f"DEBUG: Найдено {count} файлов: {self._image_files[:3]}")
            self.source_info.setText(f"Найдено {count} изображений")
            self.files_found_label.setText(f"Найдено: {count}")
            self._log(f"Найдено {count} изображений")
        else:
            print(f"DEBUG: Папка не существует или путь пустой")
            self._image_files = []
            self.source_info.setText("Папка не найдена")
            self.files_found_label.setText("Найдено: 0")
    
    def _on_excel_changed(self, path: str):
        """Обработчик изменения Excel файла."""
        print(f"DEBUG: _on_excel_changed вызван с путём: '{path}'")
        if path and Path(path).exists():
            print(f"DEBUG: Excel файл существует, загружаем...")
            try:
                self.excel_reader = ExcelReader(path)
                success, msg = self.excel_reader.load()
                if success:
                    columns = {
                        "position": 0,
                        "supplier": self.supplier_column.value(),
                        "kpp": self.kpp_column.value(),
                        "inn": self.inn_column.value(),
                        "hyperlink": self.hyperlink_column.value()
                    }
                    success, msg = self.excel_reader.parse(columns)
                    if success:
                        count = self.excel_reader.get_record_count()
                        print(f"DEBUG: Загружено {count} записей из Excel")
                        self.excel_info.setText(f"Загружено {count} записей")
                        self._log(f"Excel: загружено {count} записей")
                    else:
                        print(f"DEBUG: Ошибка парсинга Excel: {msg}")
                        self.excel_info.setText(f"Ошибка: {msg}")
                else:
                    print(f"DEBUG: Ошибка загрузки Excel: {msg}")
                    self.excel_info.setText(f"Ошибка: {msg}")
            except Exception as e:
                print(f"DEBUG: Исключение при загрузке Excel: {e}")
                import traceback
                traceback.print_exc()
                self.excel_info.setText(f"Ошибка: {e}")
        else:
            print(f"DEBUG: Excel файл не существует или путь пустой")
            self.excel_info.setText("Файл не найден")
    
    def _get_processor_settings(self) -> Dict:
        """Получение настроек для процессора."""
        return {
            "panel_width": self.panel_width.value(),
            "position": "left" if self.position_left.isChecked() else "bottom",
            "background_color": self._bg_color,
            "font_size": self.font_size.value(),
            "text_color": "#000000",
            "format": "png" if self.format_png.isChecked() else ("jpg" if self.format_jpg.isChecked() else "pdf"),
            "stamp_enabled": self.stamp_checkbox.isChecked(),
            "stamp_scale": 1.5,  # Увеличенный размер печати (150%) для лучшей видимости
            "excel_fields": {
                "inn": {"enabled": self.inn_checkbox.isChecked()},
                "kpp": {"enabled": self.kpp_checkbox.isChecked()},
                "supplier": {"enabled": self.supplier_checkbox.isChecked()},
                "hyperlink": {"enabled": self.hyperlink_checkbox.isChecked()}
            }
        }
    
    def _get_fixed_texts(self) -> List[str]:
        """Получение списка фиксированных текстов."""
        texts = []
        if self.text1_checkbox.isChecked():
            text1 = self.text1_edit.text()
            print(f"DEBUG: text1 checked={self.text1_checkbox.isChecked()}, value='{text1}'")
            texts.append(text1)
        if self.text2_checkbox.isChecked():
            text2 = self.text2_edit.text()
            print(f"DEBUG: text2 checked={self.text2_checkbox.isChecked()}, value='{text2}'")
            texts.append(text2)
        if self.text3_checkbox.isChecked():
            text3 = self.text3_edit.text()
            print(f"DEBUG: text3 checked={self.text3_checkbox.isChecked()}, value='{text3}'")
            texts.append(text3)
        print(f"DEBUG: _get_fixed_texts() returning: {texts}")
        return texts

    def _on_offsets_changed(self, offsets: Dict):
        """Обработка изменения смещений элементов."""
        # Автоматическое сохранение смещений
        self._save_offsets()

    def _save_offsets(self):
        """Сохранение смещений в настройки."""
        offsets = self.interactive_preview.getOffsets()
        # Конвертируем в формат для сохранения
        offsets_for_save = {name: list(offset) for name, offset in offsets.items()}
        self.settings.set("element_offsets", offsets_for_save)
        self.settings.save()
        self._log(f"Сохранены смещения: {len(offsets)} элементов")

    def _update_preview(self):
        """Обновление предпросмотра (интерактивный режим)."""
        if not self._image_files:
            self._log("Нет файлов для предпросмотра")
            return

        if not self.excel_reader or self.excel_reader.get_record_count() == 0:
            self._log("Нет данных из Excel")
            return

        # Находим тестовый файл
        sample_file = None
        sample_data = None

        for img_path in self._image_files:
            data = self.excel_reader.get_data_for_file(img_path)
            if data:
                sample_file = img_path
                sample_data = data
                break

        if not sample_file:
            self._log("Нет совпадений между файлами и данными Excel")
            return

        settings = self._get_processor_settings()
        processor = ImageProcessor(settings)

        stamp_path = self.stamp_file_edit.text()
        if stamp_path and self.stamp_checkbox.isChecked():
            success, msg = processor.load_stamp(stamp_path)
            if not success:
                self._log(f"Предпросмотр: Ошибка загрузки печати - {msg}")

        # Генерируем превью с позициями элементов
        result = processor.generate_preview_with_positions(
            sample_file, sample_data, self._get_fixed_texts()
        )

        if result:
            background_image, element_positions = result

            # Конвертируем в QPixmap
            preview_rgb = background_image.convert('RGB')
            data = preview_rgb.tobytes("raw", "RGB")
            qimage = QImage(data, preview_rgb.width, preview_rgb.height,
                          preview_rgb.width * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)

            # Очищаем старые элементы
            self.interactive_preview.preview_view.clearDraggableItems()

            # Устанавливаем фон
            self.interactive_preview.preview_view.setBackgroundPixmap(pixmap)

            # Добавляем перетаскиваемые элементы
            text_color = QColor(settings.get("text_color", "#000000"))

            for name, position_info in element_positions.items():
                x, y, text_content, font_size = position_info

                if text_content is not None:
                    # Текстовый элемент
                    font = QFont(settings.get("font_family", "Arial"), font_size or 12)
                    self.interactive_preview.preview_view.addDraggableText(
                        text_content, name, x, y, font, text_color
                    )
                else:
                    # Печать
                    if processor.stamp_image:
                        # Применяем масштабирование к печати
                        from PIL import Image
                        stamp_scale = settings.get("stamp_scale", 1.0)
                        panel_width = settings.get("panel_width", 300)

                        # СНАЧАЛА применяем масштаб к оригинальному размеру
                        stamp_width = int(processor.stamp_image.width * stamp_scale)
                        stamp_height = int(processor.stamp_image.height * stamp_scale)

                        # ЗАТЕМ ограничиваем шириной панели, если нужно
                        if stamp_width > panel_width - 20:
                            ratio = (panel_width - 20) / stamp_width
                            stamp_width = panel_width - 20
                            stamp_height = int(stamp_height * ratio)

                        # Масштабируем изображение печати
                        stamp_resized = processor.stamp_image.resize(
                            (stamp_width, stamp_height), Image.Resampling.LANCZOS
                        )

                        # Сохраняем прозрачность (RGBA)
                        if stamp_resized.mode != 'RGBA':
                            stamp_resized = stamp_resized.convert('RGBA')

                        stamp_data = stamp_resized.tobytes("raw", "RGBA")
                        stamp_qimage = QImage(
                            stamp_data, stamp_resized.width, stamp_resized.height,
                            stamp_resized.width * 4, QImage.Format.Format_RGBA8888
                        )
                        stamp_pixmap = QPixmap.fromImage(stamp_qimage)
                        self.interactive_preview.preview_view.addDraggablePixmap(
                            stamp_pixmap, name, x, y
                        )

            self._log(f"Интерактивное превью: {Path(sample_file).name}")
        else:
            self._log("Ошибка генерации интерактивного превью")

    def _validate_inputs(self) -> Tuple[bool, str]:
        """Валидация входных данных."""
        if not self.source_folder_edit.text():
            return False, "Не указана папка с исходными изображениями"
        if not Path(self.source_folder_edit.text()).exists():
            return False, "Папка с исходными изображениями не существует"
        if not self.output_folder_edit.text():
            return False, "Не указана папка для результатов"
        if not self.excel_file_edit.text():
            return False, "Не указан файл Excel"
        if not Path(self.excel_file_edit.text()).exists():
            return False, "Файл Excel не существует"
        if not self._image_files:
            return False, "В папке нет изображений для обработки"
        return True, "OK"
    
    def _start_processing(self):
        """Запуск обработки."""
        valid, msg = self._validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Ошибка", msg)
            return
        
        self._save_settings()
        
        self.excel_reader = ExcelReader(self.excel_file_edit.text())
        success, msg = self.excel_reader.load()
        if not success:
            QMessageBox.critical(self, "Ошибка Excel", msg)
            return
        
        columns = {
            "position": 0,
            "supplier": self.supplier_column.value(),
            "kpp": self.kpp_column.value(),
            "inn": self.inn_column.value(),
            "hyperlink": self.hyperlink_column.value()
        }
        success, msg = self.excel_reader.parse(columns)
        if not success:
            QMessageBox.critical(self, "Ошибка Excel", msg)
            return
        
        self._log(f"Начало обработки: {len(self._image_files)} файлов")
        
        output_folder = Path(self.output_folder_edit.text())
        output_folder.mkdir(parents=True, exist_ok=True)
        
        if self.format_png.isChecked():
            output_ext = ".png"
        elif self.format_jpg.isChecked():
            output_ext = ".jpg"
        else:
            output_ext = ".pdf"
        
        tasks = []
        fixed_texts = self._get_fixed_texts()
        
        for img_path in self._image_files:
            excel_data = self.excel_reader.get_data_for_file(img_path)
            if not excel_data:
                self._log(f"SKIP: Нет данных для {Path(img_path).name}")
                continue
            
            output_path = output_folder / (Path(img_path).stem + output_ext)
            tasks.append(ProcessingTask(
                image_path=img_path,
                output_path=str(output_path),
                excel_data=excel_data,
                fixed_texts=fixed_texts
            ))
        
        if not tasks:
            QMessageBox.warning(self, "Внимание", "Нет файлов для обработки (нет совпадений с Excel)")
            return
        
        settings = self._get_processor_settings()
        settings["paths"] = {"stamp_file": self.stamp_file_edit.text()}
        settings["performance"] = {
            "thread_count": self.thread_count.value(),
            "batch_size": self.batch_size.value(),
            "auto_save_interval": self.auto_save_interval.value()
        }
        
        def processor_factory():
            return ImageProcessor(settings)
        
        self.current_worker = ProcessingWorker(
            tasks=tasks,
            processor_factory=processor_factory,
            settings=settings
        )
        
        self.current_worker.signals.started.connect(self._on_processing_started)
        self.current_worker.signals.finished.connect(self._on_processing_finished)
        self.current_worker.signals.progress.connect(self._on_progress)
        self.current_worker.signals.file_processed.connect(self._on_file_processed)
        self.current_worker.signals.statistics.connect(self._on_statistics)
        self.current_worker.signals.error.connect(self._on_error)
        
        self.progress_bar.setMaximum(len(tasks))
        self.progress_bar.setValue(0)
        
        self.thread_pool.start(self.current_worker)
    
    @pyqtSlot()
    def _on_processing_started(self):
        """Обработчик начала обработки."""
        self._is_processing = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.status_bar.showMessage("Обработка...")
        
        if self.minimize_to_tray.isChecked():
            self.tray_icon.show()
    
    @pyqtSlot()
    def _on_processing_finished(self):
        """Обработчик завершения обработки."""
        self._is_processing = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setText("Пауза")
        
        self._log("Обработка завершена!")
        self.status_bar.showMessage("Обработка завершена")
        
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Image Data Annotator",
                "Обработка завершена!",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        
        self.show()
        self.activateWindow()
    
    @pyqtSlot(int, int, str)
    def _on_progress(self, current: int, total: int, filename: str):
        """Обработчик прогресса."""
        self.progress_bar.setValue(current)
        self.files_processed_label.setText(f"Обработано: {current}")
    
    @pyqtSlot(str, bool, str)
    def _on_file_processed(self, filename: str, success: bool, message: str):
        """Обработчик обработки файла."""
        if success:
            self._log(f"OK: {filename}")
        else:
            self._log(f"FAIL: {filename}: {message}")
            errors = int(self.files_errors_label.text().split(": ")[1]) + 1
            self.files_errors_label.setText(f"Ошибок: {errors}")
    
    @pyqtSlot(dict)
    def _on_statistics(self, stats: Dict):
        """Обработчик статистики."""
        speed = stats.get("speed", 0)
        remaining = stats.get("remaining", 0)
        
        self.speed_label.setText(f"Скорость: {speed:.1f}/сек")
        self.time_remaining_label.setText(f"Осталось: ~{self._format_time(remaining)}")
    
    @pyqtSlot(str, str)
    def _on_error(self, filename: str, error: str):
        """Обработчик ошибки."""
        self._log(f"ERROR: {error}")
    
    def _toggle_pause(self):
        """Переключение паузы."""
        if not self.current_worker:
            return
        
        if self.current_worker.is_paused:
            self.current_worker.resume()
            self.pause_btn.setText("Пауза")
            self._log("Обработка продолжена")
        else:
            self.current_worker.pause()
            self.pause_btn.setText("Продолжить")
            self._log("Обработка приостановлена")
    
    def _cancel_processing(self):
        """Отмена обработки."""
        if not self.current_worker:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Отменить обработку?\nУже обработанные файлы будут сохранены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.current_worker.cancel()
            self._log("Обработка отменена")
    
    def _log(self, message: str):
        """Добавление сообщения в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _format_time(self, seconds: float) -> str:
        """Форматирование времени."""
        if seconds < 60:
            return f"{int(seconds)} сек"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}:{mins:02d}:00"
    
    def _tray_activated(self, reason):
        """Обработчик активации трея."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def _quit_app(self):
        """Выход из приложения."""
        if self._is_processing:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Обработка ещё идёт. Выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            if self.current_worker:
                self.current_worker.cancel()
        
        self._save_settings()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        if self._is_processing and self.minimize_to_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Image Data Annotator",
                "Приложение свёрнуто в трей. Обработка продолжается.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self._save_settings()
            event.accept()

    def resizeEvent(self, event):
        """Обработчик изменения размера окна."""
        super().resizeEvent(event)
        # Обновляем превью при изменении размера окна
        if hasattr(self, 'preview_label') and self.preview_label.pixmap() and not self.preview_label.pixmap().isNull():
            # Используем таймер для debounce - обновляем только после завершения ресайза
            if hasattr(self, '_resize_timer'):
                self._resize_timer.stop()
            else:
                self._resize_timer = QTimer()
                self._resize_timer.setSingleShot(True)
                self._resize_timer.timeout.connect(self._update_preview)
            self._resize_timer.start(300)  # Обновляем через 300мс после окончания ресайза

    def _toggle_theme(self, checked: bool):
        """Переключение темы оформления."""
        self._is_dark_mode = checked
        self._apply_theme()
        
        # Сохраняем настройку немедленно
        self.settings.set("ui", "dark_mode", self._is_dark_mode)
        self.settings.save()
    
    def _apply_theme(self):
        """Применение текущей темы."""
        if self._is_dark_mode:
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)
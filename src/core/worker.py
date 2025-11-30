"""Модуль многопоточной обработки."""
import gc
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Event, Lock
from typing import Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    """Сигналы для worker'ов."""
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # filename, error message
    progress = pyqtSignal(int, int, str)  # current, total, filename
    file_processed = pyqtSignal(str, bool, str)  # filename, success, message
    statistics = pyqtSignal(dict)  # stats dict


@dataclass
class ProcessingTask:
    """Задача на обработку."""
    image_path: str
    output_path: str
    excel_data: Dict
    fixed_texts: List[str]


@dataclass
class ProcessingResult:
    """Результат обработки."""
    filename: str
    success: bool
    message: str
    processing_time: float


class ProcessingWorker(QRunnable):
    """Worker для обработки изображений."""
    
    def __init__(
        self,
        tasks: List[ProcessingTask],
        processor_factory: Callable,
        settings: Dict,
        checkpoint_callback: Optional[Callable] = None
    ):
        super().__init__()
        self.tasks = tasks
        self.processor_factory = processor_factory
        self.settings = settings
        self.checkpoint_callback = checkpoint_callback
        
        self.signals = WorkerSignals()
        self._is_paused = Event()
        self._is_cancelled = Event()
        self._is_paused.set()  # Не на паузе по умолчанию
        
        self._processed_count = 0
        self._success_count = 0
        self._failed_count = 0
        self._skipped_count = 0
        self._lock = Lock()
        
        self._start_time = None
        self._total_files = len(tasks)
        
        # Параметры многопоточности
        self._thread_count = settings.get("performance", {}).get("thread_count", 0)
        if self._thread_count <= 0:
            self._thread_count = max(2, min(os.cpu_count() - 1, 16))
        
        self._batch_size = settings.get("performance", {}).get("batch_size", 50)
        self._auto_save_interval = settings.get("performance", {}).get("auto_save_interval", 100)
    
    @pyqtSlot()
    def run(self):
        """Основной метод обработки."""
        self._start_time = time.time()
        self.signals.started.emit()
        
        try:
            processor = self.processor_factory()
            
            # Загружаем печать если нужна
            stamp_path = self.settings.get("paths", {}).get("stamp_file", "")
            if stamp_path and self.settings.get("fixed_texts", {}).get("stamp_enabled", True):
                processor.load_stamp(stamp_path)
            
            # Обработка с использованием ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self._thread_count) as executor:
                futures: Dict[Future, ProcessingTask] = {}
                
                for i, task in enumerate(self.tasks):
                    # Проверка на отмену
                    if self._is_cancelled.is_set():
                        break
                    
                    # Ожидание если на паузе
                    self._is_paused.wait()
                    
                    # Отправляем задачу в пул
                    future = executor.submit(
                        self._process_single_file,
                        processor,
                        task
                    )
                    futures[future] = task
                
                # Получаем результаты
                for future in as_completed(futures):
                    if self._is_cancelled.is_set():
                        break
                    
                    self._is_paused.wait()
                    
                    task = futures[future]
                    try:
                        result = future.result(timeout=30)
                        self._handle_result(result)
                    except Exception as e:
                        self._handle_result(ProcessingResult(
                            filename=Path(task.image_path).name,
                            success=False,
                            message=str(e),
                            processing_time=0
                        ))
                    
                    # Автосохранение checkpoint
                    if (self._processed_count % self._auto_save_interval == 0 
                        and self.checkpoint_callback):
                        self.checkpoint_callback()
                    
                    # Сборка мусора каждые batch_size файлов
                    if self._processed_count % self._batch_size == 0:
                        gc.collect()
            
        except Exception as e:
            self.signals.error.emit("", f"Критическая ошибка: {str(e)}")
        finally:
            self._emit_final_statistics()
            self.signals.finished.emit()
    
    def _process_single_file(
        self,
        processor,
        task: ProcessingTask
    ) -> ProcessingResult:
        """Обработка одного файла."""
        start_time = time.time()
        filename = Path(task.image_path).name
        
        try:
            success, message = processor.process_image(
                task.image_path,
                task.excel_data,
                task.fixed_texts,
                task.output_path
            )
            
            processing_time = time.time() - start_time
            return ProcessingResult(filename, success, message, processing_time)
            
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(filename, False, str(e), processing_time)
    
    def _handle_result(self, result: ProcessingResult):
        """Обработка результата."""
        with self._lock:
            self._processed_count += 1
            
            if result.success:
                self._success_count += 1
            else:
                self._failed_count += 1
        
        # Эмитируем сигналы
        self.signals.file_processed.emit(
            result.filename,
            result.success,
            result.message
        )
        
        self.signals.progress.emit(
            self._processed_count,
            self._total_files,
            result.filename
        )
        
        # Периодически отправляем статистику
        if self._processed_count % 10 == 0:
            self._emit_statistics()
    
    def _emit_statistics(self):
        """Отправка статистики."""
        elapsed = time.time() - self._start_time
        speed = self._processed_count / elapsed if elapsed > 0 else 0
        remaining = (self._total_files - self._processed_count) / speed if speed > 0 else 0
        
        stats = {
            "processed": self._processed_count,
            "total": self._total_files,
            "success": self._success_count,
            "failed": self._failed_count,
            "skipped": self._skipped_count,
            "elapsed": elapsed,
            "speed": speed,
            "remaining": remaining,
            "percent": (self._processed_count / self._total_files * 100) if self._total_files > 0 else 0
        }
        
        self.signals.statistics.emit(stats)
    
    def _emit_final_statistics(self):
        """Отправка финальной статистики."""
        elapsed = time.time() - self._start_time
        speed = self._processed_count / elapsed if elapsed > 0 else 0
        
        stats = {
            "processed": self._processed_count,
            "total": self._total_files,
            "success": self._success_count,
            "failed": self._failed_count,
            "skipped": self._skipped_count,
            "elapsed": elapsed,
            "speed": speed,
            "remaining": 0,
            "percent": 100 if self._processed_count == self._total_files else (self._processed_count / self._total_files * 100)
        }
        
        self.signals.statistics.emit(stats)
    
    def pause(self):
        """Приостановка обработки."""
        self._is_paused.clear()
    
    def resume(self):
        """Возобновление обработки."""
        self._is_paused.set()
    
    def cancel(self):
        """Отмена обработки."""
        self._is_cancelled.set()
        self._is_paused.set()  # Снимаем паузу чтобы завершиться
    
    @property
    def is_paused(self) -> bool:
        """Проверка на паузу."""
        return not self._is_paused.is_set()
    
    @property
    def is_cancelled(self) -> bool:
        """Проверка на отмену."""
        return self._is_cancelled.is_set()
    
    def get_progress(self) -> Tuple[int, int]:
        """Получение текущего прогресса."""
        return self._processed_count, self._total_files

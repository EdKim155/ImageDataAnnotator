"""Модуль для управления checkpoint'ами обработки."""
import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class CheckpointManager:
    """Менеджер checkpoint'ов для возобновления обработки."""
    
    def __init__(self, output_folder: str):
        """Инициализация менеджера."""
        self.output_folder = Path(output_folder)
        self.checkpoint_file = self.output_folder / ".checkpoint.json"
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.data: Dict = {}
    
    def create_session(self, total_files: List[str], settings_hash: str) -> None:
        """Создание новой сессии обработки."""
        self.data = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "paused_at": None,
            "total_files": len(total_files),
            "all_files": total_files,
            "processed_files": [],
            "failed_files": [],
            "settings_hash": settings_hash
        }
        self._save()
    
    def load_session(self) -> Optional[Dict]:
        """Загрузка существующей сессии."""
        try:
            if self.checkpoint_file.exists():
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    return self.data
        except Exception as e:
            print(f"Ошибка загрузки checkpoint: {e}")
        return None
    
    def has_checkpoint(self) -> bool:
        """Проверка наличия checkpoint'а."""
        return self.checkpoint_file.exists()
    
    def get_pending_files(self) -> List[str]:
        """Получение списка необработанных файлов."""
        if not self.data:
            return []
        
        processed = set(self.data.get("processed_files", []))
        failed = set(f["file"] for f in self.data.get("failed_files", []))
        all_files = self.data.get("all_files", [])
        
        return [f for f in all_files if f not in processed and f not in failed]
    
    def mark_processed(self, filename: str) -> None:
        """Отметка файла как обработанного."""
        if "processed_files" not in self.data:
            self.data["processed_files"] = []
        self.data["processed_files"].append(filename)
    
    def mark_failed(self, filename: str, error: str) -> None:
        """Отметка файла как неудачного."""
        if "failed_files" not in self.data:
            self.data["failed_files"] = []
        self.data["failed_files"].append({
            "file": filename,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def save_progress(self) -> None:
        """Сохранение прогресса."""
        self.data["paused_at"] = datetime.now().isoformat()
        self._save()
    
    def _save(self) -> None:
        """Внутренний метод сохранения."""
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения checkpoint: {e}")
    
    def clear(self) -> None:
        """Удаление checkpoint'а."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
        except Exception as e:
            print(f"Ошибка удаления checkpoint: {e}")
        self.data = {}
    
    def get_statistics(self) -> Dict:
        """Получение статистики обработки."""
        return {
            "total": self.data.get("total_files", 0),
            "processed": len(self.data.get("processed_files", [])),
            "failed": len(self.data.get("failed_files", [])),
            "pending": len(self.get_pending_files())
        }
    
    @staticmethod
    def calculate_settings_hash(settings: Dict) -> str:
        """Расчёт хэша настроек."""
        settings_str = json.dumps(settings, sort_keys=True)
        return hashlib.md5(settings_str.encode()).hexdigest()[:12]

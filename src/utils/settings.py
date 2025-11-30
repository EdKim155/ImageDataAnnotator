"""Модуль для сохранения и загрузки настроек приложения."""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Settings:
    """Класс для управления настройками приложения."""
    
    DEFAULT_SETTINGS = {
        "paths": {
            "source_folder": "",
            "output_folder": "",
            "excel_file": "",
            "stamp_file": ""
        },
        "excel_fields": {
            "inn": {"enabled": True, "column": 22},
            "kpp": {"enabled": True, "column": 21},
            "supplier": {"enabled": True, "column": 19},
            "hyperlink": {"enabled": False, "column": 23}
        },
        "fixed_texts": {
            "text1": {"enabled": True, "value": "Цена с НДС с учетом доставки"},
            "text2": {"enabled": True, "value": "КП от 13.11.2024"},
            "text3": {"enabled": True, "value": "Адрес склада: г. СПб"},
            "stamp_enabled": True
        },
        "output": {
            "format": "pdf",
            "position": "left",
            "panel_width": 300,
            "background_color": "#FFFFFF",
            "font_family": "Arial",
            "font_size": 12,
            "text_color": "#000000"
        },
        "performance": {
            "thread_count": 0,  # 0 = auto (CPU - 1)
            "batch_size": 50,
            "auto_save": True,
            "auto_save_interval": 100,
            "minimize_to_tray": True
        },
        "ui": {
            "dark_theme": False,
            "sound_on_complete": True
        },
        "element_offsets": {
            # Смещения элементов от исходных позиций (dx, dy)
            # Применяются ко всем изображениям при обработке
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Инициализация настроек."""
        if config_path is None:
            app_data = os.getenv('APPDATA', os.path.expanduser('~'))
            config_dir = Path(app_data) / "ImageDataAnnotator"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = config_dir / "settings.json"
        else:
            self.config_path = Path(config_path)
        
        self.settings = self._deep_copy(self.DEFAULT_SETTINGS)
        self.load()
    
    def _deep_copy(self, obj: Any) -> Any:
        """Глубокое копирование объекта."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        return obj
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Глубокое слияние словарей."""
        result = self._deep_copy(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = self._deep_copy(value)
        return result
    
    def load(self) -> bool:
        """Загрузка настроек из файла."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings = self._deep_merge(self.DEFAULT_SETTINGS, loaded)
                return True
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
        return False
    
    def save(self) -> bool:
        """Сохранение настроек в файл."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """Получение значения по ключам."""
        result = self.settings
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result
    
    def set(self, *keys_and_value) -> None:
        """Установка значения по ключам."""
        if len(keys_and_value) < 2:
            return
        
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]
        
        current = self.settings
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def reset(self) -> None:
        """Сброс настроек к значениям по умолчанию."""
        self.settings = self._deep_copy(self.DEFAULT_SETTINGS)

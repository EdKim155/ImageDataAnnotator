"""Модуль для обработки изображений."""
import io
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import img2pdf
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class ImageProcessor:
    """Класс для обработки изображений и добавления данных."""
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg'}
    
    def __init__(self, settings: Dict):
        """Инициализация процессора."""
        self.settings = settings
        self.stamp_image: Optional[Image.Image] = None
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
    
    def load_stamp(self, stamp_path: str) -> Tuple[bool, str]:
        """Загрузка изображения печати."""
        try:
            if not stamp_path or not Path(stamp_path).exists():
                return False, "Файл печати не найден"
            
            self.stamp_image = Image.open(stamp_path)
            # Конвертируем в RGBA для поддержки прозрачности
            if self.stamp_image.mode != 'RGBA':
                self.stamp_image = self.stamp_image.convert('RGBA')
            return True, "OK"
        except Exception as e:
            return False, f"Ошибка загрузки печати: {str(e)}"
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Получение шрифта с кэшированием."""
        if size not in self._font_cache:
            font_family = self.settings.get("font_family", "Arial")

            # Список путей к шрифтам для разных ОС
            font_paths = [
                # Windows
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/Arial.ttf",
                # macOS
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                # Linux
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                # Относительные пути
                "arial.ttf",
                "Arial.ttf"
            ]

            # Пробуем загрузить шрифт из списка
            for font_path in font_paths:
                try:
                    self._font_cache[size] = ImageFont.truetype(font_path, size)
                    break
                except (OSError, IOError):
                    continue
            else:
                # Если ничего не сработало, используем дефолтный
                self._font_cache[size] = ImageFont.load_default()

        return self._font_cache[size]
    
    def process_image(
        self,
        image_path: str,
        excel_data: Dict,
        fixed_texts: List[str],
        output_path: str
    ) -> Tuple[bool, str]:
        """Обработка одного изображения."""
        try:
            print(f"DEBUG PROCESS: Начало обработки {image_path}")
            print(f"DEBUG PROCESS: Excel данные: {excel_data}")
            print(f"DEBUG PROCESS: Фиксированные тексты: {fixed_texts}")

            # Загрузка исходного изображения
            original = Image.open(image_path)
            if original.mode != 'RGBA':
                original = original.convert('RGBA')

            print(f"DEBUG PROCESS: Изображение загружено, размер: {original.size}")
            
            # Параметры из настроек
            panel_width = self.settings.get("panel_width", 300)
            position = self.settings.get("position", "left")
            bg_color = self.settings.get("background_color", "#FFFFFF")
            font_size = self.settings.get("font_size", 12)
            text_color = self.settings.get("text_color", "#000000")
            output_format = self.settings.get("format", "png").lower()

            # Предварительно загружаем шрифт для расчета высоты
            font = self._get_font(font_size)
            line_height = font_size + 8

            # Рассчитываем необходимую высоту для панели слева
            if position == "left":
                # Считаем количество строк контента
                required_height = 20  # Начальный отступ
                excel_fields = self.settings.get("excel_fields", {})

                # ИНН
                if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                    required_height += line_height

                # КПП
                if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                    required_height += line_height

                # Поставщик (может быть многострочным)
                if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                    supplier_text = f"Поставщик:\n{excel_data['supplier']}"
                    supplier_lines = self._wrap_text(supplier_text, font, panel_width - 20)
                    required_height += len(supplier_lines) * line_height

                # Гиперссылка
                if excel_fields.get("hyperlink", {}).get("enabled") and excel_data.get("hyperlink"):
                    link_lines = self._wrap_text(f"Ссылка: {excel_data['hyperlink']}", font, panel_width - 20)
                    required_height += len(link_lines) * line_height

                # Разделитель
                required_height += 25

                # Фиксированные тексты
                for text in fixed_texts:
                    if text:
                        lines = self._wrap_text(text, font, panel_width - 20)
                        required_height += len(lines) * line_height

                # Печать (если есть)
                if self.stamp_image and self.settings.get("stamp_enabled", True):
                    stamp_scale = self.settings.get("stamp_scale", 1.0)
                    # Применяем масштаб
                    stamp_width = int(self.stamp_image.width * stamp_scale)
                    stamp_height = int(self.stamp_image.height * stamp_scale)
                    # Ограничиваем шириной панели
                    if stamp_width > panel_width - 20:
                        ratio = (panel_width - 20) / stamp_width
                        stamp_height = int(stamp_height * ratio)
                    required_height += stamp_height + 40  # +40 для отступов

                # Используем максимум из высоты изображения и требуемой высоты
                new_height = max(original.height, required_height + 20)
                new_width = original.width + panel_width

                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (panel_width, 0))
                panel_area = (0, 0, panel_width, new_height)
            else:  # bottom
                # Динамический расчёт высоты панели снизу
                panel_height = 20  # Начальный отступ
                excel_fields = self.settings.get("excel_fields", {})

                # ИНН
                if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                    panel_height += line_height

                # КПП
                if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                    panel_height += line_height

                # Поставщик (может быть многострочным)
                if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                    supplier_text = f"Поставщик:\n{excel_data['supplier']}"
                    supplier_lines = self._wrap_text(supplier_text, font, original.width - 20)
                    panel_height += len(supplier_lines) * line_height

                # Гиперссылка
                if excel_fields.get("hyperlink", {}).get("enabled") and excel_data.get("hyperlink"):
                    link_lines = self._wrap_text(f"Ссылка: {excel_data['hyperlink']}", font, original.width - 20)
                    panel_height += len(link_lines) * line_height

                # Разделитель
                panel_height += 25

                # Фиксированные тексты
                for text in fixed_texts:
                    if text:
                        lines = self._wrap_text(text, font, original.width - 20)
                        panel_height += len(lines) * line_height

                # Печать (если есть)
                if self.stamp_image and self.settings.get("stamp_enabled", True):
                    stamp_scale = self.settings.get("stamp_scale", 1.0)
                    # Применяем масштаб
                    stamp_width = int(self.stamp_image.width * stamp_scale)
                    stamp_height = int(self.stamp_image.height * stamp_scale)
                    # Ограничиваем шириной
                    if stamp_width > original.width - 20:
                        ratio = (original.width - 20) / stamp_width
                        stamp_height = int(stamp_height * ratio)
                    panel_height += stamp_height + 40  # +40 для отступов

                # Добавляем минимальный отступ снизу
                panel_height += 20

                new_width = original.width
                new_height = original.height + panel_height
                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (0, 0))
                panel_area = (0, original.height, new_width, new_height)
            
            # Рисование данных на панели
            draw = ImageDraw.Draw(result)
            # font уже загружен выше

            # Позиция для текста (базовая)
            base_text_x = panel_area[0] + 10
            base_text_y = panel_area[1] + 10
            text_x = base_text_x
            text_y = base_text_y
            # line_height уже определен выше

            # Получаем смещения из настроек
            element_offsets = self.settings.get("element_offsets", {})

            # Добавляем данные из Excel
            excel_fields = self.settings.get("excel_fields", {})

            if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                # Применяем смещение для ИНН
                offset_x, offset_y = element_offsets.get("inn", (0, 0))
                draw.text((text_x + offset_x, text_y + offset_y), f"ИНН: {excel_data['inn']}", fill=text_color, font=font)
                text_y += line_height

            if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                # Применяем смещение для КПП
                offset_x, offset_y = element_offsets.get("kpp", (0, 0))
                draw.text((text_x + offset_x, text_y + offset_y), f"КПП: {excel_data['kpp']}", fill=text_color, font=font)
                text_y += line_height
            
            if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                # Переносим длинное название поставщика
                supplier_text = f"Поставщик:\n{excel_data['supplier']}"
                lines = self._wrap_text(supplier_text, font, panel_width - 20)
                for line in lines:
                    draw.text((text_x, text_y), line, fill=text_color, font=font)
                    text_y += line_height
            
            if excel_fields.get("hyperlink", {}).get("enabled") and excel_data.get("hyperlink"):
                link_lines = self._wrap_text(f"Ссылка: {excel_data['hyperlink']}", font, panel_width - 20)
                for line in link_lines:
                    draw.text((text_x, text_y), line, fill=text_color, font=font)
                    text_y += line_height

            # Добавляем разделитель
            text_y += 10
            draw.line([(text_x, text_y), (panel_width - 10, text_y)], fill=text_color, width=1)
            text_y += 15
            
            # Добавляем фиксированные тексты
            print(f"DEBUG: Фиксированные тексты для {Path(image_path).name}: {fixed_texts}")
            print(f"DEBUG: Текущая позиция text_y={text_y}, высота панели={panel_area[3]}")
            for i, text in enumerate(fixed_texts):
                if text:
                    print(f"DEBUG: Добавляем текст #{i+1}: '{text}' на позицию y={text_y}")
                    # Применяем смещение для фиксированного текста
                    offset_x, offset_y = element_offsets.get(f"text_{i+1}", (0, 0))
                    lines = self._wrap_text(text, font, panel_width - 20)
                    current_y = text_y
                    for line in lines:
                        if current_y + line_height > panel_area[3]:
                            print(f"WARNING: Текст выходит за границы панели! y={current_y}, граница={panel_area[3]}")
                        draw.text((text_x + offset_x, current_y + offset_y), line, fill=text_color, font=font)
                        current_y += line_height
                    text_y += len(lines) * line_height
                else:
                    print(f"DEBUG: Пустой текст пропущен")

            # Добавляем печать/подпись
            if self.stamp_image and self.settings.get("stamp_enabled", True):
                # Получаем масштаб печати из настроек (по умолчанию 1.0 = 100%)
                stamp_scale = self.settings.get("stamp_scale", 1.0)

                # Применяем масштаб к оригинальному размеру
                stamp_width = int(self.stamp_image.width * stamp_scale)
                stamp_height = int(self.stamp_image.height * stamp_scale)

                # Ограничиваем шириной панели, если нужно
                if stamp_width > panel_width - 20:
                    ratio = (panel_width - 20) / stamp_width
                    stamp_width = panel_width - 20
                    stamp_height = int(stamp_height * ratio)

                stamp_resized = self.stamp_image.resize((stamp_width, stamp_height), Image.Resampling.LANCZOS)

                stamp_y = text_y + 20
                # Применяем смещение для печати
                offset_x, offset_y = element_offsets.get("stamp", (0, 0))
                # Добавляем печать независимо от проверки - она всегда должна быть видна
                print(f"DEBUG: Добавляем печать на позицию y={stamp_y}, высота панели={panel_area[3]}, масштаб={stamp_scale}")
                try:
                    result.paste(stamp_resized, (text_x + int(offset_x), stamp_y + int(offset_y)), stamp_resized)
                except Exception as e:
                    print(f"DEBUG: Ошибка вставки печати: {e}")
            
            # Сохранение результата
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Конвертируем в RGB для сохранения в JPG/PDF
            if output_format in ('jpg', 'jpeg', 'pdf'):
                result_rgb = Image.new('RGB', result.size, bg_color)
                result_rgb.paste(result, mask=result.split()[3] if result.mode == 'RGBA' else None)
                result = result_rgb
            
            if output_format == 'pdf':
                # Сохраняем как PDF
                self._save_as_pdf(result, str(output_path_obj))
            elif output_format in ('jpg', 'jpeg'):
                result.save(str(output_path_obj), 'JPEG', quality=95)
            else:
                result.save(str(output_path_obj), 'PNG')
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Ошибка обработки: {str(e)}"
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Перенос текста по ширине."""
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            if not words:
                lines.append('')
                continue
            
            current_line = words[0]
            for word in words[1:]:
                test_line = f"{current_line} {word}"
                try:
                    bbox = font.getbbox(test_line)
                    line_width = bbox[2] - bbox[0]
                except:
                    line_width = len(test_line) * (font.size // 2)
                
                if line_width <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
        
        return lines
    
    def _save_as_pdf(self, image: Image.Image, output_path: str) -> None:
        """Сохранение изображения как PDF."""
        # Сохраняем во временный буфер как PNG
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Конвертируем в PDF
        pdf_bytes = img2pdf.convert(img_buffer.getvalue())
        
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
    
    def generate_preview(
        self,
        image_path: str,
        excel_data: Dict,
        fixed_texts: List[str],
        max_size: Tuple[int, int] = (800, 600)
    ) -> Optional[Image.Image]:
        """Генерация превью результата."""
        try:
            # Создаём временный файл в памяти
            temp_output = io.BytesIO()
            
            # Сохраняем текущий формат и временно меняем на PNG
            original_format = self.settings.get("format", "png")
            self.settings["format"] = "png"
            
            # Обрабатываем изображение
            original = Image.open(image_path)
            if original.mode != 'RGBA':
                original = original.convert('RGBA')
            
            # Уменьшаем для превью
            original.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Параметры
            panel_width = min(self.settings.get("panel_width", 300), max_size[0] // 3)
            position = self.settings.get("position", "left")
            bg_color = self.settings.get("background_color", "#FFFFFF")
            font_size = max(8, self.settings.get("font_size", 12) - 2)
            text_color = self.settings.get("text_color", "#000000")
            
            # Загружаем шрифт для расчёта размеров
            font = self._get_font(font_size)
            line_height = font_size + 4

            # Создание результата
            if position == "left":
                new_width = original.width + panel_width
                new_height = original.height
                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (panel_width, 0))
                panel_area = (0, 0, panel_width, new_height)
            else:
                # Динамический расчёт высоты панели снизу
                panel_height = 20  # Начальный отступ
                excel_fields = self.settings.get("excel_fields", {})

                # ИНН
                if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                    panel_height += line_height

                # КПП
                if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                    panel_height += line_height

                # Поставщик (2 строки: заголовок + название)
                if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                    panel_height += line_height * 2

                # Разделитель
                panel_height += 5

                # Фиксированные тексты
                for text in fixed_texts:
                    if text:
                        panel_height += line_height

                # Печать (если есть)
                if self.stamp_image and self.settings.get("stamp_enabled", True):
                    stamp_scale = self.settings.get("stamp_scale", 1.0)
                    # Применяем масштаб
                    stamp_width = int(self.stamp_image.width * stamp_scale)
                    stamp_height = int(self.stamp_image.height * stamp_scale)
                    # Ограничиваем шириной
                    if stamp_width > panel_width - 20:
                        ratio = (panel_width - 20) / stamp_width
                        stamp_height = int(stamp_height * ratio)
                    panel_height += stamp_height + 40  # +40 для отступов

                # Добавляем минимальный отступ снизу
                panel_height += 20

                new_width = original.width
                new_height = original.height + panel_height
                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (0, 0))
                panel_area = (0, original.height, new_width, new_height)

            draw = ImageDraw.Draw(result)

            text_x = panel_area[0] + 5
            text_y = panel_area[1] + 5

            # Добавляем данные
            excel_fields = self.settings.get("excel_fields", {})

            if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                draw.text((text_x, text_y), f"ИНН: {excel_data['inn']}", fill=text_color, font=font)
                text_y += line_height

            if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                draw.text((text_x, text_y), f"КПП: {excel_data['kpp']}", fill=text_color, font=font)
                text_y += line_height

            if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                supplier = excel_data['supplier'][:30] + "..." if len(excel_data['supplier']) > 30 else excel_data['supplier']
                draw.text((text_x, text_y), f"Поставщик:", fill=text_color, font=font)
                text_y += line_height
                draw.text((text_x, text_y), supplier, fill=text_color, font=font)
                text_y += line_height

            # Фиксированные тексты
            text_y += 5
            print(f"DEBUG PREVIEW: Фиксированные тексты: {fixed_texts}")
            for text in fixed_texts:  # Показываем все тексты
                if text:
                    short_text = text[:35] + "..." if len(text) > 35 else text
                    print(f"DEBUG PREVIEW: Добавляем текст в превью: '{short_text}'")
                    draw.text((text_x, text_y), short_text, fill=text_color, font=font)
                    text_y += line_height

            # Добавляем печать, если она загружена
            if self.stamp_image and self.settings.get("stamp_enabled", True):
                stamp_scale = self.settings.get("stamp_scale", 1.0)

                # Применяем масштаб к оригинальному размеру
                stamp_width = int(self.stamp_image.width * stamp_scale)
                stamp_height = int(self.stamp_image.height * stamp_scale)

                # Ограничиваем шириной панели, если нужно
                if stamp_width > panel_width - 20:
                    ratio = (panel_width - 20) / stamp_width
                    stamp_width = panel_width - 20
                    stamp_height = int(stamp_height * ratio)

                stamp_resized = self.stamp_image.resize((stamp_width, stamp_height), Image.Resampling.LANCZOS)

                stamp_y = text_y + 20
                # Добавляем печать всегда
                result.paste(stamp_resized, (text_x, stamp_y), stamp_resized)

            # Восстанавливаем формат
            self.settings["format"] = original_format

            return result

        except Exception as e:
            print(f"Ошибка генерации превью: {e}")
            return None

    def generate_preview_with_positions(
        self,
        image_path: str,
        excel_data: Dict,
        fixed_texts: List[str],
        max_size: Tuple[int, int] = (800, 600)
    ) -> Optional[Tuple[Image.Image, Dict]]:
        """
        Генерация превью с информацией о позициях элементов.

        Returns:
            Tuple[Image.Image, Dict]: (изображение, словарь позиций элементов)
            Словарь формата: {element_name: (x, y, text, font_size)}
        """
        try:
            # Обрабатываем изображение
            original = Image.open(image_path)
            if original.mode != 'RGBA':
                original = original.convert('RGBA')

            # Уменьшаем для превью
            original.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Параметры
            panel_width = min(self.settings.get("panel_width", 300), max_size[0] // 3)
            position = self.settings.get("position", "left")
            bg_color = self.settings.get("background_color", "#FFFFFF")
            font_size = max(8, self.settings.get("font_size", 12) - 2)
            text_color = self.settings.get("text_color", "#000000")

            # Загружаем шрифт для расчёта размеров
            font = self._get_font(font_size)
            line_height = font_size + 4

            # Словарь для хранения позиций элементов
            element_positions = {}

            # Создание результата
            if position == "left":
                new_width = original.width + panel_width
                new_height = original.height
                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (panel_width, 0))
                panel_area = (0, 0, panel_width, new_height)
            else:
                # Динамический расчёт высоты панели снизу
                panel_height = 20
                excel_fields = self.settings.get("excel_fields", {})

                if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                    panel_height += line_height
                if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                    panel_height += line_height
                if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                    panel_height += line_height * 2
                panel_height += 5

                for text in fixed_texts:
                    if text:
                        panel_height += line_height

                if self.stamp_image and self.settings.get("stamp_enabled", True):
                    stamp_scale = self.settings.get("stamp_scale", 1.0)
                    # Применяем масштаб
                    stamp_width = int(self.stamp_image.width * stamp_scale)
                    stamp_height = int(self.stamp_image.height * stamp_scale)
                    # Ограничиваем шириной
                    if stamp_width > panel_width - 20:
                        ratio = (panel_width - 20) / stamp_width
                        stamp_height = int(stamp_height * ratio)
                    panel_height += stamp_height + 40

                panel_height += 20

                new_width = original.width
                new_height = original.height + panel_height
                result = Image.new('RGBA', (new_width, new_height), bg_color)
                result.paste(original, (0, 0))
                panel_area = (0, original.height, new_width, new_height)

            text_x = panel_area[0] + 5
            text_y = panel_area[1] + 5

            # Добавляем данные и сохраняем позиции
            excel_fields = self.settings.get("excel_fields", {})

            if excel_fields.get("inn", {}).get("enabled") and excel_data.get("inn"):
                text_content = f"ИНН: {excel_data['inn']}"
                element_positions["inn"] = (text_x, text_y, text_content, font_size)
                text_y += line_height

            if excel_fields.get("kpp", {}).get("enabled") and excel_data.get("kpp"):
                text_content = f"КПП: {excel_data['kpp']}"
                element_positions["kpp"] = (text_x, text_y, text_content, font_size)
                text_y += line_height

            if excel_fields.get("supplier", {}).get("enabled") and excel_data.get("supplier"):
                supplier = excel_data['supplier'][:30] + "..." if len(excel_data['supplier']) > 30 else excel_data['supplier']
                element_positions["supplier_label"] = (text_x, text_y, "Поставщик:", font_size)
                text_y += line_height
                element_positions["supplier_value"] = (text_x, text_y, supplier, font_size)
                text_y += line_height

            # Фиксированные тексты
            text_y += 5
            for idx, text in enumerate(fixed_texts):
                if text:
                    short_text = text[:35] + "..." if len(text) > 35 else text
                    element_positions[f"text_{idx+1}"] = (text_x, text_y, short_text, font_size)
                    text_y += line_height

            # Печать
            if self.stamp_image and self.settings.get("stamp_enabled", True):
                stamp_scale = self.settings.get("stamp_scale", 1.0)

                # Применяем масштаб к оригинальному размеру
                stamp_width = int(self.stamp_image.width * stamp_scale)
                stamp_height = int(self.stamp_image.height * stamp_scale)

                # Ограничиваем шириной панели, если нужно
                if stamp_width > panel_width - 20:
                    ratio = (panel_width - 20) / stamp_width
                    stamp_width = panel_width - 20
                    stamp_height = int(stamp_height * ratio)

                stamp_y = text_y + 20
                # Добавляем позицию печати
                element_positions["stamp"] = (text_x, stamp_y, None, None)  # Печать не имеет текста

            # Возвращаем фоновое изображение БЕЗ нарисованных элементов
            # Элементы будут добавлены как интерактивные в UI
            return (result, element_positions)

        except Exception as e:
            print(f"Ошибка генерации превью с позициями: {e}")
            return None


def get_image_files(folder_path: str) -> List[str]:
    """Получение списка файлов изображений в папке."""
    folder = Path(folder_path)
    if not folder.exists():
        return []
    
    files = set()
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in ImageProcessor.SUPPORTED_FORMATS:
            files.add(file)
    
    return [str(f) for f in sorted(files)]

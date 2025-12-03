"""Скрипт для создания иконки приложения."""
from PIL import Image, ImageDraw, ImageFont

# Создаем иконку 512x512 (рекомендуемый размер для macOS)
size = 512
icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(icon)

# Рисуем градиентный фон
for y in range(size):
    color_value = int(34 + (139 - 34) * (y / size))  # От #228be6 к более темному
    draw.rectangle([(0, y), (size, y+1)], fill=(34, color_value, 230, 255))

# Рисуем белую рамку
border = 20
draw.rectangle(
    [(border, border), (size-border, size-border)],
    outline=(255, 255, 255, 255),
    width=15
)

# Рисуем символ изображения (прямоугольник с горами)
img_rect_x = size // 4
img_rect_y = size // 4
img_rect_w = size // 2
img_rect_h = size // 2

# Белый прямоугольник внутри
draw.rectangle(
    [(img_rect_x, img_rect_y), (img_rect_x + img_rect_w, img_rect_y + img_rect_h)],
    fill=(255, 255, 255, 255),
    outline=(200, 200, 200, 255),
    width=3
)

# Рисуем "горы" (треугольники)
mountain1 = [
    (img_rect_x + 30, img_rect_y + img_rect_h - 30),
    (img_rect_x + 80, img_rect_y + 80),
    (img_rect_x + 130, img_rect_y + img_rect_h - 30)
]
draw.polygon(mountain1, fill=(100, 149, 237, 255))

# Солнце
sun_x = img_rect_x + img_rect_w - 60
sun_y = img_rect_y + 50
draw.ellipse(
    [(sun_x, sun_y), (sun_x + 40, sun_y + 40)],
    fill=(255, 215, 0, 255)
)

# Добавляем текст "A" (Annotator)
try:
    # Пытаемся загрузить системный шрифт
    font_size = 180
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except:
            continue

    if font:
        # Рисуем "A" внизу справа
        text = "A"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = size - text_width - 40
        text_y = size - text_height - 60

        # Тень
        draw.text((text_x + 3, text_y + 3), text, font=font, fill=(0, 0, 0, 128))
        # Основной текст
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
except Exception as e:
    print(f"Не удалось добавить текст: {e}")

# Сохраняем иконку
icon.save('resources/icon.png', 'PNG')
print("Иконка сохранена: resources/icon.png")

# Создаем версии разных размеров для .icns
sizes = [16, 32, 64, 128, 256, 512]
for s in sizes:
    resized = icon.resize((s, s), Image.Resampling.LANCZOS)
    resized.save(f'resources/icon_{s}x{s}.png', 'PNG')
    print(f"Создана иконка {s}x{s}")

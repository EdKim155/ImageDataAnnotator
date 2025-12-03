"""Скрипт для создания .ico иконки для Windows."""
from PIL import Image

# Используем уже созданную PNG иконку
icon_png = Image.open('resources/icon.png')

# Создаем .ico файл с несколькими размерами
# Windows поддерживает размеры: 16, 24, 32, 48, 64, 128, 256
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

icon_images = []
for size in sizes:
    resized = icon_png.resize(size, Image.Resampling.LANCZOS)
    icon_images.append(resized)

# Сохраняем как .ico
icon_images[0].save(
    'resources/icon.ico',
    format='ICO',
    sizes=sizes,
    append_images=icon_images[1:]
)

print("✓ Иконка для Windows создана: resources/icon.ico")

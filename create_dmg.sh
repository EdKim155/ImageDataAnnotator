#!/bin/bash
# Скрипт для создания DMG установщика

set -e

echo "================================================"
echo "Создание DMG установщика"
echo "================================================"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

APP_NAME="Image Data Annotator"
DMG_NAME="ImageDataAnnotator-v1.0.0"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${DMG_NAME}.dmg"
TEMP_DMG="dist/temp.dmg"

# Проверяем наличие приложения
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}Ошибка: Приложение не найдено в $APP_PATH${NC}"
    echo "Сначала запустите: ./build_app.sh"
    exit 1
fi

# Удаляем старый DMG если существует
rm -f "$DMG_PATH" "$TEMP_DMG"

# Создаем временную папку для DMG
echo -e "${BLUE}Создание временной структуры...${NC}"
TEMP_DIR="dist/dmg_temp"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Копируем приложение
cp -r "$APP_PATH" "$TEMP_DIR/"

# Создаем символическую ссылку на Applications
ln -s /Applications "$TEMP_DIR/Applications"

# Создаем README
cat > "$TEMP_DIR/README.txt" << 'EOF'
Image Data Annotator v1.0.0

Установка:
1. Перетащите "Image Data Annotator.app" в папку "Applications"
2. Откройте приложение из Launchpad или папки Applications
3. При первом запуске подтвердите открытие в настройках безопасности

Системные требования:
- macOS 10.13 или новее
- 200 МБ свободного места на диске

Поддержка:
Если у вас возникли проблемы, проверьте права доступа к файлам
или переустановите приложение.

Copyright © 2024
EOF

echo -e "${BLUE}Создание DMG образа...${NC}"

# Создаем временный DMG
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$TEMP_DIR" \
    -ov -format UDRW \
    "$TEMP_DMG"

# Конвертируем в сжатый формат
echo -e "${BLUE}Сжатие DMG...${NC}"
hdiutil convert "$TEMP_DMG" \
    -format UDZO \
    -o "$DMG_PATH"

# Очищаем временные файлы
rm -rf "$TEMP_DIR" "$TEMP_DMG"

if [ -f "$DMG_PATH" ]; then
    echo -e "${GREEN}✓ DMG создан успешно!${NC}"
    echo ""
    echo "Файл: $DMG_PATH"
    SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    echo "Размер: $SIZE"
    echo ""
    echo "================================================"
    echo "DMG готов к распространению!"
    echo "================================================"
    echo ""
    echo "Пользователи смогут:"
    echo "1. Скачать файл $DMG_NAME.dmg"
    echo "2. Открыть его двойным кликом"
    echo "3. Перетащить приложение в папку Applications"
    echo ""
else
    echo -e "${RED}✗ Ошибка при создании DMG${NC}"
    exit 1
fi

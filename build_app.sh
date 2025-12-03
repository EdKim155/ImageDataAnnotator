#!/bin/bash
# Скрипт для сборки приложения Image Data Annotator

set -e  # Останавливаем выполнение при ошибке

echo "================================================"
echo "Сборка Image Data Annotator для macOS"
echo "================================================"

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo -e "${RED}Ошибка: Виртуальное окружение не найдено${NC}"
    echo "Создайте виртуальное окружение: python3 -m venv venv"
    exit 1
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Проверяем установку PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${BLUE}Установка PyInstaller...${NC}"
    pip install pyinstaller
fi

# Очищаем предыдущие сборки
echo -e "${BLUE}Очистка предыдущих сборок...${NC}"
rm -rf build dist
mkdir -p dist

# Запускаем сборку
echo -e "${BLUE}Сборка приложения...${NC}"
pyinstaller ImageDataAnnotator.spec --clean

# Проверяем результат
if [ -d "dist/Image Data Annotator.app" ]; then
    echo -e "${GREEN}✓ Сборка завершена успешно!${NC}"
    echo ""
    echo "Приложение создано: dist/Image Data Annotator.app"
    echo ""

    # Получаем размер приложения
    SIZE=$(du -sh "dist/Image Data Annotator.app" | cut -f1)
    echo "Размер приложения: $SIZE"
    echo ""

    echo "================================================"
    echo "Что делать дальше:"
    echo "================================================"
    echo "1. Протестировать приложение:"
    echo "   open 'dist/Image Data Annotator.app'"
    echo ""
    echo "2. Скопировать в Applications:"
    echo "   cp -r 'dist/Image Data Annotator.app' /Applications/"
    echo ""
    echo "3. Создать DMG для распространения:"
    echo "   ./create_dmg.sh"
    echo ""
else
    echo -e "${RED}✗ Ошибка при сборке${NC}"
    exit 1
fi

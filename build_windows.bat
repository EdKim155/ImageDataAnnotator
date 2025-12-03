@echo off
REM Скрипт для сборки приложения Image Data Annotator для Windows
REM Запускать на Windows машине с установленным Python 3.8+

echo ================================================
echo Сборка Image Data Annotator для Windows
echo ================================================
echo.

REM Проверяем наличие виртуального окружения
if not exist "venv\" (
    echo [ОШИБКА] Виртуальное окружение не найдено
    echo Создайте виртуальное окружение: python -m venv venv
    pause
    exit /b 1
)

REM Активируем виртуальное окружение
call venv\Scripts\activate.bat

REM Проверяем установку PyInstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Установка PyInstaller...
    pip install pyinstaller
)

REM Очищаем предыдущие сборки
echo [INFO] Очистка предыдущих сборок...
if exist "build\" rmdir /s /q build
if exist "dist\" rmdir /s /q dist
mkdir dist

REM Запускаем сборку
echo [INFO] Сборка приложения...
echo.
pyinstaller ImageDataAnnotator_Windows.spec --clean

REM Проверяем результат
if exist "dist\ImageDataAnnotator\" (
    echo.
    echo ================================================
    echo [УСПЕХ] Сборка завершена успешно!
    echo ================================================
    echo.
    echo Приложение создано: dist\ImageDataAnnotator\
    echo.
    echo Исполняемый файл: dist\ImageDataAnnotator\ImageDataAnnotator.exe
    echo.
    echo ================================================
    echo Что делать дальше:
    echo ================================================
    echo 1. Протестировать приложение:
    echo    dist\ImageDataAnnotator\ImageDataAnnotator.exe
    echo.
    echo 2. Создать установщик:
    echo    build_installer.bat
    echo.
    echo 3. Скопировать папку dist\ImageDataAnnotator
    echo    на другой компьютер для использования
    echo.
) else (
    echo.
    echo [ОШИБКА] Сборка не удалась
    pause
    exit /b 1
)

pause

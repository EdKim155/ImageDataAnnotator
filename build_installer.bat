@echo off
REM Скрипт для создания установщика с помощью Inno Setup

echo ================================================
echo Создание установщика Image Data Annotator
echo ================================================
echo.

REM Проверяем наличие собранного приложения
if not exist "dist\ImageDataAnnotator\ImageDataAnnotator.exe" (
    echo [ОШИБКА] Приложение не собрано!
    echo Сначала запустите: build_windows.bat
    pause
    exit /b 1
)

REM Ищем Inno Setup Compiler
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if not exist %ISCC% (
    echo [ОШИБКА] Inno Setup не найден!
    echo.
    echo Пожалуйста, установите Inno Setup:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo После установки запустите этот скрипт снова.
    pause
    exit /b 1
)

REM Создаем папку для установщика
if not exist "dist\installer\" mkdir dist\installer

REM Компилируем установщик
echo [INFO] Компиляция установщика...
echo.
%ISCC% installer.iss

REM Проверяем результат
if exist "dist\installer\ImageDataAnnotator-Setup-v1.0.0.exe" (
    echo.
    echo ================================================
    echo [УСПЕХ] Установщик создан успешно!
    echo ================================================
    echo.
    echo Файл: dist\installer\ImageDataAnnotator-Setup-v1.0.0.exe
    echo.
    for %%A in ("dist\installer\ImageDataAnnotator-Setup-v1.0.0.exe") do echo Размер: %%~zA байт
    echo.
    echo ================================================
    echo Установщик готов к распространению!
    echo ================================================
    echo.
    echo Пользователи смогут:
    echo 1. Скачать файл ImageDataAnnotator-Setup-v1.0.0.exe
    echo 2. Запустить установщик двойным кликом
    echo 3. Следовать инструкциям мастера установки
    echo 4. Запустить приложение из меню Пуск или с рабочего стола
    echo.
) else (
    echo.
    echo [ОШИБКА] Не удалось создать установщик
    pause
    exit /b 1
)

pause

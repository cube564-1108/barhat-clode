@echo off
chcp 65001 >nul
echo ===============================================
echo     Запуск лендинга через py launcher
echo ===============================================
echo.

cd /d "%~dp0"

echo Проверка py launcher...
py --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] py launcher не найден
    pause
    exit /b 1
)

echo [OK] py launcher найден
echo.
echo Установка зависимостей через py...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Возможны проблемы с зависимостями
    echo Попробуем запустить сервер...
)

echo.
echo Запуск сервера через py...
py app.py
pause

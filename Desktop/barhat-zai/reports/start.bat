@echo off
chcp 65001 >nul
echo ===============================================
echo     Запуск лендинга отчетов Бархат
echo ===============================================
echo.

cd /d "%~dp0"

echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo.
    echo Установите Python с https://python.org
    echo При установке отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python найден
echo.
echo Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости
    pause
    exit /b 1
)
echo.
echo ===============================================
echo     Запуск сервера на http://localhost:5000
echo ===============================================
echo.
echo Нажми Ctrl+C для остановки сервера
echo.

python app.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сервер завершился с ошибкой
    pause
)

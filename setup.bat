@echo off
echo Установка виртуального окружения и зависимостей для проекта...

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка: Python не установлен. Пожалуйста, установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Создание виртуального окружения
python -m venv venv
call venv\Scripts\activate

REM Установка зависимостей
pip install -r requirements.txt

echo Виртуальное окружение настроено. Для запуска приложения используйте:
echo     1. Активируйте окружение: venv\Scripts\activate
echo     2. Запустите приложение: python app.py

pause

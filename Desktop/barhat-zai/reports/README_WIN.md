# Запуск лендинга отчетов

## Для Windows

### Вариант 1: Через bat-файл (рекомендуется)

1. Открой папку `reports`
2. Дважды кликни на `start.bat`
3. Открой в браузере: http://localhost:5000

### Вариант 2: В командной строке

```cmd
cd reports
pip install -r requirements.txt
python app.py
```

### Вариант 3: В PowerShell

```powershell
cd reports
pip install -r requirements.txt
python app.py
```

## Что делать, если не работает:

### Python не найден

1. Скачай Python с https://python.org
2. При установке отметь "Add Python to PATH"
3. Перезапусти командную строку

### Ошибка при установке зависимостей

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### Порт 5000 занят

Отредактируй `app.py` и замени порт:
```python
port = int(os.getenv('PORT', 5001))  # Вместо 5000
```

## После запуска

1. Открой в браузере: http://localhost:5000
2. Выбери период для отчета
3. Нажми "Сформировать отчет"
4. Жди загрузки (может занять время для больших периодов)

# Quality Dashboard

Аналитический dashboard для мониторинга качества сборки букетов по салонам, флористам и видам заказов с данными из Pyrus.

## Установка

1. Создать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Настроить переменные окружения:
```bash
cp .env.example .env
# редактировать .env с реальными значениями
```

## Запуск

```bash
python app.py
```

Dashboard будет доступен на http://localhost:5000

## Структура

```
quality-dashboard/
├── app.py              # Flask приложение
├── pyrus_client.py     # Pyrus API клиент
├── database.py         # Работа с SQLite
├── aggregator.py       # Агрегация данных
├── alerts.py           # Система алертов
├── models.py           # Константы и типы
├── requirements.txt
├── .env.example
└── templates/
    └── dashboard.html
```

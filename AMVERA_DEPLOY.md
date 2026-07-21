# Amvera Deploy — Quality Dashboard

Инструкция по деплою Quality Dashboard в Amvera.

## 📋 Предварительные требования

1. Аккаунт в Amvera (https://amvera.ru)
2. GitHub репозиторий с кодом проекта
3. Данные для доступа к Pyrus API

## 🚀 Шаг 1: Подключение GitHub репозитория

1. Зайдите в панель Amvera
2. Создайте новый проект
3. Выберите "Import from Git"
4. Подключите ваш GitHub аккаунт
5. Выберите репозиторий `barhat-clode`
6. Ветка: `main`

## 🔧 Шаг 2: Настройка переменных окружения

Перейдите в **Settings → Environment Variables** и добавьте:

### Обязательные переменные:

```bash
# Доступ к Pyrus API
PYRUS_LOGIN=your_login_here
PYRUS_ACCESS_TOKEN=your_token_here

# Безопасность
SECRET_KEY=сгенерируйте_случайный_ключ_минимум_32_символа
```

### Опциональные переменные (для защиты через header):

```bash
SECRET_HEADER_NAME=X-Secret-Header
SECRET_HEADER_VALUE=your_secret_value_here
```

### Генерация SECRET_KEY:

```python
import secrets
print(secrets.token_urlsafe(32))
```

## 💾 Шаг 3: Настройка персистентного хранилища

Для сохранения базы данных между перезапусками:

1. Перейдите в **Settings → Volumes**
2. Добавьте новый Volume:
   - **Mount Path**: `/app/data`
   - **Size**: 1GB (или больше по необходимости)

## 🔄 Шаг 4: Первый деплой

1. Нажмите **Deploy** в панели Amvera
2. Дождитесь окончания сборки и запуска
3. Проверьте логи в разделе **Logs**

## ✅ Шаг 5: Проверка работоспособности

После успешного деплоя проверьте эндпоинты:

### Health Check:
```
https://your-project.amvera.ru/api/health
```
Ожидаемый ответ:
```json
{
  "status": "ok",
  "timestamp": "2026-07-21T...",
  "db_connected": true
}
```

### Главная страница:
```
https://your-project.amvera.ru/
```

## 📊 Шаг 6: Настройка автоматического обновления

Опционально: настройте cron для периодического обновления данных из Pyrus.

В Amvera это можно сделать через:
1. **Cron Jobs** (если доступно)
2. Внешний сервис (например, cron-job.org)

Эндпоинт для обновления:
```
POST https://your-project.amvera.ru/api/sync
```

## 🔒 Шаг 7: Защита приложения (опционально)

Если настроили `SECRET_HEADER_NAME` и `SECRET_HEADER_VALUE`:

1. Все запросы к API должны содержать header:
   ```
   X-Secret-Header: your_secret_value_here
   ```

2. Для frontend это означает добавление header в каждый fetch запрос.

## 📝 Структура проекта

```
.
├── amvera.yml          # Конфигурация Amvera
├── app.py              # Flask приложение
├── database.py         # Работа с БД (хранит в /app/data)
├── models.py           # Модели данных
├── aggregator.py       # Агрегация статистики
├── alerts.py           # Система алертов
├── pyrus_client.py     # Клиент Pyrus API
├── requirements.txt    # Зависимости Python
├── run.py             # Entry point
├── Procfile           # Heroku-совместимый конфиг
├── start.sh           # Стартовый скрипт
├── .dockerignore      # Исключения для Docker
└── templates/
    └── dashboard.html # Frontend
```

## 🐛 Troubleshooting

### Ошибка: Unauthorized (401)

- Проверьте `SECRET_HEADER_NAME` и `SECRET_HEADER_VALUE`
- В development режиме (`FLASK_DEBUG=1`) защита отключена

### Ошибка: База данных не сохраняется

- Проверьте, что Volume настроен на `/app/data`
- Проверьте логи на наличие ошибок при создании директории

### Ошибка: Нет данных в дашборде

- Проверьте корректность `PYRUS_LOGIN` и `PYRUS_ACCESS_TOKEN`
- Запустите синхронизацию: `POST /api/sync`
- Проверьте логи на ошибки Pyrus API

### Медленная работа

- Увеличьте количество workers в `amvera.yml`
- Проверьте ресурсы в настройках проекта

## 📚 Полезные ссылки

- [Amvera Documentation](https://docs.amvera.ru)
- [Flask Deployment](https://flask.palletsprojects.com/en/latest/deploying/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

## 🔗 Следующие шаги

1. Настройте мониторинг (Amvera предоставляет метрики)
2. Настройте алерты (уведомления о проблемах)
3. Добавьте логирование в облачный сервис (например, Sentry)
4. Настройте бэкапы Volume с базой данных

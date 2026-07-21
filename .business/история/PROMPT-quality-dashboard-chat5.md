# Промт для следующей сессии (Чат 5 — Flask и Деплой)

Скопируй этот текст в новую сессию Claude:

---

# Чат 5: Quality Dashboard — Flask и Деплой

Прочитай план `plans/2026-07-21-quality-dashboard.md` и продолжи с текущего состояния.

## Контекст

Это Чат 5 из multi-chat workflow по Quality Dashboard.
- Чат 4 завершил локальное тестирование
- Данные загружены: 15144 задач, 12 салонов, 18 флористов
- Статический HTML dashboard работает
- Pyrus API интеграция протестирована

## Текущее состояние

**Сделано:**
- ✅ Pyrus API клиент (с авторизацией login/security_key)
- ✅ Загрузка данных (sync_from_pyrus.py)
- ✅ База данных SQLite с 15144 задачами
- ✅ Агрегация данных
- ✅ Система алертов
- ✅ Статический HTML dashboard
- ✅ Все модули протестированы

**Проблема:**
- ❌ Flask не установлен (pip issue с SOCKS прокси)
- ❌ Flask dashboard не запущен

## Что делать

1. **Установить Flask и зависимости:**
   - Попробовать обходные пути для pip
   - Или использовать virtualenv
   - Или установить Flask вручную

2. **Запустить Flask dashboard:**
   - `python app.py`
   - Проверить все API endpoints
   - Проверить работу фильтров

3. **Если Flask работает — Фаза 4 (Фильтры и интерактивность):**
   - Проверить drill-down по салонам
   - Проверить фильтры по периоду

4. **Фаза 6 — Деплой в Amvera:**
   - Создать Procfile
   - Создать amvera.yml
   - Настроить secrets
   - Задеплоить

## Ключевые файлы

- `src/quality-dashboard/app.py` — Flask приложение
- `src/quality-dashboard/templates/dashboard.html` — Frontend
- `src/quality-dashboard/sync_from_pyrus.py` — Загрузка данных
- `src/quality-dashboard/quality_dashboard.db` — БД с данными

## Учетные данные Pyrus

Они уже в `.env` файле:
- `PYRUS_LOGIN=komdir.barhat@gmail.com`
- `PYRUS_ACCESS_TOKEN=tuF2LSG...`

## После завершения

1. Протестировать dashboard на проде
2. Создать еженедельный cron для обновления данных
3. Записать рефлексию в `.business/история/`

---

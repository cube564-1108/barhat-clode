# Промт для следующей сессии (Чат 7 — Quality Dashboard)

Скопируй этот текст в новую сессию Claude:

---

# Чат 7: Quality Dashboard — Продолжение работы

Прочитай план `plans/2026-07-21-quality-dashboard.md` и продолжи с текущего состояния.

## Контекст

Это Чат 7 из multi-chat workflow по Quality Dashboard.
- Чат 6 завершил добавление фильтрации по периодам и запуск Flask
- Данные загружены: 15144 задач, 12 салонов, 18 флористов
- Flask приложение работает на `http://localhost:5000`
- Фильтр по периодам работает (24 месяца)

## Текущее состояние

**Сделано:**
- ✅ Pyrus API клиент (с lazy initialization)
- ✅ Загрузка данных (sync_from_pyrus.py)
- ✅ База данных SQLite с 15144 задачами
- ✅ Периоды вычислены (Месяц Год формат)
- ✅ Flask приложение запущено
- ✅ Фильтр по периодам работает
- ✅ API endpoints: /health, /periods, /summary, /salons, /florists

**Проблемы:**
- ❌ MarkupSafe установлен как stub (временное решение)
- ❌ Фильтрация по периодам не тестируется в UI
- ❌ Drill-down по салонам не реализован

## Что делать

1. **Проверить работу фильтрации периодов в UI:**
   - Открыть http://localhost:5000
   - Проверить что выпадающий список периодов populated
   - Выбрать период и проверить обновление данных

2. **Фаза 4 — Фильтры и интерактивность (дополнить):**
   - Drill-down по клику на салон → показ флористов салона
   - Хлебные крошки для навигации вверх
   - Multi-select по салонам

3. **Фаза 6 — Деплой в Amvera:**
   - Создать Procfile
   - Создать amvera.yml
   - Настроить secrets (.env переменные)
   - Задеплоить

## Ключевые файлы

- `src/quality-dashboard/app.py` — Flask приложение
- `src/quality-dashboard/templates/dashboard.html` — Frontend
- `src/quality-dashboard/database.py` — БД
- `src/quality-dashboard/aggregator.py` — Агрегация
- `src/quality-dashboard/quality_dashboard.db` — БД с данными
- `src/quality-dashboard/.env` — Учетные данные (создан)

## Учетные данные Pyrus

Они в `.env` файле:
- `PYRUS_LOGIN=komdir.barhat@gmail.com`
- `PYRUS_ACCESS_TOKEN=tuF2LSG...` (токен обрезан, в файле полный)

## Flask запуск

```bash
cd "c:\Users\Станислав\Desktop\barhat-clode\src\quality-dashboard"
python app.py
```

Приложение будет доступно на `http://localhost:5000`

## После завершения

1. Протестировать все фильтры
2. Проверить drill-down навигацию
3. Записать рефлексию в `.business/история/`

---

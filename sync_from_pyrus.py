"""
Скрипт для загрузки данных из Pyrus в локальную БД
Запуск: python sync_from_pyrus.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Импортируем модули
from pyrus_client import PyrusClient
from database import DatabaseManager
from models import (
    QualityTask, QUALITY_CRITERIA, MAX_SCORES_BY_ORDER_TYPE,
    GROUPING_FIELDS
)


def parse_pyrus_task(task_data: dict) -> QualityTask:
    """Парсит задачу из формата Pyrus register в QualityTask"""

    task_id = task_data.get('id')
    created_date = task_data.get('create_date')

    # Парсим значения полей из fields
    values = {}  # field_name -> value
    values_by_id = {}  # field_id -> value

    for field in task_data.get('fields', []):
        field_id = field.get('id')
        field_name = field.get('name', '')
        value = field.get('value')

        # Для multiple_choice value может быть объектом
        if isinstance(value, dict):
            # Извлекаем choice_names (первый элемент списка)
            choice_names = value.get('choice_names', [])
            if choice_names:
                value = choice_names[0]
            else:
                value = None

        values[field_name] = value
        values_by_id[field_id] = value

    # Извлекаем данные по названиям полей
    salon = values.get(GROUPING_FIELDS['salon'], '')
    florist = values.get(GROUPING_FIELDS['florist'], '')
    order_type = values.get(GROUPING_FIELDS['order_type'], '')
    order_id = values.get(GROUPING_FIELDS['order_id'], '')
    date = values.get(GROUPING_FIELDS['date'], '')
    period = values.get(GROUPING_FIELDS['period'], '')
    comment = values.get(GROUPING_FIELDS['comment'], '')

    # Извлекаем оценки по критериям
    scores = {}
    total_score = 0

    for crit_key, crit_name in QUALITY_CRITERIA.items():
        score = values.get(crit_name)
        if score is not None:
            try:
                score = int(float(str(score)))
                scores[crit_key] = score
                total_score += score
            except (ValueError, TypeError):
                scores[crit_key] = None

    # Создаем задачу
    return QualityTask(
        task_id=task_id,
        created_at=datetime.fromisoformat(created_date) if created_date else datetime.now(),
        salon=salon,
        florist=florist,
        order_type=order_type,
        order_id=str(order_id) if order_id else '',
        date=date,
        period=period,
        comment=comment,
        scores=scores,
        total_score=total_score if total_score > 0 else None
    )


def main():
    print("=== Загрузка данных из Pyrus ===")
    print()

    # Инициализация
    db = DatabaseManager()
    db.init_db()

    client = PyrusClient()

    form_id = 1327961

    print(f"1. Получение задач формы {form_id}...")

    # Загружаем задачи
    response = client.get_form_tasks(form_id, max_count=10000)

    if not response.success:
        print(f"ERROR: {response.error}")
        sys.exit(1)

    tasks_data = response.data
    print(f"   OK: Загружено {len(tasks_data)} задач")
    print()

    # Очищаем БД перед загрузкой (опционально)
    print("2. Очистка старых данных...")
    db.clear_all_tasks()
    print("   OK: БД очищена")
    print()

    # Парсим и сохраняем задачи
    print("3. Парсинг и сохранение задач...")

    saved_count = 0
    skipped_count = 0
    error_count = 0

    for i, task_data in enumerate(tasks_data, 1):
        try:
            task = parse_pyrus_task(task_data)

            if not task.salon or not task.florist:
                skipped_count += 1
                continue

            if db.save_task(task):
                saved_count += 1
            else:
                error_count += 1

            # Прогресс
            if i % 100 == 0:
                print(f"   Обработано {i}/{len(tasks_data)}...")

        except Exception as e:
            error_count += 1
            print(f"   ERROR parsing task {task_data.get('id')}: {e}")

    print()
    print(f"   OK: Сохранено {saved_count} задач")
    if skipped_count > 0:
        print(f"   Пропущено {skipped_count} задач (нет салона/флориста)")
    if error_count > 0:
        print(f"   Ошибок {error_count}")
    print()

    # Обновляем метаданные
    db.set_last_sync(datetime.now().isoformat())

    # Статистика
    print("4. Статистика:")
    print(f"   Всего задач в БД: {db.get_task_count()}")
    print(f"   Салонов: {len(db.get_distinct_salons())}")
    print(f"   Флористов: {len(db.get_distinct_florists())}")
    print(f"   Периодов: {len(db.get_distinct_periods())}")
    print()

    print("=== OK: Загрузка завершена! ===")
    print()
    print("Теперь можно запустить dashboard:")
    print("  python app.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

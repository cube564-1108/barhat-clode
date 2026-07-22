#!/usr/bin/env python
"""
Нормализация периодов в БД — приведение к формату ММ.ГГГГ
"""
import sqlite3
import re
from pathlib import Path

DB_PATH = "quality_dashboard.db"

def normalize_period(period: str) -> str:
    """Приводит период к формату ММ.ГГГГ"""
    if not period:
        return period

    # Если уже в формате ММ.ГГГГ — возвращаем как есть
    if re.match(r'^\d{2}\.\d{4}$', period):
        return period

    # Разбираем период
    parts = period.split('.')
    if len(parts) != 2:
        return period

    month_str, year_str = parts
    try:
        month = int(month_str)
        year = int(year_str)
        # Форматируем с ведущим нулём
        return f"{month:02d}.{year}"
    except (ValueError, TypeError):
        return period

def main():
    print(f"Обработка БД: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем текущие форматы периодов
    cursor.execute('SELECT DISTINCT period FROM tasks WHERE period IS NOT NULL LIMIT 20')
    periods = [row[0] for row in cursor.fetchall()]
    print(f"Текущие периоды (образцы): {periods[:10]}")

    # Нормализуем периоды
    cursor.execute('SELECT task_id, period FROM tasks WHERE period IS NOT NULL')
    tasks_to_update = []

    for task_id, period in cursor.fetchall():
        normalized = normalize_period(period)
        if normalized != period:
            tasks_to_update.append((normalized, task_id))

    if tasks_to_update:
        print(f"Нужно обновить {len(tasks_to_update)} задач")
        cursor.executemany('UPDATE tasks SET period = ? WHERE task_id = ?', tasks_to_update)
        conn.commit()
        print(f"Обновлено {cursor.rowcount} записей")
    else:
        print("Все периоды уже в нормализованном формате")

    # Проверяем результат
    cursor.execute('SELECT DISTINCT period FROM tasks WHERE period IS NOT NULL ORDER BY period DESC LIMIT 10')
    updated_periods = [row[0] for row in cursor.fetchall()]
    print(f"Обновлённые периоды: {updated_periods}")

    conn.close()

if __name__ == "__main__":
    main()

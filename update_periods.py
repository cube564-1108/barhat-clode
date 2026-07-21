"""
Обновление периодов в БД на основе created_at
Запускается один раз для заполнения пустых полей period
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Русские названия месяцев
MONTH_NAMES_RU = [
    '',
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]

def format_period_month_year(date_str: str) -> str:
    """Форматирует дату в формат 'Месяц Год'

    Args:
        date_str: ISO формат даты (2023-10-13T04:45:53+00:00)

    Returns:
        str: 'Октябрь 2023' или '' если не удалось распарсить
    """
    if not date_str:
        return ''

    try:
        # Парсим ISO дату (игнорируем timezone для простоты)
        dt = datetime.fromisoformat(date_str.replace('+00:00', '').replace('Z', ''))
        return f"{MONTH_NAMES_RU[dt.month]} {dt.year}"
    except Exception as e:
        logging.warning(f"Не удалось распарсить дату {date_str}: {e}")
        return ''

def update_periods(db_path: str):
    """Обновляет пустые поля period на основе created_at"""
    logging.info(f"Обновление периодов в БД: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем сколько записей нужно обновить
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE period IS NULL OR period = ''")
        count = cursor.fetchone()[0]
        logging.info(f"Нужно обновить {count} записей")

        if count == 0:
            logging.info("Все записи уже имеют период")
            return

        # Получаем записи без периода
        cursor.execute(
            "SELECT rowid, created_at FROM tasks WHERE period IS NULL OR period = ''"
        )
        rows = cursor.fetchall()

        updated = 0
        for rowid, created_at in rows:
            period = format_period_month_year(created_at)
            if period:
                cursor.execute(
                    "UPDATE tasks SET period = ? WHERE rowid = ?",
                    (period, rowid)
                )
                updated += 1

        conn.commit()
        logging.info(f"Обновлено {updated} записей")

        # Показываем примеры периодов
        cursor.execute(
            "SELECT DISTINCT period FROM tasks WHERE period IS NOT NULL AND period != '' ORDER BY created_at DESC"
        )
        periods = [row[0] for row in cursor.fetchall()]
        logging.info(f"Уникальные периоды: {periods[:12]}...")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    DB_PATH = Path(__file__).parent / "quality_dashboard.db"
    update_periods(str(DB_PATH))

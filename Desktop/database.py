"""
Quality Dashboard — Работа с SQLite базой данных
"""

import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from models import (
    QualityTask, PYRUS_FORM_ID,
    QUALITY_CRITERIA, MAX_SCORES_BY_ORDER_TYPE,
    get_quality_status, get_status_emoji, extract_city
)


# ===== Логирование =====

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Пути =====

# Для Amvera и других облачных сервисов используем отдельную директорию для данных
# Это позволяет монтировать Volume для персистентности
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')

# Создаём директорию для данных если не существует
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "quality_dashboard.db")

logger.info(f"База данных будет храниться в: {DB_PATH}")


# ===== SQL Schema =====

SCHEMA_SQL = """
-- Таблица для сырых данных из Pyrus
CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY,
    form_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    salon TEXT,
    florist TEXT,
    order_type TEXT,
    order_id TEXT,
    date TEXT,
    period TEXT,
    comment TEXT,
    total_score INTEGER,
    max_score INTEGER DEFAULT 14,
    normalized_quality REAL DEFAULT 0,
    -- Критерии оценки (9 шт, каждое 0-2)
    catalog_match INTEGER,
    packaging_neatness INTEGER,
    strawberry_design INTEGER,
    flower_processing INTEGER,
    freshness INTEGER,
    assembly_technique INTEGER,
    film_separation INTEGER,
    materials_rules INTEGER,
    photo INTEGER,
    -- Метаданные
    synced_at TEXT NOT NULL,
    -- Для инкрементального обновления
    is_archived INTEGER DEFAULT 0
);

-- Индексы для частых запросов
CREATE INDEX IF NOT EXISTS idx_tasks_salon ON tasks(salon);
CREATE INDEX IF NOT EXISTS idx_tasks_florist ON tasks(florist);
CREATE INDEX IF NOT EXISTS idx_tasks_order_type ON tasks(order_type);
CREATE INDEX IF NOT EXISTS idx_tasks_period ON tasks(period);
CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(date);
CREATE INDEX IF NOT EXISTS idx_tasks_synced_at ON tasks(synced_at);

-- Таблица для кеша агрегированных данных
CREATE TABLE IF NOT EXISTS aggregations (
    key TEXT PRIMARY KEY,
    data TEXT NOT NULL,  -- JSON
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aggregations_created_at ON aggregations(created_at);

-- Таблица метаданных
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


# ===== Database Manager =====

class DatabaseManager:
    """Менеджер работы с SQLite базой данных"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Контекст менеджер для соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> bool:
        """Инициализация базы данных (создание таблиц)"""
        logger.info(f"Инициализация БД: {self.db_path}")

        try:
            with self.get_connection() as conn:
                conn.executescript(SCHEMA_SQL)

                # Устанавливаем метаданные
                self.set_metadata("db_version", "1.0")
                self.set_metadata("form_id", str(PYRUS_FORM_ID))
                self.set_metadata("last_sync", "")

                logger.info("БД инициализирована успешно")
                return True

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            return False

    def save_task(self, task: QualityTask, form_id: int = PYRUS_FORM_ID) -> bool:
        """Сохранить задачу в БД (INSERT OR REPLACE)"""
        try:
            with self.get_connection() as conn:
                max_score = MAX_SCORES_BY_ORDER_TYPE.get(task.order_type, 14)
                normalized_quality = task.total_score / max_score if task.total_score and max_score > 0 else 0

                conn.execute("""
                    INSERT OR REPLACE INTO tasks (
                        task_id, form_id, created_at, salon, florist, order_type,
                        order_id, date, period, comment, total_score, max_score,
                        normalized_quality,
                        catalog_match, packaging_neatness, strawberry_design,
                        flower_processing, freshness, assembly_technique,
                        film_separation, materials_rules, photo,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id, form_id, task.created_at.isoformat(),
                    task.salon, task.florist, task.order_type,
                    task.order_id, task.date, task.period, task.comment,
                    task.total_score, max_score, normalized_quality,
                    task.scores.get('catalog_match') if task.scores else None,
                    task.scores.get('packaging_neatness') if task.scores else None,
                    task.scores.get('strawberry_design') if task.scores else None,
                    task.scores.get('flower_processing') if task.scores else None,
                    task.scores.get('freshness') if task.scores else None,
                    task.scores.get('assembly_technique') if task.scores else None,
                    task.scores.get('film_separation') if task.scores else None,
                    task.scores.get('materials_rules') if task.scores else None,
                    task.scores.get('photo') if task.scores else None,
                    datetime.now().isoformat()
                ))

                return True

        except Exception as e:
            logger.error(f"Ошибка сохранения задачи {task.task_id}: {e}")
            return False

    def get_tasks(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        salon: Optional[str] = None,
        florist: Optional[str] = None,
        order_type: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Получить задачи с фильтрами"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM tasks WHERE 1=1"
                params = []

                if date_from:
                    query += " AND date >= ?"
                    params.append(date_from)
                if date_to:
                    query += " AND date <= ?"
                    params.append(date_to)
                if salon:
                    query += " AND salon = ?"
                    params.append(salon)
                if florist:
                    query += " AND florist = ?"
                    params.append(florist)
                if order_type:
                    query += " AND order_type = ?"
                    params.append(order_type)
                if period:
                    query += " AND period = ?"
                    params.append(period)

                query += " ORDER BY created_at DESC"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Ошибка получения задач: {e}")
            return []

    def get_all_tasks(self) -> List[Dict]:
        """Получить все задачи"""
        return self.get_tasks()

    def get_task_count(self) -> int:
        """Получить количество задач"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM tasks")
                row = cursor.fetchone()
                return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Ошибка подсчета задач: {e}")
            return 0

    def get_distinct_salons(self) -> List[str]:
        """Получить список уникальных салонов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT salon FROM tasks WHERE salon IS NOT NULL ORDER BY salon")
                return [row["salon"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения салонов: {e}")
            return []

    def get_distinct_florists(self) -> List[str]:
        """Получить список уникальных флористов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT florist FROM tasks WHERE florist IS NOT NULL ORDER BY florist")
                return [row["florist"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения флористов: {e}")
            return []

    def get_distinct_periods(self) -> List[str]:
        """Получить список уникальных периодов (месяц год)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT period FROM tasks WHERE period IS NOT NULL AND period != '' ORDER BY created_at DESC")
                return [row["period"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения периодов: {e}")
            return []

    def get_distinct_months(self) -> List[Dict[str, str]]:
        """Получить список уникальных месяцев с данными

        Returns:
            List[Dict]: [{'value': 'Июль 2026', 'label': 'Июль 2026'}, ...]
            отсортировано от последнего к первему
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT period, MIN(created_at) as first_date
                    FROM tasks
                    WHERE period IS NOT NULL AND period != ''
                    GROUP BY period
                    ORDER BY first_date DESC
                """)
                periods = [row["period"] for row in cursor.fetchall()]

                # Формируем список с value и label (они одинаковые для этого случая)
                return [{'value': p, 'label': p} for p in periods]
        except Exception as e:
            logger.error(f"Ошибка получения месяцев: {e}")
            return []

    def get_distinct_order_types(self) -> List[str]:
        """Получить список уникальных видов заказов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT order_type FROM tasks WHERE order_type IS NOT NULL ORDER BY order_type")
                return [row["order_type"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения видов заказов: {e}")
            return []

    # ===== Metadata =====

    def set_metadata(self, key: str, value: str) -> bool:
        """Установить метаданные"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO metadata (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, value, datetime.now().isoformat()))
                return True
        except Exception as e:
            logger.error(f"Ошибка установки метаданных {key}: {e}")
            return False

    def get_metadata(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получить метаданные"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                return row["value"] if row else default
        except Exception as e:
            logger.error(f"Ошибка получения метаданных {key}: {e}")
            return default

    def get_last_sync(self) -> Optional[str]:
        """Получить время последней синхронизации"""
        return self.get_metadata("last_sync")

    def set_last_sync(self, timestamp: str) -> bool:
        """Установить время последней синхронизации"""
        return self.set_metadata("last_sync", timestamp)

    # ===== Агрегации (кеширование) =====

    def save_aggregation(self, key: str, data: Any) -> bool:
        """Сохранить агрегацию в кеш (как JSON)"""
        import json
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO aggregations (key, data, created_at)
                    VALUES (?, ?, ?)
                """, (key, json.dumps(data, ensure_ascii=False), datetime.now().isoformat()))
                return True
        except Exception as e:
            logger.error(f"Ошибка сохранения агрегации {key}: {e}")
            return False

    def get_aggregation(self, key: str) -> Optional[Any]:
        """Получить агрегацию из кеша"""
        import json
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data FROM aggregations WHERE key = ?",
                    (key,)
                )
                row = cursor.fetchone()
                return json.loads(row["data"]) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения агрегации {key}: {e}")
            return None

    def clear_aggregations(self) -> bool:
        """Очистить кеш агрегаций"""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM aggregations")
                return True
        except Exception as e:
            logger.error(f"Ошибка очистки агрегаций: {e}")
            return False

    # ===== Очистка данных =====

    def clear_all_tasks(self) -> bool:
        """Удалить все задачи (осторожно!)"""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM tasks")
                logger.warning("Все задачи удалены из БД")
                return True
        except Exception as e:
            logger.error(f"Ошибка удаления задач: {e}")
            return False


# ===== Тестирование =====

if __name__ == "__main__":
    # Пример использования
    db = DatabaseManager()

    # Инициализация
    if db.init_db():
        print("✅ БД инициализирована")

        # Статистика
        print(f"Задач в БД: {db.get_task_count()}")
        print(f"Салонов: {len(db.get_distinct_salons())}")

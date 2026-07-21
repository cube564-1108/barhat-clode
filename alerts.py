"""
Quality Dashboard — Система алертов
Детектирует проблемы и генерирует уведомления
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from models import QUALITY_CRITERIA, MAX_SCORES_BY_ORDER_TYPE
from database import DatabaseManager
from aggregator import DataAggregator


# ===== Логирование =====

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Типы алертов =====

class AlertSeverity(Enum):
    """Критичность алерта"""
    CRITICAL = "critical"  # Требует немедленного внимания
    WARNING = "warning"    # Предупреждение
    INFO = "info"          # Информационный


class AlertType(Enum):
    """Тип алерта"""
    SCORE_DROP = "score_drop"           # Падение среднего балла
    NEW_FLORIST_POOR = "new_florist_poor"  # Новый флорист с низким баллом
    CRITERION_LOW = "criterion_low"     # Критерий с низким баллом
    SALON_CRITICAL = "salon_critical"   # Салон в критическом состоянии


@dataclass
class Alert:
    """Алерт"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    entity: str  # Салон, флорист или критерий
    value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: Optional[datetime] = None
    resolved: bool = False


# ===== Alert Manager =====

class AlertManager:
    """Менеджер алертов"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.aggregator = DataAggregator(db)

    # ===== Пороги =====

    SCORE_DROP_THRESHOLD = 0.15  # 15% падение
    CRITICAL_SCORE_THRESHOLD = 1.0  # Средний балл < 1.0 (нормированный)
    NEW_FLORIST_MIN_TASKS = 3  # Минимум задач для нового флориста
    NEW_FLORIST_MAX_SCORE = 12  # Макс. балл для "плохого" нового флориста (из 14)
    CRITERION_THRESHOLD = 1.0  # Средний балл критерия < 1.0

    def generate_alerts(self, filters: Optional[Dict] = None) -> List[Alert]:
        """Генерирует все алерты

        Returns:
            List[Alert]
        """
        alerts = []

        # 1. Падение среднего балла
        alerts.extend(self._check_score_drop(filters))

        # 2. Новые флористы с низким баллом
        alerts.extend(self._check_new_florists(filters))

        # 3. Критерии с низким баллом
        alerts.extend(self._check_low_criteria(filters))

        # 4. Салоны в критическом состоянии
        alerts.extend(self._check_critical_salons(filters))

        logger.info(f"Сгенерировано {len(alerts)} алертов")
        return alerts

    def _check_score_drop(self, filters: Optional[Dict] = None) -> List[Alert]:
        """Детектирует падение среднего балла >15%"""
        alerts = []

        # Получаем статистику по салонам за весь период
        stats = self.aggregator.get_summary_stats(filters)
        salon_stats = stats.get('salons', {})

        # Для каждого салона считаем тренд
        for salon, data in salon_stats.items():
            # TODO: Добавить сравнение с предыдущим периодом
            # Сейчас это упрощенная версия
            pass

        return alerts

    def _check_new_florists(self, filters: Optional[Dict] = None) -> List[Alert]:
        """Детектирует новых флористов с низким баллом"""
        alerts = []

        if filters is None:
            filters = {}
        """Детектирует новых флористов с низким баллом"""
        alerts = []

        tasks = self.db.get_tasks(
            date_from=filters.get('date_from'),
            date_to=filters.get('date_to'),
            salon=filters.get('salon'),
            florist=filters.get('florist'),
            order_type=filters.get('order_type'),
            period=filters.get('period')
        )

        # Группируем по флористам
        from collections import defaultdict
        florist_tasks = defaultdict(list)

        for task in tasks:
            florist = task.get('florist')
            salon = task.get('salon')
            if florist and salon:
                key = f"{salon}_{florist}"
                florist_tasks[key].append(task)

        # Проверяем каждого флориста
        for key, tasks_list in florist_tasks.items():
            if len(tasks_list) < self.NEW_FLORIST_MIN_TASKS:
                continue

            salon, florist = key.split('_', 1)

            # Считаем средний балл
            total_scores = [t.get('total_score') or 0 for t in tasks_list]
            avg_score = sum(total_scores) / len(total_scores)

            # Нормируем к 14
            max_scores = [t.get('max_score', 14) for t in tasks_list]
            avg_max = sum(max_scores) / len(max_scores)
            normalized_avg = (avg_score / avg_max) * 14 if avg_max > 0 else avg_score

            if normalized_avg < self.NEW_FLORIST_MAX_SCORE:
                alerts.append(Alert(
                    id=f"new_florist_{key}",
                    type=AlertType.NEW_FLORIST_POOR,
                    severity=AlertSeverity.WARNING,
                    title=f"Новый флорист с низким баллом",
                    description=f"{florist} ({salon}) имеет средний балл {avg_score:.1f} (из {avg_max:.0f}). Рекомендуется обучение.",
                    entity=key,
                    value=avg_score,
                    threshold=self.NEW_FLORIST_MAX_SCORE
                ))

        return alerts

    def _check_low_criteria(self, filters: Optional[Dict] = None) -> List[Alert]:
        """Детектирует критерии с низким средним баллом"""
        alerts = []

        criteria_stats = self.aggregator.get_criteria_stats(filters)

        for crit in criteria_stats:
            avg_score = crit['avg_score']
            max_score = crit['max_score']

            if avg_score < self.CRITERION_THRESHOLD:
                alerts.append(Alert(
                    id=f"criterion_{crit['criterion_key']}",
                    type=AlertType.CRITERION_LOW,
                    severity=AlertSeverity.WARNING,
                    title=f"Низкий балл по критерию: {crit['criterion']}",
                    description=f"Средний балл {avg_score:.1f} из {max_score}. Худший салон: {crit['worst_salon']} ({crit['worst_salon_score']:.1f}).",
                    entity=crit['criterion'],
                    value=avg_score,
                    threshold=self.CRITERION_THRESHOLD
                ))

        return alerts

    def _check_critical_salons(self, filters: Optional[Dict] = None) -> List[Alert]:
        """Детектирует салоны в критическом состоянии"""
        alerts = []

        stats = self.aggregator.get_summary_stats(filters)
        salon_stats = stats.get('salons', {})

        for salon, data in salon_stats.items():
            avg_score = data.get('avg_score', 0)
            count = data.get('count', 0)

            # Нормируем к 14
            # Если есть категории, считаем средний max_score
            if data.get('categories'):
                from models import MAX_SCORES_BY_ORDER_TYPE
                avg_max = sum(
                    MAX_SCORES_BY_ORDER_TYPE.get(c.get('name', ''), 14) * c.get('count', 0)
                    for c in data['categories'].values()
                ) / sum(c.get('count', 0) for c in data['categories'].values())
            else:
                avg_max = 14

            normalized_avg = (avg_score / avg_max) * 14 if avg_max > 0 else avg_score

            # Если средний балл < 12 (из 14) — критично
            if normalized_avg < 12 and count >= 5:
                alerts.append(Alert(
                    id=f"salon_{salon}",
                    type=AlertType.SALON_CRITICAL,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Салон в критическом состоянии",
                    description=f"{salon} имеет средний балл {avg_score:.1f} (из {avg_max:.0f}) по {count} заказам. Требуется вмешательство.",
                    entity=salon,
                    value=avg_score,
                    threshold=12
                ))

        return alerts

    def get_alerts_summary(self, alerts: List[Alert]) -> Dict:
        """Сводка по алертам

        Returns:
            {
                'total': int,
                'critical': int,
                'warning': int,
                'info': int,
                'by_type': Dict[str, int],
            }
        """
        summary = {
            'total': len(alerts),
            'critical': 0,
            'warning': 0,
            'info': 0,
            'by_type': {}
        }

        for alert in alerts:
            # По критичности
            if alert.severity == AlertSeverity.CRITICAL:
                summary['critical'] += 1
            elif alert.severity == AlertSeverity.WARNING:
                summary['warning'] += 1
            else:
                summary['info'] += 1

            # По типу
            type_name = alert.type.value
            summary['by_type'][type_name] = summary['by_type'].get(type_name, 0) + 1

        return summary

    def filter_alerts_by_severity(self, alerts: List[Alert], severity: AlertSeverity) -> List[Alert]:
        """Фильтрует алерты по критичности"""
        return [a for a in alerts if a.severity == severity]


# ===== Тестирование =====

if __name__ == "__main__":
    from database import DatabaseManager

    db = DatabaseManager()
    alert_manager = AlertManager(db)

    alerts = alert_manager.generate_alerts()
    summary = alert_manager.get_alerts_summary(alerts)

    print(f"Всего алертов: {summary['total']}")
    print(f"Критических: {summary['critical']}")
    print(f"Предупреждений: {summary['warning']}")

    for alert in alerts:
        print(f"\n[{alert.severity.value.upper()}] {alert.title}")
        print(f"  {alert.description}")

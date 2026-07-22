"""
Quality Dashboard — Агрегация данных
Вычисляет статистику по салонам, флористам, критериям и т.д.
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from models import (
    SalonStats, FloristStats, CriterionStats, CityStats,
    QUALITY_CRITERIA, MAX_SCORES_BY_ORDER_TYPE, CRITERIA_MAX_SCORES,
    get_quality_status, get_status_emoji, get_status_label, get_status_class,
    get_max_score_for_order_type, get_quality_percentage, extract_city
)
from database import DatabaseManager


# ===== Логирование =====

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Aggregator =====

class DataAggregator:
    """Агрегатор данных из БД"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_summary_stats(self, filters: Optional[Dict] = None) -> Dict:
        """Общая статистика по всем заказам

        Returns:
            {
                'total_orders': int,
                'avg_score': float,
                'perfect_count': int,
                'perfect_percentage': float,
                'cities': Dict[str, CityStats],
                'salons': Dict[str, SalonStats],
                'florists': Dict[str, FloristStats],
            }
        """
        if filters is None:
            filters = {}

        # Получаем задачи с фильтрами
        tasks = self.db.get_tasks(
            date_from=filters.get('date_from'),
            date_to=filters.get('date_to'),
            salon=filters.get('salon'),
            florist=filters.get('florist'),
            order_type=filters.get('order_type'),
            period=filters.get('period')
        )

        if not tasks:
            return {
                'total_orders': 0,
                'avg_score': 0,
                'perfect_count': 0,
                'perfect_percentage': 0,
                'cities': {},
                'salons': {},
                'florists': {},
            }

        # Общая статистика
        total_orders = len(tasks)
        total_score = sum(t.get('total_score') for t in tasks if t.get('total_score') is not None)
        avg_score = round(total_score / total_orders, 2) if total_orders > 0 else 0

        # Идеальные заказы (балл >= 17 для 18-бальных, >= 13 для 14-бальных)
        perfect_count = 0
        for task in tasks:
            max_score = task.get('max_score', 14)
            total = task.get('total_score')
            if total is None:
                continue
            if max_score == 18 and total >= 17:
                perfect_count += 1
            elif max_score == 14 and total >= 13:
                perfect_count += 1

        perfect_percentage = round((perfect_count / total_orders) * 100, 1) if total_orders > 0 else 0

        # Агрегация по салонам
        salons_stats = self._aggregate_by_salons(tasks)

        # Агрегация по флористам
        florists_stats = self._aggregate_by_florists(tasks)

        # Агрегация по городам
        cities_stats = self._aggregate_by_cities(tasks)

        return {
            'total_orders': total_orders,
            'avg_score': avg_score,
            'perfect_count': perfect_count,
            'perfect_percentage': perfect_percentage,
            'cities': cities_stats,
            'salons': salons_stats,
            'florists': florists_stats,
        }

    def _aggregate_by_salons(self, tasks: List[Dict]) -> Dict[str, Dict]:
        """Агрегация по салонам с разделением на категории 14 и 18 баллов"""
        salons_data = defaultdict(lambda: {
            'orders': [],
            'total_score': 0,
            'count': 0,
            'perfect': 0,
            'criteria_sums': defaultdict(int),
            'criteria_counts': defaultdict(int),
            'categories': defaultdict(lambda: {'count': 0, 'total_score': 0}),
            # Разделение по максимальному баллу
            'cat_14': {'total_score': 0, 'count': 0},  # Заказы с max_score = 14
            'cat_18': {'total_score': 0, 'count': 0},  # Заказы с max_score = 18
        })

        for task in tasks:
            salon = task.get('salon')
            if not salon:
                continue

            data = salons_data[salon]
            data['orders'].append(task)
            data['count'] += 1

            total_score = task.get('total_score') or 0
            max_score = task.get('max_score', 14)
            data['total_score'] += total_score

            # Разделение по категориям (14 vs 18 максимальный балл)
            if max_score == 18:
                data['cat_18']['total_score'] += total_score
                data['cat_18']['count'] += 1
            else:
                data['cat_14']['total_score'] += total_score
                data['cat_14']['count'] += 1

            # Идеальные заказы
            if max_score == 18 and total_score >= 17:
                data['perfect'] += 1
            elif max_score == 14 and total_score >= 13:
                data['perfect'] += 1

            # Критерии
            for crit_key in QUALITY_CRITERIA.keys():
                val = task.get(crit_key)
                if val is not None:
                    data['criteria_sums'][crit_key] += val
                    data['criteria_counts'][crit_key] += 1

            # Категории (виды заказов)
            category = task.get('order_type')
            if category:
                data['categories'][category]['count'] += 1
                data['categories'][category]['total_score'] += total_score

        # Формируем итоговую статистику
        result = {}
        for salon, data in salons_data.items():
            avg_score = round(data['total_score'] / data['count'], 2) if data['count'] > 0 else 0

            # Критерии
            criteria_stats = {}
            for crit_key in QUALITY_CRITERIA.keys():
                if data['criteria_counts'][crit_key] > 0:
                    max_val = CRITERIA_MAX_SCORES[crit_key]
                    avg_crit = data['criteria_sums'][crit_key] / data['criteria_counts'][crit_key]
                    criteria_stats[crit_key] = {
                        'name': QUALITY_CRITERIA[crit_key],
                        'current': round(avg_crit, 2),
                        'max': max_val,
                        'gap': round(max_val - avg_crit, 2),
                        'percentage': round((avg_crit / max_val) * 100, 1)
                    }

            # Категории
            categories = {}
            for cat_name, cat_data in data['categories'].items():
                cat_max = MAX_SCORES_BY_ORDER_TYPE.get(cat_name, 14)
                categories[cat_name] = {
                    'name': cat_name,
                    'count': cat_data['count'],
                    'avg_score': round(cat_data['total_score'] / cat_data['count'], 2) if cat_data['count'] > 0 else 0,
                    'max_score': cat_max,
                    'percentage': round((cat_data['total_score'] / cat_data['count'] / cat_max) * 100, 1) if cat_data['count'] > 0 else 0
                }

            # Статус (на основе среднего балла)
            # Нормируем к 14 для консистентности
            normalized_avg = avg_score
            # Если есть разные виды заказов, берем средний max_score
            if data.get('categories'):
                items = list(data['categories'].items())
                if items:
                    avg_max = sum(MAX_SCORES_BY_ORDER_TYPE.get(c, 14) * d.get('count', 0) for c, d in items) / sum(d.get('count', 0) for c, d in items if d.get('count', 0) > 0)
                    normalized_avg = (avg_score / avg_max) * 14 if avg_max > 0 else avg_score

            status = get_quality_status(normalized_avg, 14)

            # Категории по максимальному баллу (14 vs 18)
            cat_14_avg = round(data['cat_14']['total_score'] / data['cat_14']['count'], 2) if data['cat_14']['count'] > 0 else 0
            cat_14_pct = round((cat_14_avg / 14) * 100, 1) if data['cat_14']['count'] > 0 else 0

            cat_18_avg = round(data['cat_18']['total_score'] / data['cat_18']['count'], 2) if data['cat_18']['count'] > 0 else 0
            cat_18_pct = round((cat_18_avg / 18) * 100, 1) if data['cat_18']['count'] > 0 else 0

            result[salon] = {
                'salon': salon,
                'avg_score': avg_score,
                'count': data['count'],
                'perfect': data['perfect'],
                'status': status.value,
                'status_emoji': get_status_emoji(status),
                'status_label': get_status_label(status),
                'status_class': get_status_class(status),
                'criteria': criteria_stats,
                'categories': categories,
                # Категории по максимальному баллу
                'cat_14': {
                    'avg_score': cat_14_avg,
                    'percentage': cat_14_pct,
                    'count': data['cat_14']['count']
                },
                'cat_18': {
                    'avg_score': cat_18_avg,
                    'percentage': cat_18_pct,
                    'count': data['cat_18']['count']
                }
            }

        return result

    def _aggregate_by_florists(self, tasks: List[Dict]) -> Dict[str, Dict]:
        """Агрегация по флористам"""
        florists_data = defaultdict(lambda: {
            'orders': [],
            'total_score': 0,
            'count': 0,
            'perfect': 0,
            'criteria_sums': defaultdict(int),
            'criteria_counts': defaultdict(int),
            'categories': defaultdict(lambda: {'count': 0, 'total_score': 0})
        })

        for task in tasks:
            florist = task.get('florist')
            salon = task.get('salon')
            if not florist or not salon:
                continue

            key = f"{salon}_{florist}"
            data = florists_data[key]
            data['orders'].append(task)
            data['count'] += 1

            total_score = task.get('total_score') or 0
            max_score = task.get('max_score', 14)
            data['total_score'] += total_score

            # Идеальные заказы
            if max_score == 18 and total_score >= 17:
                data['perfect'] += 1
            elif max_score == 14 and total_score >= 13:
                data['perfect'] += 1

            # Критерии
            for crit_key in QUALITY_CRITERIA.keys():
                val = task.get(crit_key)
                if val is not None:
                    data['criteria_sums'][crit_key] += val
                    data['criteria_counts'][crit_key] += 1

            # Категории
            category = task.get('order_type')
            if category:
                data['categories'][category]['count'] += 1
                data['categories'][category]['total_score'] += total_score

        # Формируем итоговую статистику
        result = {}
        for key, data in florists_data.items():
            salon, florist = key.split('_', 1)
            avg_score = round(data['total_score'] / data['count'], 2) if data['count'] > 0 else 0

            # Слабые критерии (топ-3 с наименьшим средним баллом)
            weak_criteria = []
            for crit_key in QUALITY_CRITERIA.keys():
                if data['criteria_counts'][crit_key] > 0:
                    avg_crit = data['criteria_sums'][crit_key] / data['criteria_counts'][crit_key]
                    weak_criteria.append((QUALITY_CRITERIA[crit_key], round(avg_crit, 2)))

            weak_criteria.sort(key=lambda x: x[1])
            weak_criteria = weak_criteria[:3]

            # Категории
            categories = {}
            for cat_name, cat_data in data['categories'].items():
                cat_max = MAX_SCORES_BY_ORDER_TYPE.get(cat_name, 14)
                categories[cat_name] = {
                    'name': cat_name,
                    'count': cat_data['count'],
                    'avg_score': round(cat_data['total_score'] / cat_data['count'], 2) if cat_data['count'] > 0 else 0,
                    'max_score': cat_max,
                    'percentage': round((cat_data['total_score'] / cat_data['count'] / cat_max) * 100, 1) if cat_data['count'] > 0 else 0
                }

            # Статус
            normalized_avg = avg_score
            if data['categories']:
                avg_max = sum(MAX_SCORES_BY_ORDER_TYPE.get(c, 14) * d['count'] for c, d in data['categories'].items()) / sum(d['count'] for d in data['categories'].values())
                normalized_avg = (avg_score / avg_max) * 14 if avg_max > 0 else avg_score

            status = get_quality_status(normalized_avg, 14)

            result[key] = {
                'key': key,
                'florist': florist,
                'salon': salon,
                'avg_score': avg_score,
                'count': data['count'],
                'perfect': data['perfect'],
                'status': status.value,
                'status_emoji': get_status_emoji(status),
                'status_label': get_status_label(status),
                'status_class': get_status_class(status),
                'weak_criteria': weak_criteria,
                'categories': categories
            }

        return result

    def _aggregate_by_cities(self, tasks: List[Dict]) -> Dict[str, Dict]:
        """Агрегация по городам"""
        cities_data = defaultdict(lambda: {'total_score': 0, 'count': 0, 'perfect': 0})

        for task in tasks:
            salon = task.get('salon')
            if not salon:
                continue

            city = extract_city(salon)
            if not city:
                continue

            data = cities_data[city]
            data['count'] += 1

            total_score = task.get('total_score') or 0
            max_score = task.get('max_score', 14)
            data['total_score'] += total_score

            # Идеальные заказы
            if max_score == 18 and total_score >= 17:
                data['perfect'] += 1
            elif max_score == 14 and total_score >= 13:
                data['perfect'] += 1

        # Формируем итоговую статистику
        result = {}
        for city, data in cities_data.items():
            avg_score = round(data['total_score'] / data['count'], 2) if data['count'] > 0 else 0
            result[city] = {
                'city': city,
                'avg_score': avg_score,
                'count': data['count'],
                'perfect': data['perfect'],
            }

        return result

    def get_criteria_stats(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Статистика по критериям (глобально)

        Returns:
            List[Dict] с информацией о каждом критерии
        """
        if filters is None:
            filters = {}

        tasks = self.db.get_tasks(
            date_from=filters.get('date_from'),
            date_to=filters.get('date_to'),
            salon=filters.get('salon'),
            florist=filters.get('florist'),
            order_type=filters.get('order_type'),
            period=filters.get('period')
        )

        # Агрегация по критериям и салонам
        criteria_data = defaultdict(lambda: {
            'total': 0,
            'count': 0,
            'by_salon': defaultdict(lambda: {'total': 0, 'count': 0})
        })

        for task in tasks:
            salon = task.get('salon')
            if not salon:
                continue

            for crit_key, crit_name in QUALITY_CRITERIA.items():
                val = task.get(crit_key)
                if val is not None:
                    criteria_data[crit_key]['total'] += val
                    criteria_data[crit_key]['count'] += 1
                    criteria_data[crit_key]['by_salon'][salon]['total'] += val
                    criteria_data[crit_key]['by_salon'][salon]['count'] += 1

        # Формируем результат
        result = []
        for crit_key, crit_name in QUALITY_CRITERIA.items():
            data = criteria_data.get(crit_key, {})
            if data.get('count', 0) == 0:
                continue

            max_score = CRITERIA_MAX_SCORES[crit_key]
            avg_score = data['total'] / data['count']

            # Находим худший салон
            worst_salon = None
            worst_salon_score = float('inf')

            for salon, salon_data in data['by_salon'].items():
                if salon_data['count'] > 0:
                    salon_avg = salon_data['total'] / salon_data['count']
                    if salon_avg < worst_salon_score:
                        worst_salon_score = salon_avg
                        worst_salon = salon

            result.append({
                'criterion': crit_name,
                'criterion_key': crit_key,
                'avg_score': round(avg_score, 2),
                'max_score': max_score,
                'gap': round(max_score - avg_score, 2),
                'percentage': round((avg_score / max_score) * 100, 1),
                'count': data['count'],
                'worst_salon': worst_salon or '—',
                'worst_salon_score': round(worst_salon_score, 2) if worst_salon_score != float('inf') else 0
            })

        # Сортируем по возрастанию среднего балла (худшие первые)
        result.sort(key=lambda x: x['avg_score'])

        return result

    def get_problem_tasks(self, filters: Optional[Dict] = None, limit_per_salon: int = 5) -> Dict[str, List[Dict]]:
        """Задачи с низким баллом (требуют внимания)

        Returns:
            Dict[str, List[Dict]] — {salon: [tasks]}
        """
        if filters is None:
            filters = {}

        tasks = self.db.get_tasks(
            date_from=filters.get('date_from'),
            date_to=filters.get('date_to'),
            salon=filters.get('salon'),
            florist=filters.get('florist'),
            order_type=filters.get('order_type'),
            period=filters.get('period')
        )

        # Группируем по салонам
        salon_tasks = defaultdict(list)

        for task in tasks:
            total_score = task.get('total_score')
            max_score = task.get('max_score', 14)

            if total_score is None:
                continue

            # Порог для "проблемных" задач
            threshold = 16 if max_score == 18 else 13

            if total_score <= threshold:
                salon_tasks[task.get('salon', 'Неизвестный')].append(task)

        # Сортируем по возрастанию балла (худшие первые) и обрезаем
        result = {}
        for salon, tasks_list in salon_tasks.items():
            sorted_tasks = sorted(tasks_list, key=lambda t: t.get('total_score', 0))
            result[salon] = sorted_tasks[:limit_per_salon]

        return result


# ===== Тестирование =====

if __name__ == "__main__":
    from database import DatabaseManager

    db = DatabaseManager()
    aggregator = DataAggregator(db)

    # Пример использования
    stats = aggregator.get_summary_stats()
    print(f"Всего заказов: {stats['total_orders']}")
    print(f"Средний балл: {stats['avg_score']}")
    print(f"Салонов: {len(stats['salons'])}")

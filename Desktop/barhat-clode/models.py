"""
Quality Dashboard — Константы и типы данных
Pyrus Form ID: 1327961 (Оценка качества сборки букетов)
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum


# ===== Pyrus Form Constants =====

PYRUS_FORM_ID = 1327961

# Критерии оценки (9 шт, шкала 0-2)
# Сопоставление с русскими названиями полей из формы
QUALITY_CRITERIA = {
    'catalog_match': 'Соответствие каталогу',
    'packaging_neatness': 'Аккуратность упаковки',
    'strawberry_design': 'Оформление клубники',
    'flower_processing': 'Обработка цветка',
    'freshness': 'Свежесть компонентов',
    'assembly_technique': 'Техника сборки',
    'film_separation': 'Клубника отделена от цветка прозрачной пленкой',
    'materials_rules': 'Соответствие правилам вложения материалов',
    'photo': 'Фотография',
}

# Максимальные баллы по критериям (каждый по 2 балла)
CRITERIA_MAX_SCORES = {key: 2 for key in QUALITY_CRITERIA.keys()}

# Поля группировки (русские названия из формы Pyrus)
GROUPING_FIELDS = {
    'salon': 'Салон',
    'florist': 'Флорист',
    'order_type': 'Вид заказа',
    'order_id': 'Номер заказа',
    'date': 'ДАТА',
    'period': 'период',
    'comment': 'Комментарии',
}

# ===== Нормировка качества по видам заказов =====

MAX_SCORES_BY_ORDER_TYPE: Dict[str, int] = {
    "Клубничный букет": 14,
    "Цветочный букет": 14,
    "Коробочка с клубникой или бананами": 14,
    "Клубнично-цветочный букет": 18,
    "Цветочный бокс": 14,
    "Коробочка+цветочный букет": 18,
    "Клубничный бокс": 14,
    "Цветочно-клубничный бокс": 18,
}


# ===== Статусы качества =====

class QualityStatus(Enum):
    """Статус качества на основе среднего балла"""
    EXCELLENT = "excellent"  # >= 1.3 (>= 13/14 или >= 17/18)
    GOOD = "good"            # 1.0 - 1.3
    POOR = "poor"            # < 1.0


def get_quality_status(score: float, max_score: int) -> QualityStatus:
    """Определить статус качества по среднему баллу

    Args:
        score: Средний балл
        max_score: Максимальный балл для вида заказа (14 или 18)

    Returns:
        QualityStatus
    """
    # Нормируем к шкале 14 (традиционно для большинства видов)
    normalized = (score / max_score) * 14

    if normalized >= 13:
        return QualityStatus.EXCELLENT
    elif normalized >= 12:
        return QualityStatus.GOOD
    else:
        return QualityStatus.POOR


def get_status_emoji(status: QualityStatus) -> str:
    """Эмодзи для статуса"""
    return {
        QualityStatus.EXCELLENT: "🟢",
        QualityStatus.GOOD: "🟡",
        QualityStatus.POOR: "🔴",
    }[status]


def get_status_label(status: QualityStatus) -> str:
    """Русский label для статуса"""
    return {
        QualityStatus.EXCELLENT: "Отлично",
        QualityStatus.GOOD: "Хорошо",
        QualityStatus.POOR: "Внимание",
    }[status]


def get_status_class(status: QualityStatus) -> str:
    """CSS класс для статуса"""
    return {
        QualityStatus.EXCELLENT: "badge-good",
        QualityStatus.GOOD: "badge-avg",
        QualityStatus.POOR: "badge-bad",
    }[status]


# ===== Модели данных =====

@dataclass
class QualityTask:
    """Задача оценки качества из Pyrus"""
    task_id: int
    created_at: datetime
    salon: str
    florist: str
    order_type: str
    order_id: Optional[str] = None
    date: Optional[str] = None
    period: Optional[str] = None
    scores: Optional[Dict[str, Optional[int]]] = None  # criterion_key -> score (0-2)
    total_score: Optional[int] = None
    comment: Optional[str] = None

    def __post_init__(self):
        if self.scores is None:
            self.scores = {}


@dataclass
class SalonStats:
    """Статистика по салону"""
    salon: str
    avg_score: float
    avg_quality: float  # 0-1
    count: int
    perfect_count: int
    status: QualityStatus
    # Статистика по критериям
    criteria_stats: Dict[str, Dict]  # criterion_key -> {avg, max, gap, percentage}
    # Статистика по видам заказов
    categories: Dict[str, Dict]  # category_name -> {count, avg_score, max_score, percentage}


@dataclass
class FloristStats:
    """Статистика по флористу"""
    florist: str
    salon: str
    avg_score: float
    avg_quality: float  # 0-1
    count: int
    perfect_count: int
    status: QualityStatus
    weak_criteria: List[tuple[str, float]]  # [(criterion_name, avg_score)]
    # Статистика по видам заказов
    categories: Dict[str, Dict]


@dataclass
class CriterionStats:
    """Статистика по критерию"""
    criterion: str
    criterion_key: str
    avg_score: float
    max_score: int
    gap: float
    percentage: float
    worst_salon: str
    worst_salon_score: float


@dataclass
class CityStats:
    """Статистика по городу"""
    city: str
    avg_score: float
    count: int
    perfect_count: int


# ===== Функции нормировки =====

def normalize_score(raw_score: int, order_type: str) -> float:
    """Нормирует сырой балл к шкале 0-1

    Args:
        raw_score: Сумма баллов по критериям
        order_type: Вид заказа

    Returns:
        float: 0-1, где 1 = идеальное качество
    """
    max_score = MAX_SCORES_BY_ORDER_TYPE.get(order_type, 14)
    return raw_score / max_score if max_score > 0 else 0


def get_max_score_for_order_type(order_type: str) -> int:
    """Получить максимальный балл для вида заказа"""
    return MAX_SCORES_BY_ORDER_TYPE.get(order_type, 14)


def get_quality_percentage(score: int, order_type: str) -> float:
    """Получить качество в процентах"""
    max_score = get_max_score_for_order_type(order_type)
    return round((score / max_score) * 100, 1) if max_score > 0 else 0


# ===== Город из названия салона =====

def extract_city(salon_name: str) -> str:
    """Извлекает город из названия салона

    Примеры:
        'ЕКБ ТЦ Гринвич' -> 'Екатеринбург'
        'БРН ТЦ Москва' -> 'Брянск'
        'ЧЛБ ТЦ Манеж' -> 'Челябинск'
    """
    if not salon_name:
        return ""

    # Разбиваем название
    parts = salon_name.strip().split()
    if not parts:
        return ""

    city_code = parts[0]

    city_mapping = {
        'ЕКБ': 'Екатеринбург',
        'БРН': 'Брянск',
        'ЧЛБ': 'Челябинск',
        'Челябинск': 'Челябинск',
        'НСК': 'Новосибирск',
        'Томск': 'Томск',
        'СПБ': 'Санкт-Петербург',
        'МСК': 'Москва',
    }

    return city_mapping.get(city_code, city_code)


# ===== Period parsing =====

def parse_period_sort(period_str: str) -> int:
    """Парсит период формата 'ММ.ГГГГ' в число для сортировки.

    Например: '07.2026' -> 202607 (можно сортировать как число)
    Возвращает 0 для пустых/некорректных периодов (они будут в конце).
    """
    if not period_str:
        return 0
    try:
        parts = period_str.split('.')
        if len(parts) == 2:
            year = int(parts[1])
            month = int(parts[0])
            return year * 100 + month
    except:
        pass
    return 0


def format_period_display(period_str: str) -> str:
    """Форматирует период для отображения

    '07.2026' -> 'июл.26'
    """
    if not period_str:
        return period_str

    try:
        parts = period_str.split('.')
        if len(parts) == 2:
            month = int(parts[0])
            year = int(parts[1])

            month_names = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн',
                          'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

            return f"{month_names[month]}.{str(year)[-2:]}"
    except:
        pass

    return period_str

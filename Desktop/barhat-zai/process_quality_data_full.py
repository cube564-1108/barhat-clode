#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт с полной фильтрацией по периоду:
- При выборе периода пересчитывается ВСЯ статистика
- Средние оценки, количества, проценты - всё обновляется
"""

import csv
import json
from collections import defaultdict

CSV_FILE = r"C:\Users\Станислав\Downloads\Отчет по качеству сборки букетов - Export.csv"
OUTPUT_FILE = r"c:\Users\Станислав\Desktop\barhat-zai\florist-quality-dashboard.html"

CRITERIA_MAX = {
    'catalog_match': 2,
    'packaging_neatness': 2,
    'strawberry_design': 2,
    'flower_processing': 2,
    'assembly_technique': 2,
    'film_separation': 2,
    'materials_rules': 2,
    'photo': 2,
    'freshness': 2
}

CATEGORY_MAX = {
    'Клубничный букет': 14,
    'Цветочный букет': 14,
    'Коробочка с клубникой или бананами': 14,
    'Клубнично-цветочный букет': 18,
    'Цветочный бокс': 18,
    'Коробочка+цветочный букет': 14,
    'Клубничный бокс': 14,
    'Цветочно-клубничный бокс': 18
}

CRITERIA_NAMES = {
    'catalog_match': 'Соответствие каталогу',
    'packaging_neatness': 'Аккуратность упаковки',
    'strawberry_design': 'Оформление клубники',
    'flower_processing': 'Обработка цветка',
    'assembly_technique': 'Техника сборки',
    'film_separation': 'Разделение пленкой',
    'materials_rules': 'Вложение материалов',
    'photo': 'Фотография',
    'freshness': 'Свежесть'
}

def parse_csv():
    data = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                if not row.get('Номер заказа'):
                    continue
                period = row.get('период', '')
                record = {
                    'city': '',
                    'period': period,
                    'period_sort': parse_period_sort(period),  # Для корректной сортировки
                    'date': row.get('ДАТА', ''),
                    'salon': row.get('Салон', ''),
                    'florist': row.get('Флорист', '').strip(),
                    'order_id': row.get('Номер заказа', ''),
                    'product_type': row.get('Вид заказа', ''),
                    'total_score': safe_int(row.get('Итоговая оценка')),
                    'catalog_match': safe_int(row.get('Соответствие каталогу')),
                    'packaging_neatness': safe_int(row.get('Аккуратность упаковки')),
                    'strawberry_design': safe_int(row.get('Оформление клубники')),
                    'flower_processing': safe_int(row.get('Обработка цветка')),
                    'assembly_technique': safe_int(row.get('Техника сборки')),
                    'film_separation': safe_int(row.get('Клубника отделена от цветка прозрачной пленкой')),
                    'materials_rules': safe_int(row.get('Соответствие правилам вложения материалов')),
                    'photo': safe_int(row.get('Фотография')),
                    'freshness': safe_int(row.get('Свежесть компонентов')),
                    'comment': row.get('Комментарии', '')
                }
                if record['salon']:
                    salon_parts = record['salon'].split()
                    if salon_parts:
                        city_code = salon_parts[0]
                        city_mapping = {
                            'ЕКБ': 'Екатеринбург',
                            'БРН': 'Брянск',
                            'ЧЛБ': 'Челябинск',
                            'Челябинск': 'Челябинск',
                            'НСК': 'Новосибирск',
                            'Томск': 'Томск'
                        }
                        record['city'] = city_mapping.get(city_code, city_code)
                data.append(record)
            except:
                continue
    return data


def parse_period_sort(period_str: str) -> int:
    """
    Парсит период формата 'ММ.ГГГГ' в число для сортировки.
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

def safe_int(value):
    if value is None or value == '':
        return None
    try:
        return int(float(str(value).strip()))
    except:
        return None

def prepare_data_for_js(data):
    """Подготавливает данные для JavaScript фильтрации"""
    orders = []
    periods_dict = {}  # period -> period_sort

    for record in data:
        period = record.get('period')
        if period:
            periods_dict[period] = record.get('period_sort', 0)

        orders.append({
            'task_id': record.get('task_id', ''),  # ID задачи Pyrus для ссылки
            'city': record['city'],
            'period': period,
            'period_sort': record.get('period_sort', 0),
            'salon': record['salon'],
            'florist': record['florist'],
            'product_type': record['product_type'],
            'total_score': record['total_score'],
            'catalog_match': record['catalog_match'],
            'packaging_neatness': record['packaging_neatness'],
            'strawberry_design': record['strawberry_design'],
            'flower_processing': record['flower_processing'],
            'assembly_technique': record['assembly_technique'],
            'film_separation': record['film_separation'],
            'materials_rules': record['materials_rules'],
            'photo': record['photo'],
            'freshness': record['freshness']
        })

    # Сортируем периоды по убыванию (от нового к старому)
    sorted_periods = sorted(periods_dict.keys(), key=lambda p: periods_dict[p], reverse=True)
    return orders, sorted_periods

def calculate_stats_from_orders(orders):
    """Вычисляет статистику из списка заказов"""
    if not orders:
        return {
            'total_orders': 0,
            'avg_score': 0,
            'perfect_count': 0,
            'cities': {},
            'salons': {},
            'florists': {}
        }

    total_score = sum(o['total_score'] for o in orders if o['total_score'])
    total_orders = len(orders)
    avg_score = total_score / total_orders if total_orders > 0 else 0
    perfect_count = sum(1 for o in orders if o['total_score'] and o['total_score'] >= 17)

    # Группировка по городам
    cities = {}
    for order in orders:
        city = order['city']
        if not city:
            continue
        if city not in cities:
            cities[city] = {'orders': [], 'total_score': 0, 'count': 0, 'perfect': 0}
        cities[city]['orders'].append(order)
        cities[city]['count'] += 1
        if order['total_score']:
            cities[city]['total_score'] += order['total_score']
            if order['total_score'] >= 17:
                cities[city]['perfect'] += 1

    city_stats = {}
    for city, data in cities.items():
        city_stats[city] = {
            'avg_score': round(data['total_score'] / data['count'], 1) if data['count'] > 0 else 0,
            'count': data['count'],
            'perfect': data['perfect']
        }

    # Группировка по салонам
    salons = {}
    for order in orders:
        salon = order['salon']
        if not salon:
            continue
        if salon not in salons:
            salons[salon] = {'orders': [], 'total_score': 0, 'count': 0, 'perfect': 0,
                            'criteria_sums': defaultdict(int), 'criteria_counts': defaultdict(int),
                            'categories': defaultdict(lambda: {'count': 0, 'total_score': 0})}
        salons[salon]['orders'].append(order)
        salons[salon]['count'] += 1
        if order['total_score']:
            salons[salon]['total_score'] += order['total_score']
            if order['total_score'] >= 17:
                salons[salon]['perfect'] += 1

        # Критерии
        for crit in CRITERIA_MAX.keys():
            val = order.get(crit)
            if val is not None:
                salons[salon]['criteria_sums'][crit] += val
                salons[salon]['criteria_counts'][crit] += 1

        # Категории
        cat = order['product_type']
        if cat:
            salons[salon]['categories'][cat]['count'] += 1
            if order['total_score']:
                salons[salon]['categories'][cat]['total_score'] += order['total_score']

    salon_stats = {}
    for salon, data in salons.items():
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0

        # Критерии
        criteria = {}
        for crit in CRITERIA_MAX.keys():
            if data['criteria_counts'][crit] > 0:
                max_val = CRITERIA_MAX[crit]
                avg_crit = data['criteria_sums'][crit] / data['criteria_counts'][crit]
                criteria[crit] = {
                    'current': round(avg_crit, 1),
                    'max': max_val,
                    'gap': round(max_val - avg_crit, 1),
                    'percentage': round((avg_crit / max_val) * 100, 0)
                }

        # Категории
        categories = {}
        for cat_name, cat_data in data['categories'].items():
            cat_max = CATEGORY_MAX.get(cat_name, 18)
            categories[cat_name] = {
                'count': cat_data['count'],
                'avg_score': round(cat_data['total_score'] / cat_data['count'], 1) if cat_data['count'] > 0 else 0,
                'max_score': cat_max,
                'percentage': round((cat_data['total_score'] / cat_data['count'] / cat_max) * 100, 0) if cat_data['count'] > 0 else 0
            }

        salon_stats[salon] = {
            'avg_score': round(avg, 1),
            'count': data['count'],
            'perfect': data['perfect'],
            'criteria': criteria,
            'categories': categories
        }

    # Группировка по флористам
    florists = {}
    for order in orders:
        florist = order['florist']
        if not florist:
            continue
        key = f"{order['salon']}_{florist}"
        if key not in florists:
            florists[key] = {'orders': [], 'total_score': 0, 'count': 0, 'perfect': 0,
                            'criteria_sums': defaultdict(int), 'criteria_counts': defaultdict(int),
                            'categories': defaultdict(lambda: {'count': 0, 'total_score': 0})}
        florists[key]['orders'].append(order)
        florists[key]['count'] += 1
        if order['total_score']:
            florists[key]['total_score'] += order['total_score']
            if order['total_score'] >= 17:
                florists[key]['perfect'] += 1

        # Критерии
        for crit in CRITERIA_MAX.keys():
            val = order.get(crit)
            if val is not None:
                florists[key]['criteria_sums'][crit] += val
                florists[key]['criteria_counts'][crit] += 1

        # Категории
        cat = order['product_type']
        if cat:
            florists[key]['categories'][cat]['count'] += 1
            if order['total_score']:
                florists[key]['categories'][cat]['total_score'] += order['total_score']

    florist_stats = {}
    for key, data in florists.items():
        florist_name = key.split('_', 1)[1] if '_' in key else key
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0

        # Критерии
        criteria = {}
        for crit in CRITERIA_MAX.keys():
            if data['criteria_counts'][crit] > 0:
                max_val = CRITERIA_MAX[crit]
                avg_crit = data['criteria_sums'][crit] / data['criteria_counts'][crit]
                criteria[crit] = {
                    'percentage': round((avg_crit / max_val) * 100, 0)
                }

        # Категории
        categories = {}
        for cat_name, cat_data in data['categories'].items():
            cat_max = CATEGORY_MAX.get(cat_name, 18)
            categories[cat_name] = {
                'count': cat_data['count'],
                'avg_score': round(cat_data['total_score'] / cat_data['count'], 1) if cat_data['count'] > 0 else 0,
                'max_score': cat_max,
                'percentage': round((cat_data['total_score'] / cat_data['count'] / cat_max) * 100, 0) if cat_data['count'] > 0 else 0
            }

        florist_stats[key] = {
            'name': florist_name,
            'salon': key.split('_')[0] if '_' in key else '',
            'avg_score': round(avg, 1),
            'count': data['count'],
            'perfect': data['perfect'],
            'criteria': criteria,
            'categories': categories
        }

    return {
        'total_orders': total_orders,
        'avg_score': round(avg_score, 2),
        'perfect_count': perfect_count,
        'perfect_percentage': round((perfect_count / total_orders) * 100, 1) if total_orders > 0 else 0,
        'cities': city_stats,
        'salons': salon_stats,
        'florists': florist_stats
    }

def generate_html(data, periods):
    """Генерирует HTML с полными данными для JavaScript фильтрации"""
    orders, period_list = prepare_data_for_js(data)

    # Общая статистика
    total_stats = calculate_stats_from_orders(orders)

    cities = sorted(total_stats['cities'].keys())

    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет по качеству сборки букетов</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }}

        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .filters {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .filter-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .filter-group label {{
            font-weight: 600;
            color: #666;
        }}

        .filter-select {{
            padding: 10px 15px;
            border: 2px solid #667eea;
            border-radius: 10px;
            font-size: 14px;
            background: white;
            color: #333;
            cursor: pointer;
            min-width: 150px;
        }}

        .kpi-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .kpi-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}

        .kpi-card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}

        .kpi-card .value {{
            font-size: 2.5em;
            font-weight: bold;
        }}

        .city-nav {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .city-btn {{
            padding: 12px 24px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }}

        .city-btn.active, .city-btn:hover {{
            background: #667eea;
            color: white;
        }}

        .salon-nav {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .salon-btn {{
            padding: 10px 20px;
            border: 2px solid #764ba2;
            background: white;
            color: #764ba2;
            border-radius: 20px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }}

        .salon-btn.active, .salon-btn:hover {{
            background: #764ba2;
            color: white;
        }}

        .salon-section {{
            display: none;
            margin-bottom: 40px;
        }}

        .salon-section.active {{
            display: block;
        }}

        .salons-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .salon-card {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            border: 2px solid #e0e0e0;
        }}

        .salon-card .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .salon-card .name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}

        .badge {{
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 600;
        }}

        .badge-good {{ background: #d4edda; color: #155724; }}
        .badge-avg {{ background: #fff3cd; color: #856404; }}
        .badge-bad {{ background: #f8d7da; color: #721c24; }}

        .score-big {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            margin: 15px 0;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }}

        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }}

        .categories-list {{
            margin-top: 15px;
        }}

        .category-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            font-size: 0.9em;
        }}

        .florist-card {{
            background: white;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
        }}

        .florist-card .name {{
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }}

        .insights {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
            font-size: 0.85em;
        }}

        .insights ul {{
            list-style: none;
        }}

        .insights li {{
            padding: 3px 0;
        }}

        .insight-strong {{ color: #27ae60; }}
        .insight-weak {{ color: #e74c3c; }}

        /* Кликабельные карточки салонов */
        .salon-card {{
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .salon-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }}

        /* Индикатор тренда */
        .trend-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-top: 10px;
        }}
        .trend-improving {{
            background: #d4edda;
            color: #155724;
        }}
        .trend-worsening {{
            background: #f8d7da;
            color: #721c24;
        }}
        .trend-stable {{
            background: #fff3cd;
            color: #856404;
        }}
        .trend-arrow {{
            font-size: 1.2em;
        }}

        /* Модальное окно */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal.active {{
            display: flex;
        }}
        .modal-content {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 900px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        }}
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: #f0f0f0;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}
        .modal-close:hover {{
            background: #e0e0e0;
        }}
        .modal-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .modal-subtitle {{
            color: #666;
            margin-bottom: 30px;
        }}

        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8em; }}
            .kpi-cards {{ grid-template-columns: 1fr; }}
            .salons-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Отчет по качеству сборки букетов</h1>
            <p>Всего заказов: <span id="totalOrders">{total_stats['total_orders']:,}</span></p>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label for="periodSelect">Период:</label>
                <select id="periodSelect" class="filter-select">
                    <option value="all">Все периоды</option>
'''

    for period in period_list:
        html += f'                    <option value="{period}">{period}</option>\n'

    html += '                </select>\n'
    html += '            </div>\n'
    html += '        </div>\n\n'

    html += '        <div class="kpi-cards">\n'
    html += f'            <div class="kpi-card">\n'
    html += f'                <h3>Средняя оценка</h3>\n'
    html += f'                <div class="value" id="avgScore">{total_stats["avg_score"]}</div>\n'
    html += f'                <div>из 18</div>\n'
    html += f'            </div>\n'
    html += f'            <div class="kpi-card">\n'
    html += f'                <h3>Эталонных работ</h3>\n'
    html += f'                <div class="value" id="perfectCount">{total_stats["perfect_count"]}</div>\n'
    html += f'                <div>(<span id="perfectPercent">{total_stats["perfect_percentage"]}</span>%)</div>\n'
    html += f'            </div>\n'
    html += f'            <div class="kpi-card">\n'
    html += f'                <h3>Городов</h3>\n'
    html += f'                <div class="value">{len(cities)}</div>\n'
    html += f'                <div>в аналитике</div>\n'
    html += f'            </div>\n'
    html += '        </div>\n\n'

    # Таблица среднего рейтинга салонов
    html += '''        <!-- Таблица среднего рейтинга салонов -->
        <div class="chart-section" style="margin: 30px 0; padding: 30px; background: #f8f9fa; border-radius: 15px;">
            <h2 style="margin-bottom: 20px; color: #667eea;">📊 Рейтинг салонов за период</h2>
            <div id="salonRatingTable" style="overflow-x: auto;">
                <!-- Таблица генерируется через JavaScript -->
            </div>
        </div>\n\n'''

    html += '        <h2 style="margin-bottom: 20px; color: #333;">📊 Качество по салонам</h2>\n'
    html += '        <div class="salons-grid" id="salonsContainer">\n'

    # Генерация карточек салонов
    sorted_salons = sorted(total_stats['salons'].items(),
                          key=lambda x: x[1]['avg_score'], reverse=True)

    for salon, salon_data in sorted_salons:
        badge_class = 'badge-good' if salon_data['avg_score'] >= 14 else 'badge-avg' if salon_data['avg_score'] >= 12 else 'badge-bad'
        badge_text = 'Отлично' if salon_data['avg_score'] >= 14 else 'Хорошо' if salon_data['avg_score'] >= 12 else 'Внимание'

        html += f'            <div class="salon-card" id="salon-{salon.replace(" ", "-")}" onclick="openSalonModal(\'{salon}\')">\n'
        html += f'                <div class="header">\n'
        html += f'                    <div class="name">{salon} 📊</div>\n'
        html += f'                    <span class="badge {badge_class}">{badge_text}</span>\n'
        html += f'                </div>\n'
        html += f'                <div class="score-big" id="score-{salon.replace(" ", "-")}">{salon_data["avg_score"]}</div>\n'
        # Индикатор тренда (пока пустой, заполнится в JavaScript)
        html += f'                <div class="trend-indicator" id="trend-{salon.replace(" ", "-")}">Загрузка...</div>\n'
        html += f'                <div class="metrics">\n'
        html += f'                    <div class="metric">\n'
        html += f'                        <span>Заказов:</span>\n'
        html += f'                        <span><strong id="count-{salon.replace(" ", "-")}">{salon_data["count"]}</strong></span>\n'
        html += f'                    </div>\n'
        html += f'                    <div class="metric">\n'
        html += f'                        <span>Эталонных:</span>\n'
        html += f'                        <span><strong id="perfect-{salon.replace(" ", "-")}">{salon_data["perfect"]}</strong></span>\n'
        html += f'                    </div>\n'
        html += f'                </div>\n'

        # Категории
        if salon_data['categories']:
            html += f'                <div class="categories-list">\n'
            html += f'                    <strong>Категории:</strong><br>\n'
            for cat_name, cat_data in sorted(salon_data['categories'].items(),
                                             key=lambda x: x[1]['avg_score'], reverse=True):
                max_val = cat_data['max_score']
                html += f'                    <div class="category-item">\n'
                html += f'                        <span>{cat_name}:</span>\n'
                html += f'                        <span><strong>{cat_data["avg_score"]}/{max_val}</strong> ({cat_data["percentage"]}%)</span>\n'
                html += f'                    </div>\n'
            html += f'                </div>\n'

        # Флористы салона
        salon_florists = {k: v for k, v in total_stats['florists'].items()
                          if v['salon'] == salon}
        if salon_florists:
            html += f'                <h4 style="margin-top: 20px; margin-bottom: 15px; color: #667eea;">Флористы:</h4>\n'
            for f_key, f_data in sorted(salon_florists.items(),
                                  key=lambda x: x[1]['avg_score'], reverse=True):
                html += f'                <div class="florist-card">\n'
                html += f'                    <div class="name">{f_data["name"]}: {f_data["avg_score"]} ({f_data["count"]} зак.)</div>\n'

                # Выводы по флористу
                strong = []
                weak = []
                for crit_id, crit_data in f_data['criteria'].items():
                    crit_name = CRITERIA_NAMES.get(crit_id, crit_id)
                    if crit_data['percentage'] >= 90:
                        strong.append(crit_name)
                    elif crit_data['percentage'] < 70:
                        weak.append(crit_name)

                if strong or weak:
                    html += f'                    <div class="insights">\n'
                    if strong:
                        html += f'                        <ul><span class="insight-strong">✅</span> {", ".join(strong)}</ul>\n'
                    if weak:
                        html += f'                        <ul><span class="insight-weak">⚠️</span> {", ".join(weak)}</ul>\n'
                    html += f'                    </div>\n'

                html += f'                </div>\n'

        html += f'            </div>\n'

    html += '        </div>\n\n'

    # Модальное окно для детального графика салона
    html += '''        <!-- Модальное окно для детального графика салона -->
        <div class="modal" id="salonModal">
            <div class="modal-content">
                <button class="modal-close" onclick="closeSalonModal()">&times;</button>
                <h2 class="modal-title" id="modalTitle">Детальный график</h2>
                <p class="modal-subtitle" id="modalSubtitle">Динамика за последние 6 месяцев</p>
                <div style="position: relative; height: 400px;">
                    <canvas id="salonDetailChart"></canvas>
                </div>
            </div>
        </div>\n\n'''

    html += '''        <!-- Проблемные задачи по салонам -->
        <div class="chart-section" style="margin: 30px 0; padding: 30px; background: #fff8e1; border-radius: 15px;">
            <h2 style="margin-bottom: 20px; color: #f57c00;">⚠️ Задачи с низким баллом (требуют внимания)</h2>
            <p style="color: #666; margin-bottom: 20px;">Показаны задачи с баллом ≤13 (max=14) или ≤16 (max=18) за выбранный период</p>
            <div id="problemTasks" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                <!-- Проблемные задачи генерируются через JavaScript -->
            </div>
        </div>
'''

    html += '''    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Все данные заказов
        const allOrders = ''' + json.dumps(orders, ensure_ascii=False) + ''';

        // Названия критериев
        const CRITERIA_NAMES = ''' + json.dumps(CRITERIA_NAMES, ensure_ascii=False) + ''';

        // Максимальные баллы категорий
        const CATEGORY_MAX = ''' + json.dumps(CATEGORY_MAX, ensure_ascii=False) + ''';

        // Глобальная переменная для детального графика
        let detailChart = null;

        // Вспомогательная функция для сортировки периодов (от нового к старому)
        function sortPeriods(periods) {
            return periods.sort((a, b) => {
                // Парсим период формата 'ММ.ГГГГ'
                const [aMonth, aYear] = a.split('.').map(Number);
                const [bMonth, bYear] = b.split('.').map(Number);

                // Сортируем по годам, затем по месяцам (по убыванию)
                if (aYear !== bYear) {
                    return bYear - aYear; // Сначала более новые годы
                }
                return bMonth - aMonth; // В рамках года - более новые месяцы
            });
        }

        // Получаем числовое значение периода для сортировки
        function getPeriodSortValue(period) {
            const parts = period.split('.');
            if (parts.length === 2) {
                const year = parseInt(parts[1]);
                const month = parseInt(parts[0]);
                return year * 100 + month;
            }
            return 0;
        }

        function calculateStats(orders) {
            if (!orders || orders.length === 0) {
                return {
                    total_orders: 0,
                    avg_score: 0,
                    perfect_count: 0,
                    perfect_percentage: 0,
                    salons: {}
                };
            }

            const totalScore = orders.reduce((sum, o) => sum + (o.total_score || 0), 0);
            const totalOrders = orders.length;
            const avgScore = totalScore / totalOrders;
            const perfectCount = orders.filter(o => o.total_score >= 17).length;

            // Группировка по салонам
            const salons = {};
            const florists = {};

            orders.forEach(order => {
                if (!order.salon) return;

                if (!salons[order.salon]) {
                    salons[order.salon] = { orders: [], totalScore: 0, count: 0, perfect: 0 };
                }
                salons[order.salon].orders.push(order);
                salons[order.salon].count++;
                salons[order.salon].totalScore += order.total_score || 0;
                if (order.total_score >= 17) salons[order.salon].perfect++;

                // Флористы
                if (order.florist) {
                    const key = order.salon + '_' + order.florist;
                    if (!florists[key]) {
                        florists[key] = { orders: [], totalScore: 0, count: 0, perfect: 0 };
                    }
                    florists[key].orders.push(order);
                    florists[key].count++;
                    florists[key].totalScore += order.total_score || 0;
                    if (order.total_score >= 17) florists[key].perfect++;
                }
            });

            const salonStats = {};
            for (const [salon, data] of Object.entries(salons)) {
                salonStats[salon] = {
                    avg_score: Math.round(data.totalScore / data.count * 10) / 10,
                    count: data.count,
                    perfect: data.perfect
                };
            }

            return {
                total_orders: totalOrders,
                avg_score: Math.round(avgScore * 100) / 100,
                perfect_count: perfectCount,
                perfect_percentage: Math.round((perfectCount / totalOrders) * 1000) / 10,
                salons: salonStats,
                florists: florists
            };
        }

        function updateUI(stats) {
            // Обновляем KPI карточки
            document.getElementById('totalOrders').textContent = stats.total_orders.toLocaleString();
            document.getElementById('avgScore').textContent = stats.avg_score;
            document.getElementById('perfectCount').textContent = stats.perfect_count;
            document.getElementById('perfectPercent').textContent = stats.perfect_percentage;

            // Получаем все карточки салонов
            const allCards = document.querySelectorAll('.salon-card');
            const salonIdsInStats = new Set(Object.keys(stats.salons).map(s => s.replace(/ /g, '-')));

            // Скрываем или показываем карточки в зависимости от наличия данных
            allCards.forEach(card => {
                const cardId = card.id.replace('salon-', '');
                const hasData = salonIdsInStats.has(cardId);

                if (hasData) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });

            // Обновляем карточки салонов только для тех, у кого есть данные
            for (const [salon, data] of Object.entries(stats.salons)) {
                const salonId = salon.replace(/ /g, '-');
                const scoreEl = document.getElementById('score-' + salonId);
                const countEl = document.getElementById('count-' + salonId);
                const perfectEl = document.getElementById('perfect-' + salonId);

                if (scoreEl) scoreEl.textContent = data.avg_score;
                if (countEl) countEl.textContent = data.count;
                if (perfectEl) perfectEl.textContent = data.perfect;

                // Обновляем бейдж
                const card = document.getElementById('salon-' + salonId);
                if (card) {
                    const badge = card.querySelector('.badge');
                    if (badge) {
                        badge.className = 'badge';
                        if (data.avg_score >= 14) {
                            badge.classList.add('badge-good');
                            badge.textContent = 'Отлично';
                        } else if (data.avg_score >= 12) {
                            badge.classList.add('badge-avg');
                            badge.textContent = 'Хорошо';
                        } else {
                            badge.classList.add('badge-bad');
                            badge.textContent = 'Внимание';
                        }
                    }
                }
            }
        }

        // Функция расчёта и обновления трендов
        function updateTrends(orders) {
            // Группируем данные по салонам и периодам
            const salonPeriodData = {};

            orders.forEach(order => {
                if (!order.salon || !order.period) return;

                if (!salonPeriodData[order.salon]) {
                    salonPeriodData[order.salon] = {};
                }
                if (!salonPeriodData[order.salon][order.period]) {
                    salonPeriodData[order.salon][order.period] = { total: 0, count: 0 };
                }
                salonPeriodData[order.salon][order.period].total += order.total_score || 0;
                salonPeriodData[order.salon][order.period].count++;
            });

            // Для каждого салона считаем тренд
            for (const [salon, periodData] of Object.entries(salonPeriodData)) {
                const salonId = salon.replace(/ /g, '-');
                const trendEl = document.getElementById('trend-' + salonId);
                if (!trendEl) continue;

                // Получаем уникальные периоды и сортируем (от нового к старому)
                const periods = sortPeriods(Object.keys(periodData));
                if (periods.length < 2) {
                    trendEl.className = 'trend-indicator trend-stable';
                    trendEl.innerHTML = '<span class="trend-arrow">➡️</span> Недостаточно данных';
                    continue;
                }

                // Берём последний период и сравниваем с предыдущим
                const lastPeriod = periods[periods.length - 1];
                const prevPeriod = periods[periods.length - 2];

                const lastAvg = periodData[lastPeriod].total / periodData[lastPeriod].count;
                const prevAvg = periodData[prevPeriod].total / periodData[prevPeriod].count;
                const diff = lastAvg - prevAvg;

                if (diff > 0.3) {
                    trendEl.className = 'trend-indicator trend-improving';
                    trendEl.innerHTML = `<span class="trend-arrow">📈</span> Улучшается (+${diff.toFixed(1)})`;
                } else if (diff < -0.3) {
                    trendEl.className = 'trend-indicator trend-worsening';
                    trendEl.innerHTML = `<span class="trend-arrow">📉</span> Ухудшается (${diff.toFixed(1)})`;
                } else {
                    trendEl.className = 'trend-indicator trend-stable';
                    trendEl.innerHTML = '<span class="trend-arrow">➡️</span> Стабильно';
                }
            }
        }

        function openSalonModal(salonName) {
            const modal = document.getElementById('salonModal');
            document.getElementById('modalTitle').textContent = salonName;
            document.getElementById('modalSubtitle').textContent = 'Динамика за последние 6 месяцев';

            // Получаем данные за 6 месяцев
            const salonOrders = allOrders.filter(o => o.salon === salonName);

            // Группируем по периодам
            const periodScores = {};
            const periodCounts = {};

            salonOrders.forEach(order => {
                if (!order.period) return;
                if (!periodScores[order.period]) {
                    periodScores[order.period] = 0;
                    periodCounts[order.period] = 0;
                }
                periodScores[order.period] += order.total_score || 0;
                periodCounts[order.period]++;
            });

            // Берём последние 6 периодов (в хронологическом порядке для графика)
            const sortedPeriods = sortPeriods(Object.keys(periodScores)); // от нового к старому
            const periods = sortedPeriods.slice(0, 6).reverse(); // берём 6 самых новых и разворачиваем
            const data = periods.map(p => Math.round(periodScores[p] / periodCounts[p] * 10) / 10);
            const counts = periods.map(p => periodCounts[p]);

            // Формируем читаемые названия периодов
            const labels = periods.map(p => {
                const [month, year] = p.split('.');
                const monthNames = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн',
                                    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
                return monthNames[parseInt(month)] + '.' + year.slice(2);
            });

            const ctx = document.getElementById('salonDetailChart').getContext('2d');

            // Удаляем старый график
            if (detailChart) {
                detailChart.destroy();
            }

            // Создаём новый график
            detailChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Средний рейтинг',
                        data: data,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 6,
                        pointBackgroundColor: '#667eea',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'Рейтинг: ' + context.parsed.y;
                                },
                                afterLabel: function(context) {
                                    return 'Заказов: ' + counts[context.dataIndex];
                                }
                            }
                        },
                        datalabels: {
                            anchor: 'end',
                            align: 'top',
                            color: '#667eea',
                            font: {
                                weight: 'bold',
                                size: 14
                            },
                            formatter: function(value) {
                                return value.toFixed(1);
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            min: Math.min(...data) - 2,
                            max: 18,
                            title: {
                                display: true,
                                text: 'Средний рейтинг',
                                font: {
                                    size: 14
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                font: {
                                    size: 13
                                },
                                callback: function(value) {
                                    return value.toFixed(1);
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                font: {
                                    size: 13
                                }
                            }
                        }
                    }
                },
                plugins: [{
                    id: 'datalabels',
                    afterDatasetsDraw: function(chart) {
                        const ctx = chart.ctx;
                        ctx.save();
                        ctx.font = 'bold 14px Arial';
                        ctx.fillStyle = '#667eea';
                        ctx.textAlign = 'center';

                        chart.data.datasets.forEach((dataset, i) => {
                            const meta = chart.getDatasetMeta(i);
                            meta.data.forEach((point, index) => {
                                const data = dataset.data[index];
                                ctx.fillText(data.toFixed(1), point.x, point.y - 10);
                            });
                        });
                        ctx.restore();
                    }
                }]
            });

            modal.classList.add('active');
        }

        function closeSalonModal() {
            const modal = document.getElementById('salonModal');
            modal.classList.remove('active');
        }

        // Закрытие по клику вне окна
        document.addEventListener('click', function(e) {
            const modal = document.getElementById('salonModal');
            if (e.target === modal) {
                closeSalonModal();
            }
        });

        function applyPeriodFilter() {
            console.log('[DEBUG] applyPeriodFilter START');
            const selectedPeriod = document.getElementById('periodSelect').value;
            console.log('[DEBUG] applyPeriodFilter called, period:', selectedPeriod);

            let filteredOrders;
            if (selectedPeriod === 'all') {
                filteredOrders = allOrders;
            } else {
                filteredOrders = allOrders.filter(o => o.period === selectedPeriod);
            }

            console.log('filteredOrders count:', filteredOrders.length);

            const stats = calculateStats(filteredOrders);
            updateUI(stats);
            updateSalonTable(filteredOrders, selectedPeriod);
            updateTrends(filteredOrders);
            updateProblemTasks(filteredOrders);

            console.log('Chart updated');

            // Показываем сообщение если нет данных
            const container = document.getElementById('salonsContainer');
            if (filteredOrders.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">Нет данных за выбранный период</p>';
            }
        }

        function updateSalonTable(orders, selectedPeriod) {
            console.log('[DEBUG] updateSalonTable START');
            console.log('[DEBUG] updateSalonTable called, orders:', orders.length, 'period:', selectedPeriod);

            // Подсчёт среднего рейтинга по салонам
            const salonScores = {};
            const salonCounts = {};

            orders.forEach(order => {
                if (!order.salon) return;
                if (!salonScores[order.salon]) {
                    salonScores[order.salon] = 0;
                    salonCounts[order.salon] = 0;
                }
                salonScores[order.salon] += order.total_score || 0;
                salonCounts[order.salon]++;
            });

            // Сортируем салоны по среднему рейтингу (топ-15)
            const salonAvg = Object.keys(salonScores).map(salon => ({
                name: salon,
                avg: Math.round(salonScores[salon] / salonCounts[salon] * 10) / 10,
                count: salonCounts[salon]
            })).sort((a, b) => b.avg - a.avg).slice(0, 15);

            console.log('Top 3 salons:', salonAvg.slice(0, 3).map(s => `${s.name}: ${s.avg}`).join(', '));

            // Генерируем HTML таблицы
            let tableHTML = '<table style="width: 100%; border-collapse: collapse;">';
            tableHTML += '<thead><tr style="background: #667eea; color: white;">';
            tableHTML += '<th style="padding: 12px; text-align: left; border-radius: 8px 0 0 0;">#</th>';
            tableHTML += '<th style="padding: 12px; text-align: left;">Салон</th>';
            tableHTML += '<th style="padding: 12px; text-align: center;">Рейтинг</th>';
            tableHTML += '<th style="padding: 12px; text-align: center; border-radius: 0 8px 0 0;">Заказов</th>';
            tableHTML += '</tr></thead><tbody>';

            salonAvg.forEach((salon, index) => {
                const rowStyle = index % 2 === 0 ? 'background: white;' : 'background: #f8f9fa;';
                const ratingColor = salon.avg >= 14 ? '#28a745' : salon.avg >= 12 ? '#ffc107' : '#dc3545';

                tableHTML += '<tr style="' + rowStyle + '">';
                tableHTML += '<td style="padding: 12px; font-weight: bold;">' + (index + 1) + '</td>';
                tableHTML += '<td style="padding: 12px;">' + salon.name + '</td>';
                tableHTML += '<td style="padding: 12px; text-align: center;"><span style="color: ' + ratingColor + '; font-weight: bold; font-size: 1.2em;">' + salon.avg.toFixed(1) + '</span></td>';
                tableHTML += '<td style="padding: 12px; text-align: center;">' + salon.count + '</td>';
                tableHTML += '</tr>';
            });

            tableHTML += '</tbody></table>';

            // Обновляем заголовок
            const chartTitle = selectedPeriod === 'all' ? '📊 Рейтинг салонов за все периоды' : `📊 Рейтинг салонов за период: ${selectedPeriod}`;
            const chartHeader = document.querySelector('.chart-section h2');
            if (chartHeader) {
                chartHeader.textContent = chartTitle;
            }

            // Вставляем таблицу
            document.getElementById('salonRatingTable').innerHTML = tableHTML;
            console.log('[DEBUG] Table innerHTML updated!');
        }

        // Максимальные баллы для типов продуктов (должны совпадать с Python)
        const CATEGORY_MAX_JS = {
            'Клубничный букет': 14,
            'Цветочный букет': 14,
            'Коробочка с клубникой или бананами': 14,
            'Клубнично-цветочный букет': 18,
            'Цветочный бокс': 18,
            'Коробочка+цветочный букет': 14,
            'Клубничный бокс': 14,
            'Цветочно-клубничный бокс': 18
        };

        function updateProblemTasks(orders) {
            console.log('[DEBUG] updateProblemTasks called, orders:', orders.length);

            // Группируем задачи по салонам
            const salonTasks = {};
            orders.forEach(order => {
                if (!order.salon || !order.total_score || !order.task_id) return;

                const maxScore = CATEGORY_MAX_JS[order.product_type] || 14;
                const threshold = maxScore === 14 ? 13 : 16;

                // Только задачи с низким баллом
                if (order.total_score <= threshold) {
                    if (!salonTasks[order.salon]) {
                        salonTasks[order.salon] = [];
                    }
                    salonTasks[order.salon].push({
                        taskId: order.task_id,
                        orderId: order.order_id || order.task_id,
                        score: order.total_score,
                        maxScore: maxScore,
                        florist: order.florist,
                        date: order.date
                    });
                }
            });

            // Для каждого салона берём 5 худших задач
            let html = '';
            for (const [salon, tasks] of Object.entries(salonTasks)) {
                // Сортируем по возрастанию балла (худшие первые)
                tasks.sort((a, b) => a.score - b.score);
                const worstTasks = tasks.slice(0, 5);

                if (worstTasks.length === 0) continue;

                html += '<div style="background: white; border-radius: 10px; padding: 15px; border: 2px solid #ffcdd2;">';
                html += '<h3 style="color: #c62828; margin-bottom: 15px;">' + salon + '</h3>';

                worstTasks.forEach(task => {
                    const pyrusUrl = 'https://pyrus.com/' + task.taskId;
                    html += '<div style="margin-bottom: 12px; padding: 10px; background: #ffebee; border-radius: 5px;">';
                    html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">';
                    html += '<span style="font-weight: bold; color: #c62828;">' + task.score + '/' + task.maxScore + '</span>';
                    html += '<a href="' + pyrusUrl + '" target="_blank" style="color: #1976d2; text-decoration: none;">🔗 Заказ #' + task.orderId + '</a>';
                    html += '</div>';
                    if (task.florist) {
                        html += '<small style="color: #666;">Флорист: ' + task.florist + '</small>';
                    }
                    html += '</div>';
                });

                html += '</div>';
            }

            if (html === '') {
                html = '<p style="text-align: center; color: #888; padding: 40px;">Нет задач с низким баллом за выбранный период 🎉</p>';
            }

            document.getElementById('problemTasks').innerHTML = html;
            console.log('[DEBUG] Problem tasks updated!');
        }

        // Инициализация при загрузке
        document.addEventListener('DOMContentLoaded', function() {
            console.log('[DEBUG] DOMContentLoaded fired!');
            console.log('[DEBUG] allOrders length:', allOrders.length);

            // Инициализируем фильтр периодов
            const periodSelect = document.getElementById('periodSelect');
            console.log('[DEBUG] periodSelect element:', periodSelect);
            if (periodSelect) {
                periodSelect.addEventListener('change', function() {
                    console.log('[DEBUG] Change event fired! Value:', periodSelect.value);
                    applyPeriodFilter();
                });
                console.log('[DEBUG] Event listener attached to periodSelect');
            }

            // Инициализируем таблицу с данными за всё время
            console.log('[DEBUG] Calling updateSalonTable with allOrders...');
            updateSalonTable(allOrders, 'all');
            console.log('[DEBUG] Initial table update complete');

            // Инициализируем график салонов
            console.log('[DEBUG] Calling updateSalonChart with allOrders...');
            updateSalonChart(allOrders, 'all');
            console.log('[DEBUG] Initial chart update complete');

            // Инициализируем проблемные задачи
            updateProblemTasks(allOrders);

            // Инициализируем тренды
            updateTrends(allOrders);
        });
    </script>
</body>
</html>'''

    return html

def main():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Чтение CSV файла...")
    data = parse_csv()
    print(f"Загружено {len(data)} записей")

    print("Подготовка данных для JavaScript...")
    # Сортируем периоды по убыванию (от нового к старому) используя period_sort
    periods_dict = {o['period']: o['period_sort'] for o in data if o['period']}
    periods = sorted(periods_dict.keys(), key=lambda p: periods_dict[p], reverse=True)
    print(f"Периодов: {len(periods)}")

    print("Генерация HTML дашборда...")
    html = generate_html(data, periods)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Дашборд сохранен: {OUTPUT_FILE}")
    print("\\nПри выборе периода будет полностью пересчитываться статистика!")

if __name__ == '__main__':
    main()

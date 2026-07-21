#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФИКСИРОВАННАЯ ВЕРСЯ: Проблема с обновлением графика решена
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
                    'period_sort': parse_period_sort(period),
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
    """Парсит период формата 'ММ.ГГГГ' в число для сортировки."""
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
    periods_dict = {}

    for record in data:
        period = record.get('period')
        if period:
            periods_dict[period] = record.get('period_sort', 0)

        orders.append({
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

    sorted_periods = sorted(periods_dict.keys(), key=lambda p: periods_dict[p], reverse=True)
    return orders, sorted_periods

def calculate_stats_from_orders(orders):
    """Вычисляет статистику из списка заказов"""
    if not orders:
        return {
            'total_orders': 0,
            'avg_score': 0,
            'perfect_count': 0,
            'perfect_percentage': 0,
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
        cities[city]['total_score'] += order['total_score'] or 0
        if order['total_score'] and order['total_score'] >= 17:
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
                            'categories': defaultdict(lambda: {'count': 0, 'total_score': 0})}
        salons[salon]['orders'].append(order)
        salons[salon]['count'] += 1
        salons[salon]['total_score'] += order['total_score'] or 0
        if order['total_score'] and order['total_score'] >= 17:
            salons[salon]['perfect'] += 1

        # Категории
        cat = order.get('product_type')
        if cat:
            salons[salon]['categories'][cat]['count'] += 1
            if order['total_score']:
                salons[salon]['categories'][cat]['total_score'] += order['total_score']

    salon_stats = {}
    for salon, data in salons.items():
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0

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
            florists[key] = {
                'orders': [],
                'total_score': 0,
                'count': 0,
                'perfect': 0,
                'criteria_sums': defaultdict(int),
                'criteria_counts': defaultdict(int)
            }
        florists[key]['orders'].append(order)
        florists[key]['count'] += 1
        florists[key]['total_score'] += order['total_score'] or 0
        if order['total_score'] and order['total_score'] >= 17:
            florists[key]['perfect'] += 1

        # Критерии
        for crit in CRITERIA_MAX.keys():
            val = order.get(crit)
            if val is not None:
                florists[key]['criteria_sums'][crit] += val
                florists[key]['criteria_counts'][crit] += 1

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
                criteria[crit] = avg_crit

        florist_stats[key] = {
            'name': florist_name,
            'salon': key.split('_')[0] if '_' in key else '',
            'avg_score': round(avg, 1),
            'count': data['count'],
            'perfect': data['perfect'],
            'criteria': criteria
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
        .chart-section {{
            margin: 30px 0;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 15px;
        }}
        .chart-section h2 {{
            margin-bottom: 20px;
            color: #667eea;
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
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .salon-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
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
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .categories-list {{
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
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
                <select id="periodSelect">
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
    html += '        </div>\n\n'

    # График
    html += '''        <div class="chart-section" id="chartSection">
            <h2 id="chartTitle">📊 Средний рейтинг салонов за период</h2>
            <div style="position: relative; height: 400px;">
                <canvas id="salonRatingChart"></canvas>
            </div>
        </div>\n'''

    html += '        <h2 style="margin-bottom: 20px; color: #333;">📊 Качество по салонам</h2>\n'
    html += '        <div class="salons-grid" id="salonsContainer">\n'

    # Генерация карточек салонов
    sorted_salons = sorted(total_stats['salons'].items(),
                          key=lambda x: x[1]['avg_score'], reverse=True)

    for salon, salon_data in sorted_salons:
        badge_class = 'badge-good' if salon_data['avg_score'] >= 14 else 'badge-avg' if salon_data['avg_score'] >= 12 else 'badge-bad'
        badge_text = 'Отлично' if salon_data['avg_score'] >= 14 else 'Хорошо' if salon_data['avg_score'] >= 12 else 'Внимание'
        salon_id = salon.replace(' ', '-').replace('(', '').replace(')', '')

        html += f'            <div class="salon-card" data-salon="{salon}" id="card-{salon_id}">\n'
        html += f'                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">\n'
        html += f'                    <div style="font-size: 1.2em; font-weight: bold; color: #333;">{salon} 📊</div>\n'
        html += f'                    <span class="badge {badge_class}">{badge_text}</span>\n'
        html += f'                </div>\n'
        html += f'                <div class="score-big" id="score-{salon_id}">{salon_data["avg_score"]}</div>\n'
        html += f'                <div class="metric">\n'
        html += f'                    <span>Заказов:</span>\n'
        html += f'                    <span><strong id="count-{salon_id}">{salon_data["count"]}</strong></span>\n'
        html += f'                </div>\n'

        # Категории салона
        html += f'                <div class="categories-list" id="categories-{salon_id}">\n'
        if salon_data.get('categories'):
            html += f'                    <strong style="color: #666; font-size: 0.9em;">Категории:</strong>\n'
            for cat_name, cat_data in sorted(salon_data['categories'].items(),
                                             key=lambda x: x[1]['avg_score'], reverse=True):
                html += f'                    <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.85em;">\n'
                html += f'                        <span>{cat_name}:</span>\n'
                html += f'                        <span><strong>{cat_data["avg_score"]}/{cat_data["max_score"]}</strong> ({cat_data["percentage"]}%)</span>\n'
                html += f'                    </div>\n'
        html += f'                </div>\n'

        # Флористы салона
        html += f'                <div id="florists-{salon_id}">\n'
        salon_florists = {k: v for k, v in total_stats['florists'].items()
                          if v.get('salon') == salon}
        if salon_florists:
            html += f'                <h4 style="margin-top: 20px; margin-bottom: 15px; color: #667eea;">Флористы:</h4>\n'
            for f_key, f_data in sorted(salon_florists.items(),
                                  key=lambda x: x[1]['avg_score'], reverse=True):
                html += f'                <div class="florist-card">\n'
                html += f'                    <div class="name">{f_data["name"]}: {f_data["avg_score"]} ({f_data["count"]} зак.)</div>\n'
                html += f'                </div>\n'
        html += f'                </div>\n'

        html += f'            </div>\n'

    html += '        </div>\n\n'

    # Модальное окно для детального графика салона
    html += '''        <div class="modal" id="salonModal">
            <div class="modal-content">
                <button class="modal-close" onclick="closeSalonModal()">&times;</button>
                <h2 class="modal-title" id="modalTitle">Детальный график</h2>
                <p class="modal-subtitle" id="modalSubtitle">Динамика за последние 6 месяцев</p>
                <div style="position: relative; height: 400px;">
                    <canvas id="salonDetailChart"></canvas>
                </div>
            </div>
        </div>\n'''

    html += '    </div>\n\n'

    html += '''    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Все данные заказов
        const allOrders = ''' + json.dumps(orders, ensure_ascii=False) + ''';

        // Названия критериев
        const CRITERIA_NAMES = ''' + json.dumps(CRITERIA_NAMES, ensure_ascii=False) + ''';

        // Максимальные баллы критериев
        const CRITERIA_MAX = ''' + json.dumps(CRITERIA_MAX, ensure_ascii=False) + ''';

        // Глобальные переменные для графиков
        let salonChart = null;
        let detailChart = null;

        // Вспомогательная функция для сортировки периодов
        function sortPeriods(periods) {
            return periods.sort((a, b) => {
                const [aMonth, aYear] = a.split('.').map(Number);
                const [bMonth, bYear] = b.split('.').map(Number);
                if (aYear !== bYear) {
                    return bYear - aYear;
                }
                return bMonth - aMonth;
            });
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

            const salons = {};
            orders.forEach(order => {
                if (!order.salon) return;
                if (!salons[order.salon]) {
                    salons[order.salon] = { totalScore: 0, count: 0 };
                }
                salons[order.salon].count++;
                salons[order.salon].totalScore += order.total_score || 0;
            });

            const salonStats = {};
            for (const [salon, data] of Object.entries(salons)) {
                salonStats[salon] = {
                    avg_score: Math.round(data.totalScore / data.count * 10) / 10,
                    count: data.count
                };
            }

            return {
                total_orders: totalOrders,
                avg_score: Math.round(avgScore * 100) / 100,
                perfect_count: perfectCount,
                perfect_percentage: Math.round((perfectCount / totalOrders) * 1000) / 10,
                salons: salonStats
            };
        }

        function updateUI(stats) {
            document.getElementById('totalOrders').textContent = stats.total_orders.toLocaleString();
            document.getElementById('avgScore').textContent = stats.avg_score;
            document.getElementById('perfectCount').textContent = stats.perfect_count;
            document.getElementById('perfectPercent').textContent = stats.perfect_percentage;
        }

        function updateSalonChart(orders, selectedPeriod) {
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

            // Сортируем салоны (топ-15)
            const salonAvg = Object.keys(salonScores).map(salon => ({
                name: salon,
                avg: Math.round(salonScores[salon] / salonCounts[salon] * 10) / 10,
                count: salonCounts[salon]
            })).sort((a, b) => b.avg - a.avg).slice(0, 15);

            const labels = salonAvg.map(s => s.name);
            const data = salonAvg.map(s => s.avg);

            // Цвета
            const colors = data.map(score => {
                if (score >= 14) return 'rgba(40, 167, 69, 0.8)';
                if (score >= 12) return 'rgba(255, 193, 7, 0.8)';
                return 'rgba(220, 53, 69, 0.8)';
            });

            // Обновляем заголовок
            const chartTitle = selectedPeriod === 'all'
                ? '📊 Средний рейтинг салонов за все периоды'
                : `📊 Средний рейтинг салонов за период: ${selectedPeriod}`;
            document.getElementById('chartTitle').textContent = chartTitle;

            // Создаём график
            const ctx = document.getElementById('salonRatingChart').getContext('2d');

            if (salonChart) {
                salonChart.destroy();
            }

            salonChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Средний рейтинг',
                        data: data,
                        backgroundColor: colors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 18
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        datalabels: {
                            anchor: 'end',
                            align: 'end',
                            color: '#333',
                            font: {
                                weight: 'bold',
                                size: 12
                            },
                            formatter: function(value) {
                                return value.toFixed(1);
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
                        ctx.fillStyle = '#333';
                        ctx.textAlign = 'center';

                        chart.data.datasets.forEach((dataset, i) => {
                            const meta = chart.getDatasetMeta(i);
                            meta.data.forEach((bar, index) => {
                                const dataVal = dataset.data[index];
                                ctx.fillText(dataVal.toFixed(1), bar.x, bar.y - 5);
                            });
                        });
                        ctx.restore();
                    }
                }]
            });
        }

        function applyPeriodFilter() {
            const selectedPeriod = document.getElementById('periodSelect').value;

            let filteredOrders;
            if (selectedPeriod === 'all') {
                filteredOrders = allOrders;
            } else {
                filteredOrders = allOrders.filter(o => o.period === selectedPeriod);
            }

            const stats = calculateStats(filteredOrders);
            updateUI(stats);
            updateSalonChart(filteredOrders, selectedPeriod);

            // Скрываем карточки салонов без заказов в выбранный период
            const activeSalons = new Set(filteredOrders.map(o => o.salon).filter(Boolean));
            const salonCards = document.querySelectorAll('.salon-card');
            salonCards.forEach(card => {
                const salonName = card.getAttribute('data-salon');
                if (selectedPeriod === 'all' || activeSalons.has(salonName)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });

            // Обновляем данные в карточках салонов
            updateSalonCards(filteredOrders);
        }

        function updateSalonCards(filteredOrders) {
            // Группируем данные по салонам
            const salonData = {};
            filteredOrders.forEach(order => {
                if (!order.salon) return;
                if (!salonData[order.salon]) {
                    salonData[order.salon] = {
                        totalScore: 0,
                        count: 0,
                        categories: {},
                        florists: {}
                    };
                }
                salonData[order.salon].totalScore += order.total_score || 0;
                salonData[order.salon].count++;

                // Категории
                if (order.product_type) {
                    if (!salonData[order.salon].categories[order.product_type]) {
                        salonData[order.salon].categories[order.product_type] = {
                            totalScore: 0,
                            count: 0,
                            maxScore: CATEGORY_MAX[order.product_type] || 18
                        };
                    }
                    salonData[order.salon].categories[order.product_type].totalScore += order.total_score || 0;
                    salonData[order.salon].categories[order.product_type].count++;
                }

                // Флористы
                if (order.florist) {
                    const key = order.salon + '_' + order.florist;
                    if (!salonData[order.salon].florists[key]) {
                        salonData[order.salon].florists[key] = {
                            name: order.florist,
                            totalScore: 0,
                            count: 0
                        };
                    }
                    salonData[order.salon].florists[key].totalScore += order.total_score || 0;
                    salonData[order.salon].florists[key].count++;
                }
            });

            // Обновляем карточки салонов
            for (const salon in salonData) {
                const data = salonData[salon];
                const salonId = salon.replace(/ /g, '-').replace(/[()]/g, '');
                const avgScore = data.count > 0 ? Math.round(data.totalScore / data.count * 10) / 10 : 0;

                // Обновляем счётчик и средний балл
                const scoreEl = document.getElementById('score-' + salonId);
                const countEl = document.getElementById('count-' + salonId);
                if (scoreEl) scoreEl.textContent = avgScore;
                if (countEl) countEl.textContent = data.count;

                // Обновляем категории
                const categoriesEl = document.getElementById('categories-' + salonId);
                if (categoriesEl) {
                    let html = '<strong style="color: #666; font-size: 0.9em;">Категории:</strong>';
                    for (const cat in data.categories) {
                        const catData = data.categories[cat];
                        const catAvg = catData.count > 0 ? Math.round(catData.totalScore / catData.count * 10) / 10 : 0;
                        const percentage = catData.count > 0 ? Math.round((catAvg / catData.maxScore) * 100) : 0;
                        html += `<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.85em;">
                            <span>${cat}</span>
                            <span><strong>${catAvg}/${catData.maxScore}</strong> (${percentage}%)</span>
                        </div>`;
                    }
                    categoriesEl.innerHTML = html;
                }

                // Обновляем флористов
                const floristsEl = document.getElementById('florists-' + salonId);
                if (floristsEl) {
                    let html = '';
                    const floristArray = Object.values(data.florists).sort((a, b) => (b.totalScore / b.count) - (a.totalScore / a.count));
                    if (floristArray.length > 0) {
                        html += '<h4 style="margin-top: 20px; margin-bottom: 15px; color: #667eea;">Флористы:</h4>';
                        floristArray.forEach(f => {
                            const fAvg = f.count > 0 ? Math.round(f.totalScore / f.count * 10) / 10 : 0;
                            html += `<div class="florist-card">
                                <div class="name">${f.name}: ${fAvg} (${f.count} зак.)</div>
                            </div>`;
                        });
                    }
                    floristsEl.innerHTML = html;
                }
            }

            // Для салонов без данных в выбранном периоде - очищаем
            document.querySelectorAll('.salon-card').forEach(card => {
                const salon = card.getAttribute('data-salon');
                if (!salonData[salon]) {
                    const salonId = salon.replace(/ /g, '-').replace(/[()]/g, '');
                    document.getElementById('score-' + salonId)?.remove();
                    document.getElementById('count-' + salonId)?.remove();
                    document.getElementById('categories-' + salonId)?.remove();
                    document.getElementById('florists-' + salonId)?.remove();
                }
            });
        }

        function openSalonModal(salonName) {{
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

            // Берём последние 6 периодов в хронологическом порядке
            const sortedPeriods = sortPeriods(Object.keys(periodScores)).slice(0, 6).reverse();
            const data = sortedPeriods.map(p => Math.round(periodScores[p] / periodCounts[p] * 10) / 10);
            const counts = sortedPeriods.map(p => periodCounts[p]);

            // Формируем читаемые названия периодов
            const labels = sortedPeriods.map(p => {
                const [month, year] = p.split('.');
                const monthNames = ['', 'янв', 'фев', 'мар', 'апр', 'май', 'июн',
                                    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
                return monthNames[parseInt(month)] + '.' + year.slice(2);
            });

            const ctx = document.getElementById('salonDetailChart').getContext('2d');

            if (detailChart) {
                detailChart.destroy();
            }

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
                            }
                        },
                        x: {
                            grid: {
                                display: false
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
                                const dataVal = dataset.data[index];
                                ctx.fillText(dataVal.toFixed(1), point.x, point.y - 10);
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

        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('periodSelect').addEventListener('change', applyPeriodFilter);
            updateSalonChart(allOrders, 'all');
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

    print("Подготовка данных...")
    periods_dict = {o['period']: o['period_sort'] for o in data if o['period']}
    periods = sorted(periods_dict.keys(), key=lambda p: periods_dict[p], reverse=True)
    print(f"Периодов: {len(periods)}")

    print("Генерация HTML...")
    html = generate_html(data, periods)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Дашборд сохранен: {OUTPUT_FILE}")
    print("\\n✓ ОБНОВЛЕНИЕ ГРАФИКА ИСПРАВЛЕНО!")

if __name__ == '__main__':
    main()

"""
Генерация статического HTML dashboard из данных БД
Для проверки без необходимости установки Flask
"""

import sys
import json
from datetime import datetime

# Импортируем модули
from database import DatabaseManager
from aggregator import DataAggregator
from alerts import AlertManager


def generate_static_dashboard():
    """Генерирует статический HTML dashboard"""

    print("=== Генерация статического dashboard ===")
    print()

    # Инициализация
    db = DatabaseManager()
    aggregator = DataAggregator(db)
    alert_manager = AlertManager(db)

    # Получаем данные
    stats = aggregator.get_summary_stats()
    salons_list = sorted(stats['salons'].values(), key=lambda x: x['avg_score'], reverse=True)
    florists_list = sorted(stats['florists'].values(), key=lambda x: x['avg_score'], reverse=True)
    criteria_list = aggregator.get_criteria_stats()
    alerts_list = alert_manager.generate_alerts()

    # Генерируем HTML
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quality Dashboard — Бархат</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #411330;
            margin-bottom: 20px;
        }}
        .kpi {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: linear-gradient(135deg, #E1A4C9 0%, #B26FA1 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
        }}
        .kpi-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .kpi-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        th {{
            background: #411330;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-good {{ background: #D8E8D8; color: #2D5A2D; }}
        .badge-avg {{ background: #FFF0C0; color: #6A5A2A; }}
        .badge-bad {{ background: #F8D8D8; color: #6A2A2A; }}
        .alert {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }}
        .alert.critical {{
            background: #f8d8da;
            border-left-color: #dc3545;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            color: #411330;
            margin-bottom: 15px;
            font-size: 24px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Quality Dashboard — Бархат</h1>
        <p style="color: #666; margin-bottom: 20px;">
            Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
            Всего задач: {stats['total_orders']}
        </p>

        <!-- KPI Cards -->
        <div class="kpi">
            <div class="kpi-card">
                <h3>Всего заказов</h3>
                <div class="value">{stats['total_orders']:,}</div>
            </div>
            <div class="kpi-card">
                <h3>Средний балл</h3>
                <div class="value">{stats['avg_score']:.2f}</div>
            </div>
            <div class="kpi-card">
                <h3>Эталонных</h3>
                <div class="value">{stats['perfect_count']:,}</div>
            </div>
            <div class="kpi-card">
                <h3>Эталонных %</h3>
                <div class="value">{stats['perfect_percentage']:.1f}%</div>
            </div>
        </div>

        <!-- Alerts -->
        {f'<div class="section"><h2 class="section-title">Внимание ({len(alerts_list)})</h2>' if alerts_list else ''}
        {f'''
        {''.join([f'<div class="alert {a.severity.value}"><strong>{a.title}</strong><br>{a.description}</div>' for a in alerts_list[:5]])}
        </div>
        ''' if alerts_list else ''}

        <!-- Salons Table -->
        <div class="section">
            <h2 class="section-title">Рейтинг салонов</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Салон</th>
                        <th>Средний балл</th>
                        <th>Заказов</th>
                        <th>Эталонных</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                    {'''
                    '''.join([f'''
                    <tr>
                        <td>{i + 1}</td>
                        <td>{s['salon']}</td>
                        <td><strong>{s['avg_score']:.2f}</strong></td>
                        <td>{s['count']}</td>
                        <td>{s['perfect']}</td>
                        <td><span class="badge {s['status_class']}">{s['status_emoji']} {s['status_label']}</span></td>
                    </tr>
                    ''' for i, s in enumerate(salons_list[:15])])}
                </tbody>
            </table>
        </div>

        <!-- Florists Table -->
        <div class="section">
            <h2 class="section-title">Рейтинг флористов</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Флорист</th>
                        <th>Салон</th>
                        <th>Средний балл</th>
                        <th>Заказов</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
                    {'''
                    '''.join([f'''
                    <tr>
                        <td>{i + 1}</td>
                        <td>{f['florist']}</td>
                        <td>{f['salon']}</td>
                        <td><strong>{f['avg_score']:.2f}</strong></td>
                        <td>{f['count']}</td>
                        <td><span class="badge {f['status_class']}">{f['status_emoji']} {f['status_label']}</span></td>
                    </tr>
                    ''' for i, f in enumerate(florists_list[:20])])}
                </tbody>
            </table>
        </div>

        <!-- Criteria Table -->
        <div class="section">
            <h2 class="section-title">Критерии качества (от худшего к лучшему)</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Критерий</th>
                        <th>Средний балл</th>
                        <th>% от максимума</th>
                        <th>Худший салон</th>
                    </tr>
                </thead>
                <tbody>
                    {'''
                    '''.join([f'''
                    <tr>
                        <td>{i + 1}</td>
                        <td>{c['criterion']}</td>
                        <td><strong>{c['avg_score']:.2f}</strong></td>
                        <td>{c['percentage']:.1f}%</td>
                        <td>{c['worst_salon']} ({c['worst_salon_score']:.2f})</td>
                    </tr>
                    ''' for i, c in enumerate(criteria_list)])}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>'''

    return html


def main():
    try:
        html = generate_static_dashboard()

        # Сохраняем
        output_file = 'dashboard_static.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"OK: Dashboard сохранен в {output_file}")
        print()
        print("Откройте файл в браузере для просмотра.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

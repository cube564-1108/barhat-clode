#!/usr/bin/env python3
"""
Генерация дашборда качества флористов из локального JSON файла Pyrus
"""

import os
import sys
import json
from datetime import datetime

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JSON_FILE = "pyrus_export_1327961_20260711_065801.json"
OUTPUT_HTML = "florist-quality-dashboard.html"


def safe_int(value):
    """Безопасное преобразование в int"""
    if value is None or value == '':
        return None
    try:
        return int(float(str(value).strip()))
    except:
        return None


def pyrus_to_csv_format(tasks):
    """Преобразование данных Pyrus в формат для дашборда"""

    csv_records = []

    for task in tasks:
        # Создаём dict значений для быстрого доступа
        values = {}
        for v in task.get('fields', []):
            field_id = v.get('id')
            value = v.get('value')

            # Обработка multiple_choice - берём choice_names[0]
            if isinstance(value, dict) and 'choice_names' in value:
                choice_names = value.get('choice_names', [])
                value = choice_names[0] if choice_names else ''
            # Обработка простых списков
            elif isinstance(value, list):
                value = ', '.join(str(v) for v in value)

            values[field_id] = value

        # Извлекаем дату
        created_date = values.get(1, '')  # field_id 1 = Дата создания
        period = ''
        if created_date:
            try:
                # Форматы: "2026-07-10" или "2026-07-10T06:29:11Z"
                if 'T' in created_date:
                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(created_date, '%Y-%m-%d')
                period = f"{dt.month}.{dt.year}"
            except:
                pass

        # Извлекаем ДАТА для отображения
        date_display = ''
        if created_date:
            try:
                if 'T' in created_date:
                    date_display = created_date.split('T')[0]
                else:
                    date_display = created_date
            except:
                pass

        # Маппинг полей Pyrus ID на поля дашборда
        record = {
            'task_id': str(task.get('id', '')),  # ID задачи Pyrus для ссылки
            'Номер заказа': values.get(4, str(task.get('id', ''))),  # field_id 4 = Номер заказа
            'период': period,
            'ДАТА': date_display,
            'Салон': values.get(10, ''),  # field_id 10 = Салон
            'Флорист': values.get(3, ''),  # field_id 3 = Флорист
            'Вид заказа': values.get(6, ''),  # field_id 6 = Вид заказа
            'Итоговая оценка': values.get(18, ''),  # field_id 18 = Итоговая оценка
            'Соответствие каталогу': values.get(7, ''),  # field_id 7 = Соответствие каталогу
            'Аккуратность упаковки': values.get(8, ''),  # field_id 8 = Аккуратность упаковки
            'Оформление клубники': values.get(11, ''),  # field_id 11 = Оформление клубники
            'Обработка цветка': values.get(20, ''),  # field_id 20 = Обработка цветка
            'Техника сборки': values.get(13, ''),  # field_id 13 = Техника сборки
            'Клубника отделена от цветка прозрачной пленкой': values.get(14, ''),  # field_id 14
            'Соответствие правилам вложения материалов': values.get(15, ''),  # field_id 15
            'Фотография': values.get(16, ''),  # field_id 16 = Фотография
            'Свежесть компонентов': values.get(23, ''),  # field_id 23 = Свежесть
            'Комментарии': values.get(17, '')  # field_id 17 = Комментарии
        }

        csv_records.append(record)

    return csv_records


def main():
    """Главная функция"""
    print("=" * 70)
    print("Генерация дашборда качества флористов из JSON")
    print("=" * 70)

    # 1. Загрузка JSON
    print(f"\n[1/3] Загрузка JSON файла: {JSON_FILE}")
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    print(f"  [OK] Загружено: {len(tasks)} задач")

    # 2. Преобразование
    print(f"\n[2/3] Преобразование данных...")
    records = pyrus_to_csv_format(tasks)
    print(f"  [OK] Преобразовано: {len(records)} записей")

    # 3. Генерация HTML
    print(f"\n[3/3] Генерация HTML...")
    try:
        from process_quality_data_full import generate_html

        # Преобразуем записи в формат для process_quality_data_full
        data = []
        for record in records:
            data.append({
                'task_id': record.get('task_id', ''),  # ID задачи Pyrus
                'city': '',  # Будет извлечён из названия салона
                'period': record['период'],
                'date': record['ДАТА'],
                'salon': record['Салон'],
                'florist': record['Флорист'],
                'order_id': record['Номер заказа'],
                'product_type': record['Вид заказа'],
                'total_score': safe_int(record['Итоговая оценка']),
                'catalog_match': safe_int(record['Соответствие каталогу']),
                'packaging_neatness': safe_int(record['Аккуратность упаковки']),
                'strawberry_design': safe_int(record['Оформление клубники']),
                'flower_processing': safe_int(record['Обработка цветка']),
                'assembly_technique': safe_int(record['Техника сборки']),
                'film_separation': safe_int(record['Клубника отделена от цветка прозрачной пленкой']),
                'materials_rules': safe_int(record['Соответствие правилам вложения материалов']),
                'photo': safe_int(record['Фотография']),
                'freshness': safe_int(record['Свежесть компонентов']),
                'comment': record['Комментарии']
            })

        # Определяем город из названия салона
        for record in data:
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

        # Генерируем периоды
        periods = sorted(list(set(r['period'] for r in data if r['period'])), reverse=True)

        # Генерируем HTML
        html = generate_html(data, periods)

        with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  [OK] Дашборд сохранён: {OUTPUT_HTML}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        return 1

    print("\n" + "=" * 70)
    print("[OK] DONE!")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Автоматическая генерация дашборда качества флористов из Pyrus API

Pyrus API → Данные качества → HTML дашборд
"""

import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

PYRUS_TOKEN = os.getenv('PYRUS_ACCESS_TOKEN')
PYRUS_LOGIN = os.getenv('PYRUS_LOGIN')
FORM_ID = 1327961  # Форма оценки качества букетов

OUTPUT_HTML = "florist-quality-dashboard.html"


def auth():
    """Авторизация в Pyrus API"""
    session = requests.Session()
    session.trust_env = False

    response = session.post(
        'https://api.pyrus.com/v4/auth',
        headers={'Content-Type': 'application/json'},
        json={'login': PYRUS_LOGIN, 'security_key': PYRUS_TOKEN}
    )

    if response.status_code != 200:
        raise Exception(f"Auth failed: {response.text}")

    access_token = response.json()['access_token']
    return session, access_token


def get_form_structure(session, access_token, form_id):
    """Получение структуры формы"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = session.get(f'https://api.pyrus.com/v4/forms/{form_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def get_all_submissions(session, access_token, form_id, date_from=None, date_to=None):
    """Получение всех заявок с пагинацией, включая завершённые"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    all_tasks = []
    next_page_token = None

    while True:
        params = {}
        if next_page_token:
            params['next_page_token'] = next_page_token
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to

        # Добавляем фильтр для получения всех задач, включая завершённые
        # Параметр для получения архива/завершённых задач
        params['include_archived'] = 'true'

        response = session.get(
            f'https://api.pyrus.com/v4/forms/{form_id}/register',
            headers=headers,
            params=params
        )
        response.raise_for_status()

        data = response.json()
        tasks = data.get('tasks', [])
        all_tasks.extend(tasks)

        print(f"  Загружено: {len(all_tasks)} заявок")

        has_more = data.get('has_more', False)
        if not has_more:
            break

        next_page_token = data.get('next_page_token')

    return all_tasks


def pyrus_to_csv_format(tasks, form_structure):
    """
    Преобразование данных Pyrus в формат CSV для дашборда.

    Маппинг полей Pyrus ID на поля дашборда:
    - 10 → Салон
    - 3 → Флорист
    - 4 → Номер заказа
    - 6 → Вид заказа
    - 7 → Соответствие каталогу (0-2)
    - 8 → Аккуратность упаковки (0-2)
    - 11 → Оформление клубники (0-2)
    - 20 → Обработка цветка (0-2)
    - 23 → Свежесть компонентов (0-2)
    - 13 → Техника сборки (0-2)
    - 14 → Клубника отделена от цветка прозрачной пленкой (0-2)
    - 15 → Соответствие правилам вложения материалов (0-2)
    - 16 → Фотография (0-2)
    - 17 → Комментарии
    - 18 → Итоговая оценка
    - 22 → Артикул оцениваемого товара
    - 1 → Дата создания
    - 21 → Автор
    """

    csv_records = []

    for task in tasks:
        # Создаём dict значений для быстрого доступа
        values = {}
        for v in task.get('fields', []):  # Pyrus использует 'fields', не 'values'!
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

        # Извлекаем дату - пробуем сначала fields, затем create_date
        created_date = values.get(1, '')  # field_id 1 = Дата создания
        if not created_date:
            created_date = task.get('create_date', '')

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
            'Номер заказа': values.get(4, task.get('id', '')),  # field_id 4 = Номер заказа
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
            'Клубника отделена от цветка прозрачной пленкой': values.get(14, ''),  # field_id 14 = Разделение пленкой
            'Соответствие правилам вложения материалов': values.get(15, ''),  # field_id 15 = Вложение материалов
            'Фотография': values.get(16, ''),  # field_id 16 = Фотография
            'Свежесть компонентов': values.get(23, ''),  # field_id 23 = Свежесть
            'Комментарии': values.get(17, '')  # field_id 17 = Комментарии
        }

        csv_records.append(record)

    return csv_records


def generate_dashboard(records):
    """Генерация HTML дашборда из записей"""
    # Импортируем функцию генерации из process_quality_data_full.py
    try:
        from process_quality_data_full import generate_html, prepare_data_for_js

        # Преобразуем записи в формат для process_quality_data_full
        data = []
        for record in records:
            data.append({
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

        return html

    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь что process_quality_data_full.py находится в корне проекта")
        return None


def safe_int(value):
    """Безопасное преобразование в int"""
    if value is None or value == '':
        return None
    try:
        return int(float(str(value).strip()))
    except:
        return None


def main():
    """Главная функция"""
    print("=" * 70)
    print("Генерация дашборда качества флористов из Pyrus API")
    print("=" * 70)

    # 1. Авторизация
    print("\n[1/5] Authorization in Pyrus...")
    session, access_token = auth()
    print("  [OK] Authorized")

    # 2. Получение структуры формы
    print(f"\n[2/5] Getting form structure (ID: {FORM_ID})...")
    form_structure = get_form_structure(session, access_token, FORM_ID)
    print(f"  [OK] Form: {form_structure.get('name')}")
    print(f"  [OK] Fields: {len(form_structure.get('fields', []))}")

    # 3. Получение всех заявок
    print(f"\n[3/5] Downloading submissions from Pyrus...")
    tasks = get_all_submissions(session, access_token, FORM_ID)
    print(f"  [OK] Downloaded: {len(tasks)} submissions")

    # 4. Преобразование в формат дашборда
    print(f"\n[4/5] Converting data...")
    records = pyrus_to_csv_format(tasks, form_structure)
    print(f"  [OK] Converted: {len(records)} records")

    # 5. Генерация HTML дашборда
    print(f"\n[5/5] Generating HTML dashboard...")
    html = generate_dashboard(records)

    if html:
        with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  [OK] Dashboard saved: {OUTPUT_HTML}")
    else:
        print("  [ERROR] Dashboard generation failed")
        return 1

    print("\n" + "=" * 70)
    print("[OK] DONE! Dashboard updated")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    exit(main())

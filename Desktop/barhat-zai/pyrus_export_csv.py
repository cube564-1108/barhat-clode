"""
Правильный экспорт данных Pyrus в CSV с учётом структуры fields
"""

import json
import csv

INPUT_JSON = 'pyrus_export_1327961_20260710_214924.json'
OUTPUT_CSV = 'pyrus_export_final.csv'

# Загружаем данные
with open(INPUT_JSON, 'r', encoding='utf-8') as f:
    tasks = json.load(f)

print(f'Total tasks: {len(tasks)}')

# Собираем все уникальные поля
all_fields = {}
for task in tasks:
    for field in task.get('fields', []):
        field_id = field['id']
        if field_id not in all_fields:
            all_fields[field_id] = field['name']

# Сортируем по ID
sorted_field_ids = sorted(all_fields.keys())
print(f'Total unique fields: {len(sorted_field_ids)}')

# Создаём CSV
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)

    # Заголовок
    header = ['Task_ID', 'Created_Date'] + [all_fields[fid] for fid in sorted_field_ids]
    writer.writerow(header)

    # Данные
    for task in tasks:
        row = [
            task.get('id'),
            task.get('create_date', '')
        ]

        # Создаём dict значений
        values = {}
        for field in task.get('fields', []):
            field_id = field['id']
            value = field.get('value')

            # Обработка different types
            if isinstance(value, dict) and 'choice_names' in value:
                # Multiple choice - берём names
                choice_names = value.get('choice_names', [])
                values[field_id] = ', '.join(str(n) for n in choice_names)
            elif isinstance(value, dict) and 'id' in value:
                # File attachment
                values[field_id] = f"[file: {value.get('name', value['id'])}]"
            else:
                # Simple value
                values[field_id] = value

        # Добавляем значения в правильном порядке
        for field_id in sorted_field_ids:
            row.append(str(values.get(field_id, '')))

        writer.writerow(row)

print(f'[OK] Exported to {OUTPUT_CSV}')
print(f'[OK] Rows: {len(tasks) + 1} (including header)')

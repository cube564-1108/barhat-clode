"""
Тестовый скрипт для проверки соединения с Pyrus API
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Проверяем переменные окружения
login = os.getenv('PYRUS_LOGIN')
token = os.getenv('PYRUS_ACCESS_TOKEN')

print("=== Проверка переменных окружения ===")
print(f"PYRUS_LOGIN: {'{' + login + '}' if login else '❌ НЕ ЗАДАН'}")
print(f"PYRUS_ACCESS_TOKEN: {'{' + token[:4] + '...' + token[-4:] + '}' if token else '❌ НЕ ЗАДАН'}")
print()

if not login or not token:
    print("❌ Ошибка: PYRUS_LOGIN и/или PYRUS_ACCESS_TOKEN не заданы в .env")
    print()
    print="Пожалуйста, отредактируйте .env файл и добавьте:"
    print("  PYRUS_LOGIN=your_email@pyrus.com")
    print("  PYRUS_ACCESS_TOKEN=your_security_key")
    sys.exit(1)

# Импортируем клиент
from pyrus_client import PyrusClient

print("=== Тестирование соединения с Pyrus API ===")
print()

try:
    client = PyrusClient()

    print("1. Проверка соединения...")
    if client.test_connection():
        print("   ✅ Соединение установлено")
    else:
        print("   ❌ Ошибка соединения")
        sys.exit(1)

    print()
    print("2. Получение структуры формы...")
    form_id = 1327961
    response = client.get_form_structure(form_id)

    if response.success:
        print(f"   ✅ Форма загружена: {len(response.data)} полей")
        print()
        print("   Поля формы:")
        for field in response.data:
            print(f"      - {field.name} (ID: {field.id}, Тип: {field.type})")
    else:
        print(f"   ❌ Ошибка: {response.error}")
        sys.exit(1)

    print()
    print("3. Получение задач формы...")
    tasks_response = client.get_form_tasks(form_id, max_count=10)

    if tasks_response.success:
        tasks = tasks_response.data
        print(f"   ✅ Загружено {len(tasks)} задач")
        if tasks:
            print()
            print("   Пример задачи:")
            task = tasks[0]
            print(f"      ID: {task.get('id')}")
            print(f"      Дата: {task.get('creation_date')}")
            print(f"      Значений: {len(task.get('values', []))}")
    else:
        print(f"   ❌ Ошибка: {tasks_response.error}")
        sys.exit(1)

    print()
    print("=== ✅ Все тесты пройдены! ===")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

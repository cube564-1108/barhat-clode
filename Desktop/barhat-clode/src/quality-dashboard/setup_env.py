"""
Скрипт для копирования Pyrus учетных данных из barhat-zai/.env
Запустите из корня проекта: python src/quality-dashboard/setup_env.py
"""

import os
import sys

# Используем относительные пути от корня проекта
# Скрипт должен запускаться из корня проекта (barhat-clode)
project_root = os.getcwd()
barhat_zai_env = os.path.join(project_root, "barhat-zai", ".env")
quality_dashboard_env = os.path.join(project_root, "src", "quality-dashboard", ".env")

print("=== Copying Pyrus credentials ===")
print(f"Current dir: {project_root}")
print(f"From: {barhat_zai_env}")
print(f"To: {quality_dashboard_env}")
print()

# Проверяем существование исходного файла
if not os.path.exists(barhat_zai_env):
    print(f"ERROR: Source file not found")
    print(f"Expected: {barhat_zai_env}")
    print()
    print("Please run this script from project root (barhat-clode)")
    print("Usage: python src/quality-dashboard/setup_env.py")
    sys.exit(1)

try:
    # Читаем из barhat-zai/.env
    pyrus_login = None
    pyrus_token = None

    with open(barhat_zai_env, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('PYRUS_LOGIN='):
                pyrus_login = line.split('=', 1)[1]
            elif line.startswith('PYRUS_ACCESS_TOKEN='):
                pyrus_token = line.split('=', 1)[1]

    if not pyrus_login or not pyrus_token:
        print("ERROR: PYRUS_LOGIN and/or PYRUS_ACCESS_TOKEN not found")
        sys.exit(1)

    print(f"OK: Found credentials:")
    print(f"   LOGIN: {pyrus_login}")
    print(f"   TOKEN: {pyrus_token[:20]}...{pyrus_token[-10:]}")
    print()

    # Читаем текущий .env если существует
    env_lines = []
    if os.path.exists(quality_dashboard_env):
        with open(quality_dashboard_env, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()

    # Обновляем строки
    updated_lines = []
    login_found = False
    token_found = False

    for line in env_lines:
        if line.startswith('PYRUS_LOGIN='):
            updated_lines.append(f'PYRUS_LOGIN={pyrus_login}\n')
            login_found = True
        elif line.startswith('PYRUS_ACCESS_TOKEN='):
            updated_lines.append(f'PYRUS_ACCESS_TOKEN={pyrus_token}\n')
            token_found = True
        else:
            updated_lines.append(line)

    # Если не нашли, добавляем в конец
    if not login_found:
        updated_lines.append(f'PYRUS_LOGIN={pyrus_login}\n')
    if not token_found:
        updated_lines.append(f'PYRUS_ACCESS_TOKEN={pyrus_token}\n')

    # Перезаписываем .env
    with open(quality_dashboard_env, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)

    print("OK: .env file updated!")
    print()
    print("Now run connection test:")
    print("  cd src/quality-dashboard")
    print("  python test_pyrus_connection.py")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

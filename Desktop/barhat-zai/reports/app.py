#!/usr/bin/env python3
"""
Backend API для лендинга с отчетами по сверке заказов.
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Добавляем корневую директорию в path для импорта скриптов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)


@app.route('/')
def index():
    """Главная страница."""
    return send_from_directory('.', 'index.html')


@app.route('/api/reconcile', methods=['POST'])
def reconcile_orders():
    """
    Запустить сверку заказов за период.

    Body:
    {
        "from": "2026-07-01T00:00",
        "to": "2026-07-07T23:59"
    }
    """
    try:
        data = request.json
        from_date_str = data.get('from')
        to_date_str = data.get('to')

        if not from_date_str:
            return jsonify({'error': 'Не указана дата начала'}), 400

        # Конвертируем даты из формата datetime-local в формат для скриптов
        from_date = datetime.fromisoformat(from_date_str).strftime('%Y-%m-%d %H:%M:%S')
        to_date = datetime.fromisoformat(to_date_str).strftime('%Y-%m-%d %H:%M:%S') if to_date_str else None

        print(f"Запуск сверки: {from_date} - {to_date}")

        # Пути к скриптам
        scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        crm_script = os.path.join(scripts_dir, 'scripts', 'export_retailcrm.py')
        ms_script = os.path.join(scripts_dir, 'scripts', 'export_moysklad.py')
        reconcile_script = os.path.join(scripts_dir, 'scripts', 'reconcile_orders.py')

        # Временные файлы
        temp_dir = os.path.join(scripts_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        crm_file = os.path.join(temp_dir, 'crm_orders.json')
        ms_file = os.path.join(temp_dir, 'ms_orders.json')
        report_file = os.path.join(temp_dir, 'report.json')

        # Шаг 1: Выгрузка из CRM
        print('Выгрузка из RetailCRM...')
        cmd_crm = [
            sys.executable, crm_script,
            '--from', from_date,
            '--output', crm_file
        ]
        if to_date:
            cmd_crm.extend(['--to', to_date])

        result_crm = subprocess.run(cmd_crm, capture_output=True, text=True)
        if result_crm.returncode != 0:
            return jsonify({'error': f'Ошибка выгрузки CRM: {result_crm.stderr}'}), 500

        # Шаг 2: Выгрузка из МойСклад
        print('Выгрузка из МойСклад...')
        cmd_ms = [
            sys.executable, ms_script,
            '--from', from_date,
            '--output', ms_file
        ]
        if to_date:
            cmd_ms.extend(['--to', to_date])

        result_ms = subprocess.run(cmd_ms, capture_output=True, text=True)
        if result_ms.returncode != 0:
            return jsonify({'error': f'Ошибка выгрузки МойСклад: {result_ms.stderr}'}), 500

        # Шаг 3: Сверка
        print('Выполнение сверки...')
        cmd_reconcile = [
            sys.executable, reconcile_script,
            '--crm', crm_file,
            '--ms', ms_file,
            '--output', report_file
        ]

        result_reconcile = subprocess.run(cmd_reconcile, capture_output=True, text=True)
        if result_reconcile.returncode != 0:
            return jsonify({'error': f'Ошибка сверки: {result_reconcile.stderr}'}), 500

        # Читаем отчет
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)

        # Удаляем временные файлы
        try:
            os.remove(crm_file)
            os.remove(ms_file)
            os.remove(report_file)
        except:
            pass

        return jsonify(report)

    except Exception as e:
        print(f'Ошибка: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health():
    """Проверка здоровья сервера."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'retailcrm': bool(os.getenv('RETAILCRM_API_KEY')),
            'moysklad': bool(os.getenv('MOYSKLAD_LOGIN') or os.getenv('MOYSKLAD_TOKEN'))
        }
    })


def main():
    """Запуск сервера."""
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print(f"🌸 Запуск сервера отчетов Бархат на порту {port}")
    print(f"📊 Открой в браузере: http://localhost:{port}")

    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    main()

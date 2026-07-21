"""
Quality Dashboard — Flask Application
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from flask import Flask, render_template, jsonify, request

from database import DatabaseManager
from aggregator import DataAggregator
from alerts import AlertManager
from pyrus_client import PyrusClient


# ===== Конфигурация =====

DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Secret header для защиты
SECRET_HEADER_NAME = os.getenv('SECRET_HEADER_NAME', 'X-Secret-Header')
SECRET_HEADER_VALUE = os.getenv('SECRET_HEADER_VALUE', '')


# ===== Логирование =====

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Flask App =====

app = Flask(__name__)
app.config['DEBUG'] = DEBUG
app.config['SECRET_KEY'] = SECRET_KEY

# Инициализация БД
db = DatabaseManager()
aggregator = DataAggregator(db)
alert_manager = AlertManager(db)
pyrus_client = PyrusClient()


# ===== Middleware =====

@app.before_request
def check_secret_header():
    """Проверка secret header для базовой защиты"""
    # В development пропускаем все
    if DEBUG:
        return None

    # В production проверяем header
    if SECRET_HEADER_VALUE:
        header_value = request.headers.get(SECRET_HEADER_NAME)
        if header_value != SECRET_HEADER_VALUE:
            return jsonify({'error': 'Unauthorized'}), 401

    return None


# ===== Routes =====

@app.route('/')
def index():
    """Главная страница dashboard"""
    return render_template('dashboard.html')


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'db_connected': db.get_task_count() >= 0
    })


@app.route('/api/summary')
def summary():
    """Общая статистика (KPI)"""
    try:
        filters = extract_filters(request.args)
        stats = aggregator.get_summary_stats(filters)

        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error in /api/summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/salons')
def salons():
    """Статистика по салонам"""
    try:
        filters = extract_filters(request.args)
        stats = aggregator.get_summary_stats(filters)

        # Сортируем салоны по среднему баллу
        salons_list = sorted(
            stats['salons'].values(),
            key=lambda x: x['avg_score'],
            reverse=True
        )

        return jsonify({
            'success': True,
            'data': salons_list
        })
    except Exception as e:
        logger.error(f"Error in /api/salons: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/florists')
def florists():
    """Статистика по флористам"""
    try:
        filters = extract_filters(request.args)
        stats = aggregator.get_summary_stats(filters)

        # Сортируем флористов по среднему баллу
        florists_list = sorted(
            stats['florists'].values(),
            key=lambda x: x['avg_score'],
            reverse=True
        )

        return jsonify({
            'success': True,
            'data': florists_list
        })
    except Exception as e:
        logger.error(f"Error in /api/florists: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/criteria')
def criteria():
    """Статистика по критериям"""
    try:
        filters = extract_filters(request.args)
        criteria_stats = aggregator.get_criteria_stats(filters)

        return jsonify({
            'success': True,
            'data': criteria_stats
        })
    except Exception as e:
        logger.error(f"Error in /api/criteria: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cities')
def cities():
    """Статистика по городам"""
    try:
        filters = extract_filters(request.args)
        stats = aggregator.get_summary_stats(filters)

        cities_list = sorted(
            stats['cities'].values(),
            key=lambda x: x['avg_score'],
            reverse=True
        )

        return jsonify({
            'success': True,
            'data': cities_list
        })
    except Exception as e:
        logger.error(f"Error in /api/cities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/alerts')
def alerts():
    """Алерты"""
    try:
        filters = extract_filters(request.args)
        alerts_list = alert_manager.generate_alerts(filters)
        summary = alert_manager.get_alerts_summary(alerts_list)

        # Фильтруем по severity если указано
        severity = request.args.get('severity')
        if severity:
            from alerts import AlertSeverity
            try:
                sev_enum = AlertSeverity(severity)
                alerts_list = alert_manager.filter_alerts_by_severity(alerts_list, sev_enum)
            except ValueError:
                pass

        return jsonify({
            'success': True,
            'data': {
                'alerts': [
                    {
                        'id': a.id,
                        'type': a.type.value,
                        'severity': a.severity.value,
                        'title': a.title,
                        'description': a.description,
                        'entity': a.entity,
                        'value': a.value,
                        'threshold': a.threshold,
                    }
                    for a in alerts_list
                ],
                'summary': summary
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/problems')
def problems():
    """Проблемные задачи"""
    try:
        filters = extract_filters(request.args)
        limit = int(request.args.get('limit', 5))

        problem_tasks = aggregator.get_problem_tasks(filters, limit_per_salon=limit)

        return jsonify({
            'success': True,
            'data': problem_tasks
        })
    except Exception as e:
        logger.error(f"Error in /api/problems: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filters/options')
def filter_options():
    """Опции для фильтров"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'salons': db.get_distinct_salons(),
                'florists': db.get_distinct_florists(),
                'order_types': db.get_distinct_order_types(),
                'periods': db.get_distinct_periods(),
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/filters/options: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Обновить данные из Pyrus"""
    try:
        logger.info("Запуск обновления данных из Pyrus...")

        # TODO: Реализовать полную логику обновления
        # 1. Загрузить задачи из Pyrus
        # 2. Парсить и сохранить в БД
        # 3. Очистить кеш агрегаций

        return jsonify({
            'success': True,
            'message': 'Данные обновлены',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in /api/refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sync', methods=['POST'])
def sync():
    """Полная синхронизация с Pyrus"""
    try:
        logger.info("Запуск полной синхронизации с Pyrus...")

        # TODO: Реализовать полную логику синхронизации
        # Это будет основной endpoint для cron

        return jsonify({
            'success': True,
            'message': 'Синхронизация запущена',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in /api/sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== Helpers =====

def extract_filters(args) -> Dict:
    """Извлекает фильтры из request.args"""
    filters = {}

    if args.get('date_from'):
        filters['date_from'] = args.get('date_from')
    if args.get('date_to'):
        filters['date_to'] = args.get('date_to')
    if args.get('salon'):
        filters['salon'] = args.get('salon')
    if args.get('florist'):
        filters['florist'] = args.get('florist')
    if args.get('order_type'):
        filters['order_type'] = args.get('order_type')
    if args.get('period'):
        filters['period'] = args.get('period')

    return filters


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


# ===== Main =====

if __name__ == '__main__':
    # Инициализация БД
    logger.info("Инициализация БД...")
    db.init_db()

    # Запуск приложения
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Запуск Flask на порту {port}...")

    app.run(host='0.0.0.0', port=port, debug=DEBUG)

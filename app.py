"""
Quality Dashboard — Flask Application
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

# Загружаем .env переменные
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request

from database import DatabaseManager
from aggregator import DataAggregator
from alerts import AlertManager
from pyrus_client import PyrusClient
from models import QualityTask, QUALITY_CRITERIA, GROUPING_FIELDS


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

# PyrusClient будет инициализирован лениво при необходимости
pyrus_client = None

def get_pyrus_client():
    """Ленивая инициализация PyrusClient"""
    global pyrus_client
    if pyrus_client is None:
        pyrus_client = PyrusClient()
    return pyrus_client


def auto_sync_if_needed():
    """Автоматическая синхронизация если БД пустая"""
    try:
        task_count = db.get_task_count()
        logger.info(f"Текущее количество задач в БД: {task_count}")

        if task_count == 0:
            logger.warning("БД пуста, запускаю автоматическую синхронизацию с Pyrus...")

            # Проверяем наличие кредов
            pyrus_login = os.getenv('PYRUS_LOGIN')
            pyrus_token = os.getenv('PYRUS_ACCESS_TOKEN')

            if not pyrus_login or not pyrus_token:
                logger.error("PYRUS_LOGIN или PYRUS_ACCESS_TOKEN не заданы! Пропускаю синхронизацию.")
                return False

            # Ленивая инициализация PyrusClient
            client = get_pyrus_client()

            # Загружаем задачи из Pyrus
            form_id = 1327961
            response = client.get_form_tasks(form_id, max_count=10000)

            if not response.success:
                logger.error(f"Ошибка загрузки задач: {response.error}")
                return False

            tasks_data = response.data
            logger.info(f"Загружено {len(tasks_data)} задач из Pyrus")

            if not tasks_data:
                logger.warning("Pyrus вернул пустой список задач")
                return False

            # Парсим и сохраняем задачи
            saved_count = 0
            skipped_count = 0
            error_count = 0

            for task_data in tasks_data:
                try:
                    task = parse_pyrus_task(task_data)

                    if not task.salon or not task.florist:
                        skipped_count += 1
                        continue

                    if db.save_task(task):
                        saved_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"Error parsing task {task_data.get('id')}: {e}")

            # Обновляем метаданные
            db.set_last_sync(datetime.now().isoformat())

            logger.info(f"Автосинхронизация завершена: сохранено {saved_count}, пропущено {skipped_count}, ошибок {error_count}")
            return True

        else:
            logger.info("БД содержит данные, синхронизация не требуется")
            return True

    except Exception as e:
        logger.error(f"Ошибка при автосинхронизации: {e}")
        return False


# Инициализация БД и автосинхронизация при старте (для gunicorn)
logger.info("Инициализация БД...")
try:
    db.init_db()
    logger.info("БД инициализирована")

    # Автосинхронизация если пусто (только в production)
    if not DEBUG:
        auto_sync_if_needed()
except Exception as e:
    logger.error(f"Ошибка при инициализации БД: {e}")


def parse_pyrus_task(task_data: dict) -> QualityTask:
    """Парсит задачу из формата Pyrus register в QualityTask"""

    task_id = task_data.get('id')
    created_date = task_data.get('create_date')

    # Парсим значения полей из fields
    values = {}  # field_name -> value
    values_by_id = {}  # field_id -> value

    for field in task_data.get('fields', []):
        field_id = field.get('id')
        field_name = field.get('name', '')
        value = field.get('value')

        # Для multiple_choice value может быть объектом
        if isinstance(value, dict):
            # Извлекаем choice_names (первый элемент списка)
            choice_names = value.get('choice_names', [])
            if choice_names:
                value = choice_names[0]
            else:
                value = None

        values[field_name] = value
        values_by_id[field_id] = value

    # Извлекаем данные по названиям полей
    salon = values.get(GROUPING_FIELDS['salon'], '')
    florist = values.get(GROUPING_FIELDS['florist'], '')
    order_type = values.get(GROUPING_FIELDS['order_type'], '')
    order_id = values.get(GROUPING_FIELDS['order_id'], '')
    date = values.get(GROUPING_FIELDS['date'], '')
    period = values.get(GROUPING_FIELDS['period'], '')
    comment = values.get(GROUPING_FIELDS['comment'], '')

    # Извлекаем оценки по критериям
    scores = {}
    total_score = 0

    for crit_key, crit_name in QUALITY_CRITERIA.items():
        score = values.get(crit_name)
        if score is not None:
            try:
                score = int(float(str(score)))
                scores[crit_key] = score
                total_score += score
            except (ValueError, TypeError):
                scores[crit_key] = None

    # Создаем задачу
    return QualityTask(
        task_id=task_id,
        created_at=datetime.fromisoformat(created_date) if created_date else datetime.now(),
        salon=salon,
        florist=florist,
        order_type=order_type,
        order_id=str(order_id) if order_id else '',
        date=date,
        period=period,
        comment=comment,
        scores=scores,
        total_score=total_score if total_score > 0 else None
    )


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
        import traceback
        logger.error(f"Error in /api/salons: {e}\n{traceback.format_exc()}")
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
        import traceback
        logger.error(f"Error in /api/criteria: {e}\n{traceback.format_exc()}")
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
        import traceback
        logger.error(f"Error in /api/alerts: {e}\n{traceback.format_exc()}")
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


@app.route('/api/periods')
def periods():
    """Месячные периоды для фильтра"""
    try:
        months = db.get_distinct_months()
        return jsonify({
            'success': True,
            'data': months
        })
    except Exception as e:
        logger.error(f"Error in /api/periods: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh():
    """Обновить данные из Pyrus"""
    try:
        logger.info("Запуск обновления данных из Pyrus...")

        # Ленивая инициализация PyrusClient
        client = get_pyrus_client()

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

        # Ленивая инициализация PyrusClient
        client = get_pyrus_client()

        # Загружаем задачи из Pyrus
        form_id = 1327961
        response = client.get_form_tasks(form_id, max_count=10000)

        if not response.success:
            logger.error(f"Ошибка загрузки задач: {response.error}")
            return jsonify({
                'success': False,
                'error': response.error
            }), 500

        tasks_data = response.data
        logger.info(f"Загружено {len(tasks_data)} задач из Pyrus")

        # Очищаем старые данные
        db.clear_all_tasks()
        logger.info("БД очищена от старых данных")

        # Парсим и сохраняем задачи
        saved_count = 0
        skipped_count = 0
        error_count = 0

        for task_data in tasks_data:
            try:
                task = parse_pyrus_task(task_data)

                if not task.salon or not task.florist:
                    skipped_count += 1
                    continue

                if db.save_task(task):
                    saved_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Error parsing task {task_data.get('id')}: {e}")

        # Обновляем метаданные
        db.set_last_sync(datetime.now().isoformat())

        logger.info(f"Синхронизация завершена: сохранено {saved_count}, пропущено {skipped_count}, ошибок {error_count}")

        return jsonify({
            'success': True,
            'message': 'Синхронизация завершена',
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'saved': saved_count,
                'skipped': skipped_count,
                'errors': error_count,
                'total_tasks': db.get_task_count()
            }
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

    # Автосинхронизация если пусто (для dev режима)
    if DEBUG:
        logger.info("Dev mode: пропускаю автосинхронизацию")

    # Запуск приложения
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Запуск Flask на порту {port}...")

    app.run(host='0.0.0.0', port=port, debug=DEBUG)

#!/usr/bin/env python3
"""
Выгрузка заказов покупателей из МойСклад для сверки с RetailCRM.
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Any
import json
from dotenv import load_dotenv


class MoyskladExporter:
    """Экспортер заказов покупателей из МойСклад."""

    def __init__(self):
        """Инициализация с загрузкой переменных окружения."""
        load_dotenv()

        self.api_url = os.getenv('MOYSKLAD_API_URL', 'https://api.moysklad.ru/api/remap/1.2')
        self.login = os.getenv('MOYSKLAD_LOGIN')
        self.password = os.getenv('MOYSKLAD_PASSWORD')
        self.token = os.getenv('MOYSKLAD_TOKEN')

        # Проверяем, что указаны либо Basic Auth, либо токен
        if not self.token and not (self.login and self.password):
            raise ValueError("Требуется MOYSKLAD_TOKEN или MOYSKLAD_LOGIN + MOYSKLAD_PASSWORD в .env")

        # Настройка сессии с Basic Auth если есть логин/пароль
        self.session = requests.Session()
        self.session.trust_env = False  # Игнорировать системные прокси
        if self.login and self.password:
            self.session.auth = (self.login, self.password)

        # Заголовки для МойСклад (обязательно gzip)
        self.headers = {
            'Accept-Encoding': 'gzip'
        }

        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'

    def fetch_orders(self, from_date: str, to_date: str = None) -> List[Dict[str, Any]]:
        """
        Выгрузить заказы покупателей за период.

        Args:
            from_date: Начальная дата в формате 'YYYY-MM-DD HH:MM:SS'
            to_date: Конечная дата в формате 'YYYY-MM-DD HH:MM:SS' (опционально)

        Returns:
            Список заказов с основными полями
        """
        all_orders = []
        limit = 100  # Ограничение для expand
        offset = 0

        print(f"Начинаем выгрузку заказов с {from_date}")
        if to_date:
            print(f"по {to_date}")

        while True:
            # Формируем фильтр по дате
            # В МойСклад даты в moment хранятся в часовом поясе MSK
            filter_params = f'moment>{from_date}'
            if to_date:
                filter_params += f';moment<{to_date}'

            # Параметры запроса
            params = {
                'limit': limit,
                'offset': offset,
                'filter': filter_params,
                'expand': 'agent,organization,state'  # Развернуть связанные объекты
            }

            try:
                response = self.session.get(
                    f"{self.api_url}/entity/customerorder",
                    headers=self.headers,
                    params=params
                )

                response.raise_for_status()
                data = response.json()

                orders = data.get('rows', [])
                if not orders:
                    break

                all_orders.extend(orders)

                # Показываем прогресс
                meta = data.get('meta', {})
                total_size = meta.get('size', 0)
                print(f"Загружено: {len(all_orders)} из {total_size}")

                # Проверяем, есть ли еще страницы
                if len(orders) < limit or offset + len(orders) >= total_size:
                    break

                offset += len(orders)

            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе: {e}")
                if hasattr(e.response, 'text'):
                    print(f"Ответ сервера: {e.response.text}")
                break

        print(f"Всего загружено заказов: {len(all_orders)}")
        return all_orders

    def normalize_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализовать заказ к унифицированному формату.

        Args:
            order: Сырой заказ из МойСklad

        Returns:
            Нормализованный заказ
        """
        # Информация о контрагенте (клиенте)
        agent = order.get('agent', {}) or {}
        agent_meta = agent.get('meta', {}) if isinstance(agent, dict) else {}
        agent_name = agent.get('name', 'Неизвестно') if isinstance(agent, dict) else 'Неизвестно'

        # Статус заказа
        state = order.get('state', {}) or {}
        state_name = state.get('name', 'Не указан') if isinstance(state, dict) else 'Не указан'

        # Описание часто содержит ID из внешней системы (в т.ч. RetailCRM)
        description = order.get('description', '')
        external_code = order.get('externalCode', '')

        # Сумма заказа
        sum_value = order.get('sum', 0)
        if isinstance(sum_value, (int, float)):
            sum_value = float(sum_value)
        else:
            sum_value = 0.0

        return {
            'id': order.get('id', ''),
            'name': order.get('name', ''),
            'number': order.get('name', ''),  # В МойСклад name используется как номер
            'status': state.get('id', '') if isinstance(state, dict) else '',
            'status_name': state_name,
            'sum': sum_value,
            'total_sum': sum_value,  # В МойСклад обычно одна сумма
            'created_at': order.get('created', ''),
            'updated_at': order.get('updated', ''),
            'moment': order.get('moment', ''),  # Момент документа
            'customer_id': agent_meta.get('href', '').split('/')[-1] if agent_meta.get('href') else '',
            'customer_name': agent_name,
            'customer_phone': '',  # В МойСклад телефон не всегда readily available
            'description': description,
            'external_code': external_code,
            'applicable': order.get('applicable', True),  # Проведен ли заказ
            'source': 'moysklad'
        }

    def export_to_file(self, orders: List[Dict[str, Any]], filename: str = 'moysklad_orders.json'):
        """
        Сохранить заказы в JSON файл.

        Args:
            orders: Список заказов
            filename: Имя файла для сохранения
        """
        normalized_orders = [self.normalize_order(order) for order in orders]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(normalized_orders, f, ensure_ascii=False, indent=2)

        print(f"Сохранено {len(normalized_orders)} заказов в {filename}")
        return normalized_orders


def main():
    """Главная функция для тестирования."""
    import argparse

    parser = argparse.ArgumentParser(description='Выгрузка заказов покупателей из МойСклад')
    parser.add_argument('--from', dest='from_date', required=True, help='Начальная дата (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--to', dest='to_date', help='Конечная дата (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--output', default='moysklad_orders.json', help='Имя выходного файла')

    args = parser.parse_args()

    try:
        exporter = MoyskladExporter()
        orders = exporter.fetch_orders(args.from_date, args.to_date)
        exporter.export_to_file(orders, args.output)
        print(f"✅ Выгрузка завершена! Заказы сохранены в {args.output}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())

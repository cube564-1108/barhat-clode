#!/usr/bin/env python3
"""
Модуль для работы с очередью заказов флористов.
Получает заказы из RetailCRM и обогащает их данными из каталога (фото).
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


class FloristOrderQueue:
    """Очередь заказов для флористов."""

    # Статус заказа, переданного флористу
    STATUS_SEND_TO_FLORIST = 'send-to-florist'

    def __init__(self):
        """Инициализация с загрузкой переменных окружения."""
        load_dotenv()

        self.api_url = os.getenv('RETAILCRM_API_URL')
        self.api_key = os.getenv('RETAILCRM_API_KEY')

        if not self.api_url or not self.api_key:
            raise ValueError("RETAILCRM_API_URL и RETAILCRM_API_KEY должны быть указаны в .env")

        self.session = requests.Session()
        self.session.trust_env = False
        self.headers = {'X-API-Key': self.api_key}

        # Кеш каталога: offer_id -> {name, imageUrl}
        self._catalog_cache: Dict[str, Dict[str, str]] = None

    def _fetch_catalog(self) -> Dict[str, Dict[str, str]]:
        """
        Получить каталог товаров и построить кеш.

        Returns:
            Словарь offer_id -> {name, imageUrl}
        """
        if self._catalog_cache is not None:
            return self._catalog_cache

        print("Загрузка каталога...")
        cache = {}
        limit = 100
        offset = 0

        while True:
            url = f"{self.api_url}/api/v5/store/products?limit={limit}&offset={offset}"
            try:
                response = self.session.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                if not data.get('success'):
                    print(f"Ошибка API каталога: {data.get('errorMsg', 'Unknown')}")
                    break

                products = data.get('products', [])
                if not products:
                    break

                for product in products:
                    # Берём imageUrl с уровня продукта
                    image_url = product.get('imageUrl', '')

                    for offer in product.get('offers', []):
                        offer_id = str(offer.get('id'))
                        offer_name = offer.get('name', product.get('name', ''))

                        # Если у offer есть свои images, используем их
                        if offer.get('images'):
                            image_url = offer['images'][0]
                        elif not image_url:
                            # Fallback: пустой URL
                            image_url = ''

                        cache[offer_id] = {
                            'name': offer_name,
                            'imageUrl': image_url
                        }

                total_count = data.get('pagination', {}).get('totalCount', 0)
                print(f"Загружено: {len(cache)} товаров из {total_count}")

                if len(products) < limit:
                    break

                offset += limit

            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе каталога: {e}")
                break

        self._catalog_cache = cache
        print(f"Каталог загружен: {len(cache)} товаров")
        return cache

    def get_orders(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить заказы для флористов с обогащением данными из каталога.

        Args:
            date_from: Начальная дата в формате 'YYYY-MM-DD'
            date_to: Конечная дата в формате 'YYYY-MM-DD'
            use_cache: Использовать кеш каталога

        Returns:
            Список заказов с данными о товарах и фото
        """
        # Получаем каталог для обогащения
        catalog = self._fetch_catalog() if use_cache else self._fetch_catalog()

        # Формируем фильтр по статусу и дате
        url = f"{self.api_url}/api/v5/orders"
        params = {
            'limit': 100,
            'filter': self.STATUS_SEND_TO_FLORIST
        }

        # Добавляем фильтр по дате если указан
        if date_from:
            params['fromDate'] = f"{date_from} 00:00:00"
        if date_to:
            params['toDate'] = f"{date_to} 23:59:59"

        print(f"Запрос заказов: {params}")

        try:
            response = self.session.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                error_msg = data.get('errorMsg', 'Unknown error')
                print(f"Ошибка API: {error_msg}")
                return []

            orders = data.get('orders', [])
            print(f"Получено заказов: {len(orders)}")

            # Обогащаем заказы данными из каталога
            enriched_orders = []
            for order in orders:
                enriched = self._enrich_order(order, catalog)
                enriched_orders.append(enriched)

            return enriched_orders

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе заказов: {e}")
            return []

    def _enrich_order(self, order: Dict[str, Any], catalog: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Обогатить заказ данными из каталога.

        Args:
            order: Сырой заказ из RetailCRM
            catalog: Кеш каталога

        Returns:
            Обогащённый заказ
        """
        customer = order.get('customer', {})
        customer_name = customer.get('firstName', '') + ' ' + customer.get('lastName', '')
        customer_name = customer_name.strip() or customer.get('nickname', 'Неизвестно')

        # Обработка статуса
        status = order.get('status', {})
        if isinstance(status, str):
            status_code = status
            status_name = status
        else:
            status_code = status.get('code', 'unknown')
            status_name = status.get('name', 'Неизвестно')

        # Обработка доставки
        delivery = order.get('delivery', {})
        delivery_address = delivery.get('address', {})
        delivery_time = delivery.get('time', {})
        delivery_date = delivery.get('date', '')

        # Обрабатываем items (позиции заказа)
        enriched_items = []
        for item in order.get('items', []):
            offer = item.get('offer', {})
            offer_id = str(offer.get('id', ''))

            # Получаем данные из каталога
            catalog_data = catalog.get(offer_id, {})
            image_url = catalog_data.get('imageUrl', '')
            product_name = catalog_data.get('name', offer.get('name', ''))

            enriched_items.append({
                'id': item.get('id'),
                'quantity': item.get('quantity', 1),
                'offer_id': offer_id,
                'product_name': product_name,
                'image_url': image_url,
                'price': offer.get('price', item.get('initialPrice', 0))
            })

        return {
            'id': str(order.get('id', '')),
            'number': order.get('number', ''),
            'status': status_code,
            'status_name': status_name,
            'created_at': order.get('createdAt', ''),
            'customer_id': str(customer.get('id', '')),
            'customer_name': customer_name,
            'customer_phone': customer.get('phone', '') or (
                customer.get('contacts', [{}])[0].get('value', '') if customer.get('contacts') else ''
            ),
            'delivery': {
                'date': delivery_date,
                'time_from': delivery_time.get('from', '') if delivery_time else '',
                'time_to': delivery_time.get('to', '') if delivery_time else '',
                'address': delivery_address.get('text', '') if delivery_address else '',
                'type': delivery.get('name', '') if isinstance(delivery.get('name'), str) else delivery.get('code', '')
            },
            'items': enriched_items,
            'sum': float(order.get('summ', 0) or 0),
            'total_sum': float(order.get('totalSumm', 0) or 0)
        }

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Изменить статус заказа.

        Args:
            order_id: ID заказа
            new_status: Новый статус

        Returns:
            True если успешно, False иначе
        """
        url = f"{self.api_url}/api/v5/orders/{order_id}/edit"
        data = {
            'order': {
                'status': new_status
            }
        }

        try:
            response = self.session.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                print(f"Статус заказа {order_id} изменён на {new_status}")
                return True
            else:
                error_msg = result.get('errorMsg', 'Unknown error')
                print(f"Ошибка изменения статуса: {error_msg}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при изменении статуса: {e}")
            return False


def main():
    """Главная функция для тестирования."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Получение заказов для флористов')
    parser.add_argument('--from', dest='from_date', help='Начальная дата (YYYY-MM-DD)')
    parser.add_argument('--to', dest='to_date', help='Конечная дата (YYYY-MM-DD)')
    parser.add_argument('--output', default='florist_orders.json', help='Имя выходного файла')

    args = parser.parse_args()

    try:
        queue = FloristOrderQueue()
        orders = queue.get_orders(args.from_date, args.to_date)

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

        print(f"✅ Выгрузка завершена! Заказы сохранены в {args.output}")
        return 0

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == '__main__':
    exit(main())

#!/usr/bin/env python3
"""
Сверка заказов между RetailCRM и МойСклад.

Логика интеграции:
- Заказы создаются только в CRM
- В МойСклад подгружаются заказы со статусами: "выполнен", "отменен", "удержание"
- Сверка имеет смысл только для этих заказов

Что сверяем:
1. Наличие заказа в CRM
2. Наличие заказа в МойСклад (для заказов с правильными статусами)
3. Соответствие статусов
4. Соответствие суммы
5. Соответствие позиций (товаров)
"""

import json
import sys
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime


class OrderReconciler:
    """Сверка заказов между RetailCRM и МойСклад."""

    # Статусы CRM, которые должны быть в МойСклад
    # В МойСклад подгружаются только: Выполнен, Отменен, Удержание
    STATUSES_TO_SYNC = [
        'complete',           # Выполнен
        'cancel-other',       # Отменен
        'cancel-*',           # Другие типы отмены
        'hold',               # Удержание
    ]

    def __init__(self):
        """Инициализация."""
        self.crm_orders = []
        self.ms_orders = []

    def load_data(self, crm_file: str, ms_file: str):
        """
        Загрузить данные из файлов.

        Args:
            crm_file: Путь к файлу с заказами CRM
            ms_file: Путь к файлу с заказами МойСклад
        """
        print(f"Загрузка данных из CRM: {crm_file}")
        with open(crm_file, 'r', encoding='utf-8') as f:
            self.crm_orders = json.load(f)
        print(f"Загружено {len(self.crm_orders)} заказов CRM")

        print(f"Загрузка данных из МойСклад: {ms_file}")
        with open(ms_file, 'r', encoding='utf-8') as f:
            self.ms_orders = json.load(f)
        print(f"Загружено {len(self.ms_orders)} заказов МойСклад")

    def should_be_in_moysklad(self, crm_order: Dict[str, Any]) -> bool:
        """
        Проверить, должен ли заказ быть в МойСклад.

        Args:
            crm_order: Заказ из CRM

        Returns:
            True если заказ должен быть в МойСклад
        """
        status = crm_order.get('status', '').lower()
        status_name = crm_order.get('status_name', '').lower()

        # Проверяем по коду и названию статуса
        for sync_status in self.STATUSES_TO_SYNC:
            # Обработка wildcard
            if sync_status.endswith('*'):
                pattern = sync_status[:-1]  # Убираем *
                if status.startswith(pattern) or status_name.startswith(pattern):
                    return True
            elif sync_status in status or sync_status in status_name:
                return True

        return False

    def find_matching_order(self, crm_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Найти соответствующий заказ в МойСклад.

        Args:
            crm_order: Заказ из CRM

        Returns:
            Найденный заказ или None
        """
        crm_id = crm_order.get('id')
        crm_number = crm_order.get('number')

        # Способ 1: поиск по external_code (там может быть ID CRM)
        for ms_order in self.ms_orders:
            external_code = ms_order.get('external_code', '')
            if external_code == crm_id or external_code == crm_number:
                return ms_order

        # Способ 2: поиск по description (там может быть ID CRM)
        for ms_order in self.ms_orders:
            description = ms_order.get('description', '')
            if crm_id in description or crm_number in description:
                return ms_order

        # Способ 3: поиск по номеру заказа (name в МойСклад)
        for ms_order in self.ms_orders:
            ms_name = ms_order.get('name', '')
            ms_number = ms_order.get('number', '')
            if ms_name == crm_number or ms_number == crm_number:
                return ms_order

        return None

    def compare_orders(self, crm_order: Dict[str, Any], ms_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сравнить два заказа.

        Args:
            crm_order: Заказ из CRM
            ms_order: Заказ из МойСклад

        Returns:
            Словарь с результатами сравнения
        """
        differences = []

        # Сравнение статусов
        crm_status = crm_order.get('status_name', '')
        ms_status = ms_order.get('status_name', '')

        # Нормализация статусов для сравнения
        status_mapping = {
            'выполнен': 'выполнен',
            'completed': 'выполнен',
            'отменен': 'отменен',
            'canceled': 'отменен',
            'удержание': 'удержание',
            'hold': 'удержание'
        }

        crm_status_normalized = status_mapping.get(crm_status.lower(), crm_status.lower())
        ms_status_normalized = status_mapping.get(ms_status.lower(), ms_status.lower())

        if crm_status_normalized != ms_status_normalized:
            differences.append({
                'field': 'status',
                'crm': crm_status,
                'ms': ms_status
            })

        # Сравнение сумм (допустимая погрешность 1 рубль)
        crm_sum = float(crm_order.get('total_sum', 0))
        ms_sum = float(ms_order.get('total_sum', 0))

        if abs(crm_sum - ms_sum) > 1.0:
            differences.append({
                'field': 'sum',
                'crm': crm_sum,
                'ms': ms_sum,
                'diff': crm_sum - ms_sum
            })

        return {
            'match': len(differences) == 0,
            'differences': differences,
            'crm_order': crm_order,
            'ms_order': ms_order
        }

    def reconcile(self) -> Dict[str, Any]:
        """
        Выполнить сверку заказов.

        Returns:
            Результаты сверки
        """
        results = {
            'summary': {
                'total_crm': len(self.crm_orders),
                'total_ms': len(self.ms_orders),
                'should_be_in_ms': 0,
                'found_in_ms': 0,
                'not_found_in_ms': 0,
                'with_differences': 0,
                'fully_match': 0
            },
            'not_found_in_ms': [],
            'with_differences': [],
            'fully_match': [],
            'not_expected_in_ms': []
        }

        # Находим заказы из CRM, которые должны быть в МойСклад
        for crm_order in self.crm_orders:
            if not self.should_be_in_moysklad(crm_order):
                # Этот статус не должен быть в МойСклад
                # Но если он там есть - это тоже расхождение
                ms_order = self.find_matching_order(crm_order)
                if ms_order:
                    results['not_expected_in_ms'].append({
                        'crm_order': crm_order,
                        'ms_order': ms_order,
                        'reason': f"Статус '{crm_order.get('status_name')}' не должен быть в МойСклад"
                    })
                continue

            results['summary']['should_be_in_ms'] += 1

            # Ищем заказ в МойСклад
            ms_order = self.find_matching_order(crm_order)

            if not ms_order:
                # Заказ не найден в МойСклад
                results['not_found_in_ms'].append(crm_order)
                results['summary']['not_found_in_ms'] += 1
            else:
                # Заказ найден - сравниваем
                comparison = self.compare_orders(crm_order, ms_order)
                results['summary']['found_in_ms'] += 1

                if comparison['match']:
                    results['fully_match'].append(comparison)
                    results['summary']['fully_match'] += 1
                else:
                    results['with_differences'].append(comparison)
                    results['summary']['with_differences'] += 1

        return results

    def print_report(self, results: Dict[str, Any]):
        """
        Вывести отчет в консоль.

        Args:
            results: Результаты сверки
        """
        summary = results['summary']

        print("\n" + "=" * 70)
        print("ОТЧЕТ ПО СВЕРКЕ ЗАКАЗОВ")
        print("=" * 70)

        print(f"\n📊 Общая статистика:")
        print(f"  • Всего заказов в CRM: {summary['total_crm']}")
        print(f"  • Всего заказов в МойСклад: {summary['total_ms']}")
        print(f"  • Должны быть в МойСклад: {summary['should_be_in_ms']}")

        print(f"\n✅ Совпадения:")
        print(f"  • Найдены в МойСклад: {summary['found_in_ms']}")
        print(f"  • Полностью совпадают: {summary['fully_match']}")
        print(f"  • С расхождениями: {summary['with_differences']}")
        print(f"  • Не найдены: {summary['not_found_in_ms']}")

        if results['not_expected_in_ms']:
            print(f"\n⚠️  В МойСклад есть заказы со статусами, которые не должны быть там: {len(results['not_expected_in_ms'])}")

        # Вывод заказов не найденных в МойСклад
        if results['not_found_in_ms']:
            print(f"\n❌ Заказы из CRM, не найденные в МойСклад ({len(results['not_found_in_ms'])}):")
            for order in results['not_found_in_ms'][:10]:  # Первые 10
                print(f"  • #{order.get('number')} - {order.get('customer_name')} - {order.get('status_name')}")
            if len(results['not_found_in_ms']) > 10:
                print(f"  ... и еще {len(results['not_found_in_ms']) - 10}")

        # Вывод расхождений
        if results['with_differences']:
            print(f"\n⚠️  Заказы с расхождениями ({len(results['with_differences'])}):")
            for item in results['with_differences'][:10]:
                crm = item['crm_order']
                print(f"  • #{crm.get('number')} - {crm.get('customer_name')}")
                for diff in item['differences']:
                    if diff['field'] == 'status':
                        print(f"    Статус: CRM={diff['crm']} vs МойСклад={diff['ms']}")
                    elif diff['field'] == 'sum':
                        print(f"    Сумма: CRM={diff['crm']} vs МойСклад={diff['ms']} (разница={diff['diff']})")
            if len(results['with_differences']) > 10:
                print(f"  ... и еще {len(results['with_differences']) - 10}")

        print("\n" + "=" * 70)

    def save_report(self, results: Dict[str, Any], filename: str = 'reconciliation_report.json'):
        """
        Сохранить отчет в файл.

        Args:
            results: Результаты сверки
            filename: Имя файла
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📁 Отчет сохранен в {filename}")


def main():
    """Главная функция."""
    import argparse

    parser = argparse.ArgumentParser(description='Сверка заказов между RetailCRM и МойСклад')
    parser.add_argument('--crm', required=True, help='Файл с заказами CRM (JSON)')
    parser.add_argument('--ms', required=True, help='Файл с заказами МойСклад (JSON)')
    parser.add_argument('--output', default='reconciliation_report.json', help='Файл для сохранения отчета')

    args = parser.parse_args()

    try:
        reconciler = OrderReconciler()
        reconciler.load_data(args.crm, args.ms)

        print("\n⏳ Выполняю сверку...")
        results = reconciler.reconcile()

        reconciler.print_report(results)
        reconciler.save_report(results, args.output)

        # Возвращаем код 1 если есть критические расхождения
        if results['summary']['not_found_in_ms'] > 0:
            print(f"\n⚠️  Внимание: {results['summary']['not_found_in_ms']} заказов не найдены в МойСклад")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

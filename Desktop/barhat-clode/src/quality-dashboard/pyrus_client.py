"""
Quality Dashboard — Pyrus API Client
https://pyrus.com/ru/help/api
"""

import os
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

import requests


# ===== Логирование =====

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Конфигурация =====

PYRUS_API_BASE_URL = "https://api.pyrus.com/v4"
PYRUS_API_TOKEN = os.getenv("PYRUS_API_TOKEN")
if not PYRUS_API_TOKEN:
    raise ValueError("PYRUS_API_TOKEN не установлен в переменных окружения")


# ===== Типы данных =====

@dataclass
class PyrusResponse:
    """Обертка над ответом Pyrus API"""
    success: bool
    data: Any
    error: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    next_page_token: Optional[str] = None


@dataclass
class PyrusFormField:
    """Описание поля формы Pyrus"""
    id: int
    name: str
    type: str
    required: bool = False
    choices: Optional[List[Dict[str, Any]]] = None


@dataclass
class PyrusTask:
    """Задача из Pyrus"""
    task_id: int
    created_at: datetime
    values: Dict[int, Any]
    author: str


# ===== Pyrus API Client =====

class PyrusClient:
    """Клиент для работы с Pyrus API"""

    def __init__(self, api_token: Optional[str] = None, base_url: str = PYRUS_API_BASE_URL):
        self.api_token = api_token or PYRUS_API_TOKEN
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        max_retries: int = 3
    ) -> PyrusResponse:
        """Выполнить запрос к API с retry при rate limits"""

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                logger.debug(f"{method} {url} — attempt {retry_count + 1}")

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=30
                )

                # Логируем результат
                logger.debug(f"Response status: {response.status_code}")

                # Rate limit handling
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                if rate_limit_remaining:
                    logger.debug(f"Rate limit remaining: {rate_limit_remaining}")

                # 429 Too Many Requests — retry with backoff
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry...")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue

                # Обычный ответ
                if response.status_code == 200:
                    data = response.json()
                    return PyrusResponse(
                        success=True,
                        data=data,
                        rate_limit_remaining=int(rate_limit_remaining) if rate_limit_remaining else None,
                        next_page_token=data.get("next_page_token")
                    )
                elif response.status_code == 204:
                    return PyrusResponse(success=True, data=None)
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return PyrusResponse(success=False, error=error_msg)

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                logger.error(f"Request timeout: {url}")
                retry_count += 1
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.error(f"Request error: {e}")
                return PyrusResponse(success=False, error=str(e))

        # Все retry попытки исчерпаны
        return PyrusResponse(success=False, error=last_error or "Max retries exceeded")

    def get_form_structure(self, form_id: int) -> PyrusResponse:
        """Получить структуру формы (поля и их типы)

        API: GET /forms/{form_id}
        """
        logger.info(f"Получение структуры формы {form_id}")

        response = self._make_request("GET", f"forms/{form_id}")
        if not response.success:
            return response

        # Парсим поля формы
        form_data = response.data
        fields = []

        for field in form_data.get("fields", []):
            fields.append(PyrusFormField(
                id=field["id"],
                name=field["name"],
                type=field["type"],
                required=field.get("required", False),
                choices=field.get("choices")
            ))

        logger.info(f"Загружено {len(fields)} полей формы")
        return PyrusResponse(success=True, data=fields)

    def get_form_register(self, form_id: int) -> PyrusResponse:
        """Получить реестр задач формы (register)

        API: GET /forms/{form_id}/register
        """
        logger.info(f"Получение реестра формы {form_id}")

        response = self._make_request("GET", f"forms/{form_id}/register")
        if not response.success:
            return response

        return response

    def get_form_tasks(
        self,
        form_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_count: int = 10000
    ) -> PyrusResponse:
        """Получить все задачи формы с пагинацией через register

        API: GET /forms/{form_id}/register

        Args:
            form_id: ID формы
            date_from: Фильтр по дате начала
            date_to: Фильтр по дате окончания
            max_count: Максимальное количество задач

        Returns:
            PyrusResponse с list[dict] — сырые данные из Pyrus register
        """

        logger.info(f"Загрузка задач формы {form_id} из register")

        tasks = []
        current_page_token = None

        while len(tasks) < max_count:
            params = {}
            if current_page_token:
                params["next_page_token"] = current_page_token

            # Добавляем фильтр для получения всех задач, включая завершённые
            params["include_archived"] = "true"

            response = self._make_request(
                "GET",
                f"forms/{form_id}/register",
                params=params
            )

            if not response.success:
                logger.error(f"Ошибка загрузки задач: {response.error}")
                if tasks:
                    # Возвращаем что есть
                    return PyrusResponse(success=True, data=tasks)
                return response

            data = response.data
            tasks_batch = data.get("tasks", [])

            if not tasks_batch:
                logger.info(f"Загружено {len(tasks)} задач (нет больше данных)")
                break

            # Добавляем задачи как есть (сырые данные из Pyrus)
            tasks.extend(tasks_batch)

            logger.info(f"Загружено {len(tasks)} задач...")

            # Проверяем пагинацию
            has_more = data.get("has_more", False)
            if not has_more:
                break

            current_page_token = data.get("next_page_token")

            if len(tasks) >= max_count:
                break

        logger.info(f"Итого загружено {len(tasks)} задач")
        return PyrusResponse(success=True, data=tasks)

    def get_task(self, task_id: int) -> PyrusResponse:
        """Получить детальную информацию о задаче

        API: GET /tasks/{task_id}
        """
        logger.debug(f"Получение задачи {task_id}")
        return self._make_request("GET", f"tasks/{task_id}")

    def test_connection(self) -> bool:
        """Проверить соединение с API

        API: GET /auth/calc_hash
        """
        logger.info("Проверка соединения с Pyrus API...")
        response = self._make_request("GET", "auth/calc_hash")
        return response.success


# ===== Тестирование =====

if __name__ == "__main__":
    # Пример использования
    client = PyrusClient()

    # Проверка соединения
    if client.test_connection():
        print("✅ Соединение с Pyrus API установлено")
    else:
        print("❌ Ошибка соединения с Pyrus API")
        exit(1)

    # Получение структуры формы
    form_id = 1327961
    form_response = client.get_form_structure(form_id)

    if form_response.success:
        print(f"\n📋 Поля формы {form_id}:")
        for field in form_response.data:
            print(f"  - {field.name} (ID: {field.id}, Тип: {field.type})")
    else:
        print(f"❌ Ошибка получения структуры формы: {form_response.error}")

# Инструкция по настройке API интеграции с Pyrus

## Что даёт API Pyrus

- **Получение данных из форм** — выгрузка заявок, анкет, регистраций
- **Создание задач** — автоматическое создание задач из внешних систем
- **Изменение статусов** — обновление задач по событиям
- **Вебхуки** — автоматическая отправка данных при событиях в Pyrus

---

## Шаг 1. Получение Access Token

### Через настройки организации

1. Войдите в Pyrus под аккаунтом администратора организации
2. Перейдите в **Настройки организации** (значок шестерёнки → Настройки)
3. Выберите раздел **API** или **Интеграции**
4. Нажмите **Создать токен**
5. Укажите имя токена (например, "Выгрузка форм")
6. Выберите права доступа (scopes):
   - `forms.read` — чтение данных форм
   - `forms.write` — создание задач через формы
   - `tasks.read` — чтение задач
   - `tasks.write` — изменение задач
7. Скопируйте токен и сохраните в безопасном месте (показывается только один раз)

### Хранение токена

```bash
# .env файл (никогда не коммитить в git!)
PYRUS_ACCESS_TOKEN=your_token_here
PYRUS_LOGIN=your_email@example.com
```

---

## Шаг 2. Определение ID формы

### Способ 1: Из URL
Откройте форму в Pyrus — ID находится в URL:
```
https://pyrus.com/ru/form/12345  ← ID формы = 12345
```

### Способ 2: Через API
```python
import requests

def get_form_list(access_token):
    response = requests.get(
        "https://api.pyrus.com/v4/forms",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()

# Вернёт список всех доступных форм с их ID
```

---

## Шаг 3. Базовые запросы к API

### Адрес базовый URL
```
https://api.pyrus.com/v4/
```

### Структура запроса
```python
import requests
import os

ACCESS_TOKEN = os.getenv("PYRUS_ACCESS_TOKEN")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}
```

---

## Шаг 4. Выгрузка данных из формы (Register)

### Получение реестра заявок формы

```python
def get_form_registers(form_id, date_from=None, date_to=None):
    """
    Выгрузка заявок из формы.
    
    Args:
        form_id: ID формы
        date_from: Начальная дата (YYYY-MM-DD)
        date_to: Конечная дата (YYYY-MM-DD)
    """
    url = f"https://api.pyrus.com/v4/forms/{form_id}/registers"
    
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    return response.json()

# Пример использования
data = get_form_registers(
    form_id=12345,
    date_from="2024-01-01",
    date_to="2024-12-31"
)

# data['tasks'] — список заявок с полями формы
for task in data.get('tasks', []):
    print(f"Заявка #{task['id']}: {task['values']}")
```

### Пагинация (если много заявок)

```python
def get_all_registers(form_id, date_from=None, date_to=None):
    """Выгрузка с учётом пагинации"""
    url = f"https://api.pyrus.com/v4/forms/{form_id}/registers"
    
    all_tasks = []
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    
    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        all_tasks.extend(data.get('tasks', []))
        
        # Проверяем, есть ли следующая страница
        if not data.get('has_more'):
            break
        
        # Получаем next_page_token для следующего запроса
        params['next_page_token'] = data.get('next_page_token')
    
    return all_tasks
```

---

## Шаг 5. Получение конкретной заявки

```python
def get_task(task_id):
    """Получение детальной информации по заявке"""
    url = f"https://api.pyrus.com/v4/tasks/{task_id}"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

# Пример
task_detail = get_task(987654)
print(task_detail['task']['values'])  # Поля формы
```

---

## Шаг 6. Создание задачи через форму

```python
def create_form_task(form_id, fields):
    """
    Создание новой заявки через форму.
    
    Args:
        form_id: ID формы
        fields: dict с полями формы {field_id: value}
    """
    url = f"https://api.pyrus.com/v4/forms/{form_id}/register"
    
    payload = {"fields": fields}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()

# Пример: заполнение формы заявки
# ID полей нужно узнать из настроек формы или через API
new_task = create_form_task(
    form_id=12345,
    fields={
        1001: "Иван Иванов",      # ФИО
        1002: "ivan@example.com", # Email
        1003: "Текст заявки",     # Комментарий
        1004: ["option1"],        # Множественный выбор
    }
)

print(f"Создана заявка #{new_task['task']['id']}")
```

---

## Шаг 7. Настройка Webhooks (для автоматической выгрузки)

### Что такое вебхуки

Вебхук — это HTTP-запрос, который Pyrus отправляет на ваш сервер при наступлении события:
- Создана новая задача
- Изменён статус задачи
- Добавлен комментарий
- Изменены поля формы

### Как создать вебхук

```python
def create_webhook(url, events, filter_by=None):
    """
    Создание вебхука.
    
    Args:
        url: Ваш endpoint для приёма уведомлений
        events: Список событий ['task_create', 'task_update']
        filter_by: Опциональная фильтрация по форме/папке
    """
    api_url = "https://api.pyrus.com/v4/webhooks"
    
    payload = {
        "url": url,
        "events": events
    }
    
    if filter_by:
        payload["filter_by"] = filter_by
    
    response = requests.post(api_url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()

# Пример: webhook для новых заявок формы
webhook = create_webhook(
    url="https://your-server.com/pyrus-webhook",
    events=["task_create"],
    filter_by={
        "form_id": 12345  # Только для конкретной формы
    }
)

print(f"Вебхук создан: {webhook['guid']}")
```

### Обработка вебхука на вашем сервере

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/pyrus-webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    
    # Проверка подписи (recommended)
    # Pyrus может подписывать запросы секретом
    
    event_type = data.get('type')
    task = data.get('task')
    
    if event_type == 'task_create':
        task_id = task['id']
        form_id = task['form_id']
        values = task['values']
        
        # Ваша логика обработки
        print(f"Новая заявка #{task_id} из формы #{form_id}")
        print(f"Данные: {values}")
        
        # Сохранение в БД, отправка уведомления и т.д.
        
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

---

## Шаг 8. Работа с файлами/вложениями

```python
def download_attachment(file_id, save_path):
    """Скачивание вложения из заявки"""
    url = f"https://api.pyrus.com/v4/files/{file_id}/download"
    
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return save_path

def upload_attachment(file_path):
    """Загрузка файла в Pyrus"""
    url = "https://api.pyrus.com/v4/files/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, headers=headers, files=files)
    
    response.raise_for_status()
    return response.json()  # Вернёт file_id для прикрепления
```

---

## Шаг 9. Добавление комментария к задаче

```python
def add_comment(task_id, text, attachments=None):
    """
    Добавление комментария к задаче.
    
    Args:
        task_id: ID задачи
        text: Текст комментария
        attachments: Список file_id (опционально)
    """
    url = f"https://api.pyrus.com/v4/tasks/{task_id}/comments"
    
    payload = {"text": text}
    if attachments:
        payload["attachments"] = attachments
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()
```

---

## Полезные вспомогательные функции

### Получение структуры формы (описание полей)

```python
def get_form_structure(form_id):
    """Получение описания полей формы с их типами"""
    url = f"https://api.pyrus.com/v4/forms/{form_id}"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

# Используйте для маппинга полей:
structure = get_form_structure(12345)
for field in structure['fields']:
    print(f"ID: {field['id']}, Название: {field['name']}, Тип: {field['type']}")
```

### Получение списка всех форм

```python
def list_all_forms():
    """Список всех доступных форм в организации"""
    url = "https://api.pyrus.com/v4/forms"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

forms = list_all_forms()
for form in forms['forms']:
    print(f"ID: {form['id']}, Название: {form['name']}")
```

---

## Пример полного скрипта выгрузки

```python
#!/usr/bin/env python3
"""
Выгрузка заявок из формы Pyrus в CSV.
"""

import csv
import requests
import os
from datetime import datetime

ACCESS_TOKEN = os.getenv("PYRUS_ACCESS_TOKEN")
FORM_ID = 12345
OUTPUT_FILE = "pyrus_export.csv"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def export_form_to_csv(form_id, output_file, date_from=None, date_to=None):
    """Выгрузка заявок в CSV файл"""
    
    # Получение данных
    url = f"https://api.pyrus.com/v4/forms/{form_id}/registers"
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    
    if not data.get('tasks'):
        print("Нет заявок для выгрузки")
        return
    
    # Получение структуры формы для заголовков
    structure_response = requests.get(
        f"https://api.pyrus.com/v4/forms/{form_id}",
        headers=headers
    )
    structure = structure_response.json()
    
    # Создание маппинга field_id -> название поля
    field_names = {f['id']: f['name'] for f in structure['fields']}
    
    # Запись в CSV
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Заголовки
        header = ['Task ID', 'Created Date'] + list(field_names.values())
        writer.writerow(header)
        
        # Строки данных
        for task in data['tasks']:
            row = [
                task['id'],
                task.get('creation_date', '')
            ]
            
            # Значения полей
            values = {v['field_id']: str(v['value']) for v in task.get('values', [])}
            for field_id in field_names:
                row.append(values.get(field_id, ''))
            
            writer.writerow(row)
    
    print(f"Выгружено {len(data['tasks'])} заявок в {output_file}")

if __name__ == '__main__':
    export_form_to_csv(
        form_id=FORM_ID,
        output_file=OUTPUT_FILE,
        date_from="2024-01-01"
    )
```

---

## Ограничения и квоты API

- **Лимит запросов**: ~100 запросов/минуту (проверьте актуальные лимиты в документации)
- **Пагинация**: большие списки (>100 элементов) разбиваются на страницы
- **Размер файла**: ограничен при загрузке через API
- **Токен**: имеет срок действия, может требоваться обновление

---

## Полезные ссылки

- **Документация API**: `help.pyrus.com` → раздел API
- **Песочница/тестовый режим**: доступен по запросу
- **Поддержка**: `api@pyrus.com` для технических вопросов

---

## Чеклист настройки

- [ ] Получен Access Token с нужными правами
- [ ] Определён ID формы для выгрузки
- [ ] Изучена структура формы (названия и ID полей)
- [ ] Написан и протестирован скрипт выгрузки
- [ ] Настроен webhook (если нужна автоматическая выгрузка)
- [ ] Проверены лимиты API
- [ ] Токен сохранён в `.env` (не в коде!)
- [ ] Настроена обработка ошибок и ретраев

---

## Типичные проблемы

### 401 Unauthorized
- Токен неверный или истёк
- Проверьте `Authorization` header

### 403 Forbidden
- Недостаточно прав у токена
- Пользователь не имеет доступа к форме

### 404 Not Found
- Неверный ID формы
- Форма удалена или недоступна

### 429 Too Many Requests
- Превышен лимит запросов
- Добавьте задержку между запросами

---

**Документ создан:** 2026-07-10  
**Версия Pyrus API:** v4

#!/usr/bin/env python3
"""
Получение структуры полей формы Pyrus для настройки маппинга
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('PYRUS_ACCESS_TOKEN')
LOGIN = os.getenv('PYRUS_LOGIN')
FORM_ID = 1327961


def auth():
    session = requests.Session()
    session.trust_env = False

    response = session.post(
        'https://api.pyrus.com/v4/auth',
        headers={'Content-Type': 'application/json'},
        json={'login': LOGIN, 'security_key': TOKEN}
    )

    access_token = response.json()['access_token']
    return session, access_token


def main():
    print("Getting Pyrus form structure...")

    session, access_token = auth()

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = session.get(f'https://api.pyrus.com/v4/forms/{FORM_ID}', headers=headers)
    form = response.json()

    print(f"\nForm: {form.get('name')}")
    print(f"\nFields ({len(form.get('fields', []))}):")
    print("-" * 60)

    for field in form.get('fields', []):
        field_id = field.get('id')
        name = field.get('name')
        field_type = field.get('type')
        print(f"ID {field_id:3d}: {name:40s} ({field_type})")

    # Save to JSON
    with open('pyrus_form_structure.json', 'w', encoding='utf-8') as f:
        json.dump(form, f, ensure_ascii=False, indent=2)

    print(f"\nStructure saved to: pyrus_form_structure.json")


if __name__ == '__main__':
    main()

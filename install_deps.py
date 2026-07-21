"""
Установка зависимостей напрямую без pip (из-за проблем с SOCKS прокси)
"""

import urllib.request
import ssl
import zipfile
import shutil
import os
import sys
import json

def get_site_packages():
    """Находим site-packages"""
    for path in sys.path:
        if 'site-packages' in path:
            return path
    import site
    return site.getusersitepackages()

def install_package(package_name, version, filename=None):
    """Скачивает и устанавливает пакет из PyPI"""
    if filename is None:
        filename = f"{package_name}-{version}-py3-none-any.whl"

    print(f"\n{'='*60}")
    print(f"Installing {package_name} {version}...")
    print(f"{'='*60}")

    # Получаем метаданные с PyPI
    try:
        url = f'https://pypi.org/pypi/{package_name}/{version}/json'
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context) as response:
            data = json.loads(response.read())

        # Находим py3 wheel
        wheel_url = None
        for file in data['urls']:
            if 'py3-none-any' in file['filename'] and file['packagetype'] == 'bdist_wheel':
                wheel_url = file['url']
                wheel_filename = file['filename']
                break
            elif 'py3' in file['filename'] and file['packagetype'] == 'bdist_wheel':
                wheel_url = file['url']
                wheel_filename = file['filename']

        if not wheel_url:
            print(f"  No wheel found for {package_name}")
            return False

        print(f"  Downloading from {wheel_filename}...")

        # Скачиваем
        urllib.request.urlretrieve(wheel_url, wheel_filename)
        print(f"  Downloaded: {wheel_filename}")

        # Извлекаем
        extract_dir = f"{package_name}_temp"
        with zipfile.ZipFile(wheel_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"  Extracted to {extract_dir}/")

        # Копируем в site-packages
        site_packages = get_site_packages()

        # Находим директорию пакета
        for root, dirs, files in os.walk(extract_dir):
            for d in dirs:
                if d.lower() == package_name.lower() or d.lower().startswith(package_name.lower() + '-'):
                    src = os.path.join(root, d)
                    # Вычисляем относительный путь
                    rel_path = os.path.relpath(src, extract_dir)
                    dst = os.path.join(site_packages, os.path.basename(src))

                    if os.path.isdir(src):
                        print(f"  Copying {os.path.basename(src)} -> site-packages")
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)

        print(f"  ✓ {package_name} installed successfully!")
        return True

    except Exception as e:
        print(f"  ✗ Error installing {package_name}: {e}")
        return False

def main():
    print("="*60)
    print("Quality Dashboard - Installing Dependencies")
    print("="*60)

    site_packages = get_site_packages()
    print(f"\nSite-packages: {site_packages}\n")

    # Зависимости в правильном порядке
    dependencies = [
        ("markupsafe", "2.1.3"),
        ("itsdangerous", "2.1.2"),
        ("click", "8.1.7"),
        ("Jinja2", "3.1.2"),
        ("blinker", "1.7.0"),
    ]

    success_count = 0
    for package, version in dependencies:
        if install_package(package, version):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Installed: {success_count}/{len(dependencies)} packages")
    print(f"{'='*60}")

    # Проверяем импорты
    print("\nTesting imports...")
    try:
        import markupsafe
        print(f"  ✓ markupsafe {markupsafe.__version__}")
    except ImportError as e:
        print(f"  ✗ markupsafe: {e}")

    try:
        import itsdangerous
        print(f"  ✓ itsdangerous {itsdangerous.__version__}")
    except ImportError as e:
        print(f"  ✗ itsdangerous: {e}")

    try:
        import click
        print(f"  ✓ click {click.__version__}")
    except ImportError as e:
        print(f"  ✗ click: {e}")

    try:
        import jinja2
        print(f"  ✓ jinja2 {jinja2.__version__}")
    except ImportError as e:
        print(f"  ✗ jinja2: {e}")

    try:
        import blinker
        print(f"  ✓ blinker {blinker.__version__}")
    except ImportError as e:
        print(f"  ✗ blinker: {e}")

    try:
        import werkzeug
        print(f"  ✓ werkzeug {werkzeug.__version__}")
    except ImportError as e:
        print(f"  ✗ werkzeug: {e}")

    try:
        import flask
        print(f"  ✓ flask {flask.__version__}")
    except ImportError as e:
        print(f"  ✗ flask: {e}")

if __name__ == "__main__":
    main()

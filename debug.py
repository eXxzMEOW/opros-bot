import os
import sys

print("=" * 50)
print("ДИАГНОСТИКА БОТА")
print("=" * 50)

# 1. Проверка текущей директории
print("1. Текущая директория:")
print(f"   {os.getcwd()}")
print(f"   Файлы в директории: {os.listdir('.')}")

# 2. Проверка tests.py
print("\n2. Проверка tests.py:")
try:
    # Пробуем импортировать
    from tests import tests_data

    print(f"   ✅ tests.py найден и импортирован")
    print(f"   Количество тестов: {len(tests_data)}")

    # Выводим список тестов
    for test_id, test in tests_data.items():
        print(f"   - ID: '{test_id}', Название: '{test['title']}'")
        print(f"     Вопросов: {len(test['questions'])}")

except ImportError as e:
    print(f"   ❌ Ошибка импорта: {e}")
    print(f"   Попытка загрузить вручную...")

    # Пробуем прочитать файл напрямую
    try:
        with open('tests.py', 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   Файл tests.py существует, размер: {len(content)} символов")

            # Ищем переменную tests_data
            if 'tests_data' in content:
                print("   ✅ Переменная tests_data найдена в файле")
                # Покажем начало файла
                print(f"   Первые 500 символов файла:")
                print(f"   {content[:500]}...")
            else:
                print("   ❌ Переменная tests_data НЕ найдена в файле")

    except FileNotFoundError:
        print("   ❌ Файл tests.py не найден!")
    except Exception as e:
        print(f"   ❌ Ошибка чтения файла: {e}")

except Exception as e:
    print(f"   ❌ Другая ошибка: {e}")

# 3. Проверка bot.py
print("\n3. Проверка bot.py:")
try:
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"   Размер файла: {len(content)} символов")

        # Проверяем импорт tests_data
        if 'from tests import tests_data' in content:
            print("   ✅ Импорт tests_data найден в bot.py")
        else:
            print("   ❌ Импорт tests_data НЕ найден в bot.py")

        # Ищем класс TestBot
        if 'class TestBot:' in content:
            print("   ✅ Класс TestBot найден")
        else:
            print("   ❌ Класс TestBot НЕ найден")

except Exception as e:
    print(f"   ❌ Ошибка чтения bot.py: {e}")

# 4. Проверка переменных окружения
print("\n4. Проверка .env файла:")
try:
    from dotenv import load_dotenv

    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if token:
        print(f"   ✅ BOT_TOKEN найден: {token[:10]}...")
    else:
        print("   ❌ BOT_TOKEN не найден в .env")
except Exception as e:
    print(f"   ❌ Ошибка загрузки .env: {e}")

print("\n" + "=" * 50)
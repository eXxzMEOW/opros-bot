# Пример тестов
tests_data = {
    'math_basics': {
        'title': 'Основы математики',
        'description': 'Проверка базовых знаний математики',
        'questions': [
            {
                'text': 'Сколько будет 2 + 2?',
                'options': ['3', '4', '5', '6'],
                'correct_answer': 1
            },
            {
                'text': 'Чему равен квадратный корень из 9?',
                'options': ['2', '3', '4', '5'],
                'correct_answer': 1
            },
            {
                'text': 'Что больше: π или 3.14?',
                'options': ['π', '3.14', 'Они равны', 'Не знаю'],
                'correct_answer': 0
            }
        ]
    },
    'python_basics': {
        'title': 'Основы Python',
        'description': 'Тест на знание основ Python',
        'questions': [
            {
                'text': 'Какой тип данных является неизменяемым?',
                'options': ['Список', 'Словарь', 'Кортеж', 'Множество'],
                'correct_answer': 2
            },
            {
                'text': 'Что выведет print(2 ** 3)?',
                'options': ['6', '8', '9', '23'],
                'correct_answer': 1
            },
            {
                'text': 'Как создать пустой список?',
                'options': ['{}', '[]', '()', 'set()'],
                'correct_answer': 1
            }
        ]
    }
}
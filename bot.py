import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from database import Database
from tests import tests_data

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)


class TestBot:
    def __init__(self):
        print("\n" + "=" * 60)
        print("🤖 ЗАГРУЗКА БОТА")
        print("=" * 60)

        # Инициализация базы данных
        try:
            self.db = Database()
            print("✅ База данных подключена")
        except Exception as e:
            print(f"⚠️ Ошибка БД: {e}")
            self.db = None

        # Загрузка тестов
        self.tests = tests_data
        print(f"✅ Загружено тестов: {len(self.tests)}")

        for test_id, test in self.tests.items():
            print(f"   ├─ {test['title']}")
            print(f"   └─ Вопросов: {len(test['questions'])}")

        print("=" * 60 + "\n")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        # Добавляем пользователя в БД
        if self.db:
            self.db.add_user(user.id, user.first_name)

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n"
            f"Я бот для прохождения тестов.\n\n"
            f"📚 Доступно тестов: {len(self.tests)}\n"
            f"❓ Всего вопросов: {sum(len(t['questions']) for t in self.tests.values())}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

    async def list_tests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список тестов"""
        query = update.callback_query
        await query.answer()

        print(f"\n📋 ПОЛЬЗОВАТЕЛЬ ЗАПРОСИЛ СПИСОК ТЕСТОВ")

        if not self.tests:
            await query.edit_message_text("📭 Нет доступных тестов")
            return

        keyboard = []
        for test_id, test in self.tests.items():
            question_count = len(test['questions'])
            button_text = f"{test['title']} ({question_count} вопр.)"
            callback_data = f'test_{test_id}'

            print(f"   Создаю кнопку: {button_text} -> {callback_data}")

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')])

        total_questions = sum(len(t['questions']) for t in self.tests.values())

        await query.edit_message_text(
            "📚 <b>Доступные тесты:</b>\n\n"
            f"📊 Всего тестов: <b>{len(self.tests)}</b>\n"
            f"❓ Всего вопросов: <b>{total_questions}</b>\n\n"
            "<i>Выберите тест:</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def handle_test_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора теста"""
        query = update.callback_query
        await query.answer()

        # Получаем callback_data (формат: test_math_test)
        callback_data = query.data

        print(f"\n🎯 ВЫБРАН ТЕСТ: {callback_data}")

        # Извлекаем test_id
        if not callback_data.startswith('test_'):
            await query.edit_message_text("❌ Ошибка формата")
            return

        test_id = callback_data[5:]  # Убираем "test_"
        print(f"   ID теста: '{test_id}'")
        print(f"   Доступные тесты: {list(self.tests.keys())}")

        # Ищем тест
        test = self.tests.get(test_id)

        if not test:
            await query.edit_message_text(f"❌ Тест '{test_id}' не найден")
            return

        print(f"   ✅ Найден тест: {test['title']}")

        # Инициализируем данные теста в context.user_data
        context.user_data['current_test'] = test_id
        context.user_data['current_question'] = 0
        context.user_data['answers'] = []
        context.user_data['score'] = 0

        print(f"   💾 Сохранено в user_data:")
        print(f"      current_test: {test_id}")
        print(f"      current_question: 0")

        # Показываем информацию о тесте
        keyboard = [
            [InlineKeyboardButton("✅ Начать тест", callback_data=f'begin_{test_id}')],
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data='list_tests')]
        ]

        question_count = len(test['questions'])

        await query.edit_message_text(
            f"📝 <b>{test['title']}</b>\n\n"
            f"📖 {test['description']}\n\n"
            f"❓ Вопросов: {question_count}\n"
            f"⏱️ Время: ~{question_count * 2} мин\n\n"
            f"<i>Нажмите 'Начать тест'</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать тест (обработка begin_)"""
        query = update.callback_query
        await query.answer()

        # Получаем callback_data (формат: begin_math_test)
        callback_data = query.data

        print(f"\n🚀 НАЧАЛО ТЕСТА: {callback_data}")

        # Извлекаем test_id
        test_id = callback_data[6:]  # Убираем "begin_"
        print(f"   ID теста: '{test_id}'")

        # Устанавливаем данные теста
        context.user_data['current_test'] = test_id
        context.user_data['current_question'] = 0
        context.user_data['answers'] = []
        context.user_data['score'] = 0

        # Показываем первый вопрос
        await self.show_question(update, context)

    async def show_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать текущий вопрос"""
        query = update.callback_query if hasattr(update, 'callback_query') else None

        # Получаем данные теста
        test_id = context.user_data.get('current_test')
        question_idx = context.user_data.get('current_question', 0)

        print(f"\n❓ ПОКАЗ ВОПРОСА")
        print(f"   test_id: '{test_id}'")
        print(f"   question_idx: {question_idx}")

        # Проверяем данные
        if not test_id or test_id not in self.tests:
            if query:
                await query.edit_message_text("❌ Ошибка: тест не найден")
            return

        test = self.tests[test_id]

        # Проверяем, есть ли еще вопросы
        if question_idx >= len(test['questions']):
            print(f"   🏁 Вопросов больше нет, завершаем тест")
            await self.show_results(update, context)
            return

        # Получаем вопрос
        question = test['questions'][question_idx]

        print(f"   📝 Вопрос {question_idx + 1}/{len(test['questions'])}")
        print(f"   Текст: {question['text'][:50]}...")

        # Создаем кнопки с вариантами ответов
        keyboard = []
        for idx, option in enumerate(question['options']):
            keyboard.append([InlineKeyboardButton(
                f"{idx + 1}. {option}",
                callback_data=f'answer_{idx}'
            )])

        # Добавляем кнопку отмены
        keyboard.append([InlineKeyboardButton("🚫 Отменить тест", callback_data='cancel_test')])

        # Показываем вопрос
        if query:
            await query.edit_message_text(
                f"📝 <b>Вопрос {question_idx + 1}/{len(test['questions'])}</b>\n\n"
                f"{question['text']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        else:
            # Если вызываем из другого места (например из handle_answer)
            await update.edit_message_text(
                f"📝 <b>Вопрос {question_idx + 1}/{len(test['questions'])}</b>\n\n"
                f"{question['text']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработать ответ на вопрос"""
        query = update.callback_query
        await query.answer()

        print(f"\n✅ ОБРАБОТКА ОТВЕТА")
        print(f"   Callback: {query.data}")

        # Получаем индекс ответа
        answer_idx = int(query.data.split('_')[1])
        print(f"   Ответ пользователя: {answer_idx}")

        # Получаем данные теста
        test_id = context.user_data.get('current_test')
        question_idx = context.user_data.get('current_question', 0)

        print(f"   Текущий тест: {test_id}")
        print(f"   Текущий вопрос: {question_idx}")

        # Проверяем данные
        if not test_id or test_id not in self.tests:
            await query.edit_message_text("❌ Ошибка: тест не найден")
            return

        test = self.tests[test_id]

        # Проверяем, что вопрос существует
        if question_idx >= len(test['questions']):
            print(f"   ⚠️ Вопросов больше нет")
            await self.show_results(update, context)
            return

        question = test['questions'][question_idx]

        # Проверяем правильность ответа
        is_correct = answer_idx == question['correct_answer']
        print(f"   Правильный ответ: {question['correct_answer']}")
        print(f"   Ответ верный: {is_correct}")

        # Увеличиваем счет если правильно
        if is_correct:
            context.user_data['score'] = context.user_data.get('score', 0) + 1

        # Сохраняем ответ
        context.user_data.setdefault('answers', []).append({
            'question': question['text'],
            'user_answer': answer_idx,
            'user_answer_text': question['options'][answer_idx],
            'correct_answer': question['correct_answer'],
            'correct_answer_text': question['options'][question['correct_answer']],
            'is_correct': is_correct
        })

        print(f"   🎯 Текущий счет: {context.user_data['score']}")

        # Переходим к следующему вопросу
        context.user_data['current_question'] = question_idx + 1
        print(f"   Следующий вопрос: {context.user_data['current_question']}")

        # Проверяем, есть ли еще вопросы
        if context.user_data['current_question'] < len(test['questions']):
            print(f"   ⏭️ Переход к следующему вопросу")
            # Показываем следующий вопрос
            await self.show_question(update, context)
        else:
            # Тест завершен
            print(f"   🏁 Тест завершен!")
            await self.show_results(update, context)

    async def show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать результаты теста"""
        query = update.callback_query if hasattr(update, 'callback_query') else None

        print(f"\n🏁 ПОКАЗ РЕЗУЛЬТАТОВ")

        # Получаем данные
        test_id = context.user_data.get('current_test')
        score = context.user_data.get('score', 0)
        answers = context.user_data.get('answers', [])

        print(f"   test_id: {test_id}")
        print(f"   score: {score}")
        print(f"   answers: {len(answers)}")

        if not test_id or test_id not in self.tests:
            if query:
                await query.edit_message_text("❌ Ошибка: тест не найден")
            return

        test = self.tests[test_id]
        total = len(test['questions'])
        percentage = round(score / total * 100, 1) if total > 0 else 0

        print(f"   total: {total}")
        print(f"   percentage: {percentage}%")

        # Сохраняем результат в БД
        if self.db and query:
            user_id = query.from_user.id
            self.db.save_result(user_id, test_id, score, total, answers)
            print(f"   💾 Результат сохранен в БД")

        # Формируем сообщение с результатами
        result_text = f"✅ <b>Тест завершен!</b>\n\n"
        result_text += f"📝 <b>{test['title']}</b>\n\n"
        result_text += f"📊 <b>Результаты:</b>\n"
        result_text += f"   🎯 Правильных ответов: <b>{score}/{total}</b>\n"
        result_text += f"   📈 Процент выполнения: <b>{percentage}%</b>\n\n"

        # Оценка результата
        if percentage == 100:
            result_text += "🏆 <b>Отличный результат! Идеально!</b> 🎉\n"
        elif percentage >= 80:
            result_text += "👍 <b>Очень хороший результат!</b>\n"
        elif percentage >= 70:
            result_text += "✅ <b>Хороший результат!</b>\n"
        elif percentage >= 50:
            result_text += "😐 <b>Неплохо, но можно лучше</b>\n"
        else:
            result_text += "📚 <b>Стоит повторить материал</b>\n"

        # Кнопки
        keyboard = [
            [InlineKeyboardButton("📋 К списку тестов", callback_data='list_tests')],
            [InlineKeyboardButton("🔍 Посмотреть ответы", callback_data='view_details')],
            [InlineKeyboardButton("🔄 Пройти еще раз", callback_data=f'test_{test_id}')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        if query:
            await query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    async def view_detailed_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детальные результаты"""
        query = update.callback_query
        await query.answer()

        print(f"\n🔍 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")

        answers = context.user_data.get('answers', [])
        detailed_text = "📖 <b>Детальные результаты:</b>\n\n"

        for i, answer in enumerate(answers, 1):
            status = "✅" if answer['is_correct'] else "❌"
            detailed_text += f"<b>Вопрос {i}:</b> {answer['question']}\n"
            detailed_text += f"   Ваш ответ: {answer['user_answer_text']}\n"
            detailed_text += f"   {status} Правильный ответ: {answer['correct_answer_text']}\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ Назад к результатам", callback_data='back_to_results')]]

        await query.edit_message_text(
            detailed_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def back_to_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться к результатам теста"""
        query = update.callback_query
        await query.answer()

        print(f"\n⬅️ ВОЗВРАТ К РЕЗУЛЬТАТАМ")

        await self.show_results(update, context)

    async def cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить тест"""
        query = update.callback_query
        await query.answer()

        print(f"\n🚫 ОТМЕНА ТЕСТА")

        # Очищаем данные
        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        await query.edit_message_text(
            "❌ <b>Тест отменен</b>\n\n"
            "Все данные удалены.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        query = update.callback_query
        await query.answer()

        print(f"\n🏠 ВОЗВРАТ В ГЛАВНОЕ МЕНЮ")

        # Очищаем данные
        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')]
        ]

        await query.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def my_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать историю результатов пользователя"""
        query = update.callback_query
        await query.answer()

        print(f"\n📊 ИСТОРИЯ РЕЗУЛЬТАТОВ")

        if not self.db:
            await query.edit_message_text("❌ База данных не подключена")
            return

        user_id = query.from_user.id
        results = self.db.get_user_results(user_id)

        if not results:
            text = "📭 <b>У вас еще нет результатов тестов</b>\n\n"
            text += "Пройти тесты можно через меню:\n"
            text += "📋 Список тестов → Выберите тест → Начать тест"
        else:
            text = "📊 <b>Ваши результаты:</b>\n\n"
            for i, result in enumerate(results[:5], 1):
                test_title = self.tests.get(result['test_id'], {}).get('title', 'Неизвестный тест')
                text += f"<b>{i}. {test_title}</b>\n"
                text += f"   📅 {result['date']}\n"
                text += f"   🎯 {result['score']}/{result['total']}\n"
                text += f"   📈 {result['percentage']}%\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    def run(self):
        """Запуск бота"""
        if not TOKEN:
            print("❌ ОШИБКА: BOT_TOKEN не найден!")
            print("   Создайте файл .env с содержимым:")
            print("   BOT_TOKEN=ваш_токен_от_BotFather")
            return

        print("🚀 Запускаю бота...")
        print(f"   Токен: {TOKEN[:10]}...")
        print(f"   Тестов: {len(self.tests)}")
        print("\n" + "=" * 60)
        print("🤖 Бот запущен и готов к работе!")
        print("   Напишите /start в Telegram")
        print("   Для остановки: Ctrl+C")
        print("=" * 60 + "\n")

        application = Application.builder().token(TOKEN).build()

        # Регистрация обработчиков
        application.add_handler(CommandHandler('start', self.start))

        # Обработчики callback-запросов
        application.add_handler(CallbackQueryHandler(self.list_tests, pattern='^list_tests$'))
        application.add_handler(CallbackQueryHandler(self.handle_test_selection, pattern='^test_'))
        application.add_handler(CallbackQueryHandler(self.start_test, pattern='^begin_'))
        application.add_handler(CallbackQueryHandler(self.handle_answer, pattern='^answer_'))
        application.add_handler(CallbackQueryHandler(self.view_detailed_results, pattern='^view_details$'))
        application.add_handler(CallbackQueryHandler(self.back_to_results, pattern='^back_to_results$'))
        application.add_handler(CallbackQueryHandler(self.cancel_test, pattern='^cancel_test$'))
        application.add_handler(CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$'))
        application.add_handler(CallbackQueryHandler(self.my_results, pattern='^my_results$'))

        # Для отладки: обработчик всех callback
        application.add_handler(CallbackQueryHandler(self.debug_callback))

        application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def debug_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отладочный обработчик для всех callback"""
        query = update.callback_query
        print(f"\n🔍 DEBUG CALLBACK: {query.data}")
        print(f"   user_data: {context.user_data}")
        await query.answer(f"Получен: {query.data}")


if __name__ == '__main__':
    bot = TestBot()
    bot.run()
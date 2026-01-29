import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from dotenv import load_dotenv
from database import Database
from tests import tests_data

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

# Состояния для ConversationHandler
CHOOSING_TEST, SOLVING_TEST, VIEW_RESULTS = range(3)


class TestBot:
    def __init__(self):
        print("\n" + "=" * 60)
        print("🤖 ИНИЦИАЛИЗАЦИЯ ТЕСТОВОГО БОТА")
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

        # Вывод информации о тестах для отладки
        for test_id, test in self.tests.items():
            print(f"   ├─ ID: '{test_id}'")
            print(f"   ├─ Название: {test['title']}")
            print(f"   ├─ Вопросов: {len(test['questions'])}")
            print(f"   └─ Callback: test_{test_id}")

        print("=" * 60 + "\n")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        # Добавляем пользователя в БД
        if self.db:
            self.db.add_user(user.id, user.first_name)

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        query = update.callback_query
        await query.answer()

        help_text = (
            "📚 <b>Помощь по боту:</b>\n\n"
            "1. <b>📋 Список тестов</b> - выбрать тест для прохождения\n"
            "2. <b>📊 Мои результаты</b> - посмотреть историю прохождения\n"
            "3. <b>❓ Помощь</b> - это сообщение\n\n"
            "📝 <b>Как пройти тест:</b>\n"
            "1. Выберите тест из списка\n"
            "2. Нажмите 'Начать тест'\n"
            "3. Отвечайте на вопросы, выбирая варианты\n"
            "4. В конце увидите результат\n\n"
            "🔄 <b>Команды:</b>\n"
            "/start - начать работу с ботом\n"
            "/help - показать это сообщение"
        )

        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]

        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def list_tests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список тестов"""
        query = update.callback_query
        await query.answer()

        print(f"\n📋 ПОЛЬЗОВАТЕЛЬ ЗАПРОСИЛ СПИСОК ТЕСТОВ")

        if not self.tests:
            await query.edit_message_text(
                "📭 Тесты еще не добавлены!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
                ])
            )
            return

        keyboard = []
        for test_id, test in self.tests.items():
            question_count = len(test['questions'])
            button_text = f"{test['title']} ({question_count} вопр.)"
            callback_data = f'test_{test_id}'

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
            "<i>Выберите тест для прохождения:</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return CHOOSING_TEST

    async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать выбранный тест"""
        query = update.callback_query
        await query.answer()

        # Получаем callback_data
        callback_data = query.data

        print(f"\n🎯 ПОЛЬЗОВАТЕЛЬ ВЫБРАЛ ТЕСТ: {callback_data}")

        # Извлекаем test_id
        if not callback_data.startswith('test_'):
            await query.edit_message_text("❌ Ошибка формата")
            return

        test_id = callback_data[5:]  # Убираем "test_"
        print(f"   test_id: '{test_id}'")

        # Ищем тест
        test = self.tests.get(test_id)

        if not test:
            await query.edit_message_text(f"❌ Тест '{test_id}' не найден")
            return

        print(f"   ✅ Найден: {test['title']}")

        # Сохраняем информацию о текущем тесте
        context.user_data['current_test'] = test_id
        context.user_data['current_question'] = 0
        context.user_data['answers'] = []
        context.user_data['score'] = 0

        print(f"   💾 Сохранено в user_data")

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

    async def show_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать вопрос"""
        query = update.callback_query
        await query.answer()

        print(f"\n❓ ОБРАБОТКА BEGIN_: {query.data}")

        # Если пришел begin_, извлекаем test_id
        if query.data.startswith('begin_'):
            test_id = query.data[6:]  # Убираем "begin_"
            print(f"   Начинаем тест: {test_id}")

            # Устанавливаем начальные значения
            context.user_data['current_test'] = test_id
            context.user_data['current_question'] = 0
            context.user_data['answers'] = []
            context.user_data['score'] = 0

        # Получаем данные из контекста
        test_id = context.user_data.get('current_test')
        question_idx = context.user_data.get('current_question', 0)

        print(f"   test_id: '{test_id}'")
        print(f"   question_idx: {question_idx}")

        # Проверяем данные
        if not test_id or test_id not in self.tests:
            print(f"   ❌ Ошибка: тест не найден")
            await query.edit_message_text("❌ Ошибка: тест не найден")
            return

        test = self.tests[test_id]

        # Проверяем, есть ли еще вопросы
        if question_idx >= len(test['questions']):
            print(f"   ⚠️ Вопросов больше нет")
            await self.show_results(update, context)
            return

        question = test['questions'][question_idx]

        print(f"   📝 Вопрос {question_idx + 1}/{len(test['questions'])}")

        # Создаем клавиатуру с вариантами ответов
        keyboard = []
        for idx, option in enumerate(question['options']):
            keyboard.append([InlineKeyboardButton(
                f"{idx + 1}. {option}",
                callback_data=f'answer_{idx}'
            )])

        # Добавляем кнопку отмены
        keyboard.append([InlineKeyboardButton("🚫 Завершить тест", callback_data='cancel_test')])

        await query.edit_message_text(
            f"📝 <b>Вопрос {question_idx + 1}/{len(test['questions'])}</b>\n\n"
            f"{question['text']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return SOLVING_TEST

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработать ответ пользователя"""
        query = update.callback_query
        await query.answer()

        # Получаем данные
        test_id = context.user_data['current_test']
        question_idx = context.user_data['current_question']
        answer_idx = int(query.data.split('_')[1])

        print(f"\n✅ ОТВЕТ: test={test_id}, question={question_idx}, answer={answer_idx}")

        test = self.tests[test_id]
        question = test['questions'][question_idx]

        # Проверяем ответ
        is_correct = answer_idx == question['correct_answer']

        if is_correct:
            context.user_data['score'] += 1

        # Сохраняем ответ
        context.user_data['answers'].append({
            'question': question['text'],
            'user_answer': answer_idx,
            'correct_answer': question['correct_answer'],
            'is_correct': is_correct,
            'user_answer_text': question['options'][answer_idx],
            'correct_answer_text': question['options'][question['correct_answer']]
        })

        # Переходим к следующему вопросу
        context.user_data['current_question'] += 1

        if context.user_data['current_question'] < len(test['questions']):
            await self.show_question(update, context)
        else:
            # Тест завершен
            print(f"   🏁 Тест завершен!")
            await self.show_results(update, context)

    async def show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать результаты теста"""
        test_id = context.user_data['current_test']
        test = self.tests[test_id]
        score = context.user_data['score']
        total = len(test['questions'])
        percentage = round(score / total * 100, 1) if total > 0 else 0

        print(f"\n🏁 РЕЗУЛЬТАТЫ: {score}/{total} ({percentage}%)")

        # Сохраняем результат в БД
        if self.db:
            user_id = update.effective_user.id
            self.db.save_result(
                user_id,
                test_id,
                score,
                total,
                context.user_data['answers']
            )

        # Формируем сообщение
        result_text = f"✅ <b>Тест завершен!</b>\n\n"
        result_text += f"📝 <b>{test['title']}</b>\n\n"
        result_text += f"📊 <b>Результаты:</b>\n"
        result_text += f"   🎯 Правильных: <b>{score}/{total}</b>\n"
        result_text += f"   📈 Процент: <b>{percentage}%</b>\n\n"

        # Оценка результата
        if percentage == 100:
            result_text += "🏆 <b>Отлично! Идеально!</b> 🎉\n"
        elif percentage >= 70:
            result_text += "👍 <b>Хороший результат!</b>\n"
        else:
            result_text += "📚 <b>Попробуйте еще раз</b>\n"

        result_text += f"\n<i>Выберите действие:</i>"

        # Кнопки
        keyboard = [
            [InlineKeyboardButton("📋 К списку тестов", callback_data='list_tests')],
            [InlineKeyboardButton("🔍 Посмотреть ответы", callback_data='view_details')],
            [InlineKeyboardButton("🔄 Пройти еще раз", callback_data=f'test_{test_id}')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        query = update.callback_query
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return VIEW_RESULTS

    async def view_detailed_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детальные результаты"""
        query = update.callback_query
        await query.answer()

        print(f"\n🔍 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ")

        answers = context.user_data['answers']
        detailed_text = "📖 <b>Детальные результаты:</b>\n\n"

        for i, answer in enumerate(answers, 1):
            status = "✅" if answer['is_correct'] else "❌"
            detailed_text += f"<b>Вопрос {i}:</b> {answer['question']}\n"
            detailed_text += f"   Ваш ответ: {answer['user_answer_text']}\n"
            detailed_text += f"   {status} Правильный: {answer['correct_answer_text']}\n\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к результатам", callback_data='back_to_results')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        await query.edit_message_text(
            detailed_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def cancel_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить тест"""
        query = update.callback_query
        await query.answer()

        print(f"\n🚫 ТЕСТ ОТМЕНЕН")

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        await query.edit_message_text(
            "❌ <b>Тест отменен</b>\n\n"
            "Прогресс удален.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        query = update.callback_query
        await query.answer()

        print(f"\n🏠 ВОЗВРАТ В ГЛАВНОЕ МЕНЮ")

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]

        await query.edit_message_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    async def my_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать историю результатов пользователя"""
        query = update.callback_query
        await query.answer()

        print(f"\n📊 РЕЗУЛЬТАТЫ ПОЛЬЗОВАТЕЛЯ")

        user_id = update.effective_user.id
        results = self.db.get_user_results(user_id) if self.db else []

        print(f"   Найдено: {len(results)} результатов")

        if not results:
            text = "📭 <b>У вас еще нет результатов тестов</b>"
        else:
            text = "📊 <b>Ваши результаты:</b>\n\n"
            for i, result in enumerate(results[:5], 1):
                test_title = self.tests.get(result['test_id'], {}).get('title', 'Неизвестный тест')
                text += f"<b>{i}. {test_title}</b>\n"
                text += f"   📅 {result['date']}\n"
                text += f"   🎯 {result['score']}/{result['total']} ({result['percentage']}%)\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

    async def back_to_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться к результатам теста"""
        query = update.callback_query
        await query.answer()

        print(f"\n⬅️ ВОЗВРАТ К РЕЗУЛЬТАТАМ")

        await self.show_results(update, context)

    def run(self):
        """Запуск бота"""
        if not TOKEN:
            print("❌ ОШИБКА: BOT_TOKEN не найден!")
            return

        print("🚀 Запускаю бота...")

        application = Application.builder().token(TOKEN).build()

        # ВАЖНО: ConversationHandler с правильными состояниями
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.list_tests, pattern='^list_tests$')],
            states={
                CHOOSING_TEST: [
                    CallbackQueryHandler(self.start_test, pattern='^test_'),
                    CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$')
                ],
                SOLVING_TEST: [
                    CallbackQueryHandler(self.handle_answer, pattern='^answer_'),
                    CallbackQueryHandler(self.show_question, pattern='^begin_'),  # ← ЭТО ВАЖНО!
                    CallbackQueryHandler(self.cancel_test, pattern='^cancel_test$')
                ],
                VIEW_RESULTS: [
                    CallbackQueryHandler(self.view_detailed_results, pattern='^view_details$'),
                    CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$'),
                    CallbackQueryHandler(self.back_to_results, pattern='^back_to_results$')
                ]
            },
            fallbacks=[
                CommandHandler('start', self.start),
                CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$')
            ]
        )

        # Регистрация обработчиков
        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('help', self.start))

        application.add_handler(conv_handler)

        # Отдельные обработчики для callback
        application.add_handler(CallbackQueryHandler(self.my_results, pattern='^my_results$'))
        application.add_handler(CallbackQueryHandler(self.help_command, pattern='^help$'))
        application.add_handler(CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$'))

        # Добавьте этот обработчик для отладки
        application.add_handler(CallbackQueryHandler(self.show_question, pattern='^begin_'))

        print("\n" + "=" * 60)
        print("🤖 Бот запущен!")
        print("=" * 60 + "\n")

        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


if __name__ == '__main__':
    bot = TestBot()
    bot.run()
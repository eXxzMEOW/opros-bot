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
        self.db = Database()
        self.tests = tests_data

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_user(user.id, user.first_name)

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для прохождения тестов.\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

    async def list_tests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список тестов"""
        query = update.callback_query
        await query.answer()

        keyboard = []
        for test_id, test in self.tests.items():
            keyboard.append([InlineKeyboardButton(
                test['title'],
                callback_data=f'test_{test_id}'
            )])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')])

        await query.edit_message_text(
            "📚 Доступные тесты:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING_TEST

    async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать выбранный тест"""
        query = update.callback_query
        await query.answer()

        test_id = query.data.split('_')[1]
        test = self.tests.get(test_id)

        if not test:
            await query.edit_message_text("Тест не найден!")
            return

        context.user_data['current_test'] = test_id
        context.user_data['current_question'] = 0
        context.user_data['answers'] = []
        context.user_data['score'] = 0

        # Показываем описание теста
        keyboard = [[InlineKeyboardButton("Начать тест", callback_data=f'begin_{test_id}')]]

        await query.edit_message_text(
            f"📝 {test['title']}\n\n"
            f"Описание: {test['description']}\n"
            f"Количество вопросов: {len(test['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать вопрос"""
        query = update.callback_query
        await query.answer()

        test_id = context.user_data['current_test']
        question_idx = context.user_data['current_question']
        test = self.tests[test_id]
        question = test['questions'][question_idx]

        # Создаем клавиатуру с вариантами ответов
        keyboard = []
        for idx, option in enumerate(question['options']):
            keyboard.append([InlineKeyboardButton(
                option,
                callback_data=f'answer_{idx}'
            )])

        await query.edit_message_text(
            f"Вопрос {question_idx + 1}/{len(test['questions'])}\n\n"
            f"{question['text']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SOLVING_TEST

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработать ответ пользователя"""
        query = update.callback_query
        await query.answer()

        test_id = context.user_data['current_test']
        question_idx = context.user_data['current_question']
        answer_idx = int(query.data.split('_')[1])

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
            'is_correct': is_correct
        })

        # Переходим к следующему вопросу
        context.user_data['current_question'] += 1

        if context.user_data['current_question'] < len(test['questions']):
            await self.show_question(update, context)
        else:
            # Тест завершен
            await self.show_results(update, context)

    async def show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать результаты теста"""
        test_id = context.user_data['current_test']
        test = self.tests[test_id]
        score = context.user_data['score']
        total = len(test['questions'])

        # Сохраняем результат в БД
        user_id = update.effective_user.id
        self.db.save_result(
            user_id,
            test_id,
            score,
            total,
            context.user_data['answers']
        )

        # Формируем детали результатов
        result_text = f"✅ Тест завершен!\n\n"
        result_text += f"🎯 Ваш результат: {score}/{total}\n"
        result_text += f"📊 Процент: {round(score / total * 100, 1)}%\n\n"

        if score == total:
            result_text += "Отличный результат! 🎉\n"
        elif score / total >= 0.7:
            result_text += "Хороший результат! 👍\n"
        else:
            result_text += "Попробуйте еще раз! 💪\n"

        # Кнопки
        keyboard = [
            [InlineKeyboardButton("📋 К списку тестов", callback_data='list_tests')],
            [InlineKeyboardButton("🔍 Посмотреть ответы", callback_data='view_details')],
            [InlineKeyboardButton("🏠 В главное меню", callback_data='back_to_menu')]
        ]

        query = update.callback_query
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return VIEW_RESULTS

    async def view_detailed_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детальные результаты"""
        query = update.callback_query
        await query.answer()

        answers = context.user_data['answers']
        detailed_text = "📖 Детальные результаты:\n\n"

        for i, answer in enumerate(answers, 1):
            status = "✅" if answer['is_correct'] else "❌"
            detailed_text += f"{i}. {answer['question']}\n"
            detailed_text += f"   Ваш ответ: {answer['user_answer'] + 1}\n"
            detailed_text += f"   {status} Правильный ответ: {answer['correct_answer'] + 1}\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_results')]]

        await query.edit_message_text(
            detailed_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вернуться в главное меню"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("📋 Список тестов", callback_data='list_tests')],
            [InlineKeyboardButton("📊 Мои результаты", callback_data='my_results')]
        ]

        await query.edit_message_text(
            "Главное меню:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    async def my_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать историю результатов пользователя"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        results = self.db.get_user_results(user_id)

        if not results:
            text = "У вас еще нет результатов тестов."
        else:
            text = "📊 Ваши результаты:\n\n"
            for result in results:
                test_title = self.tests.get(result['test_id'], {}).get('title', 'Неизвестный тест')
                text += f"📝 {test_title}\n"
                text += f"   Дата: {result['date']}\n"
                text += f"   Результат: {result['score']}/{result['total']}\n"
                text += f"   Процент: {result['percentage']}%\n\n"

        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.list_tests, pattern='^list_tests$')],
            states={
                CHOOSING_TEST: [
                    CallbackQueryHandler(self.start_test, pattern='^test_'),
                    CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$')
                ],
                SOLVING_TEST: [
                    CallbackQueryHandler(self.handle_answer, pattern='^answer_'),
                    CallbackQueryHandler(self.show_question, pattern='^begin_')
                ],
                VIEW_RESULTS: [
                    CallbackQueryHandler(self.view_detailed_results, pattern='^view_details$'),
                    CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$'),
                    CallbackQueryHandler(self.show_results, pattern='^back_to_results$')
                ]
            },
            fallbacks=[CommandHandler('start', self.start)]
        )

        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(self.my_results, pattern='^my_results$'))
        application.add_handler(CallbackQueryHandler(self.back_to_menu, pattern='^back_to_menu$'))

        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = TestBot()
    bot.run()
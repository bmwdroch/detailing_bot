"""
Модуль обработчиков команд для работы с транзакциями и кассой.
Включает обработку команд для добавления транзакций, просмотра отчетов и управления финансами.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from core.models import TransactionType
from services import db
from services.analytics.analytics import AnalyticsService
from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService
from utils.formatters import format_money
from utils.keyboards import (
    get_cancel_keyboard,
    get_inline_cancel_keyboard, 
    get_confirmation_keyboard,
    get_main_menu_keyboard,
    get_services_keyboard,
    get_transaction_type_keyboard,
)
from utils.validators import validate_amount, validate_category

router = Router(name="payment")
logger = logging.getLogger(__name__)

# В начале файла, в блоке импорта и определения состояний
class PaymentStates(StatesGroup):
    SELECT_TYPE = State()         # Выбор типа транзакции
    ENTER_AMOUNT = State()        # Ввод суммы
    SELECT_SERVICE = State()      # Выбор услуги или "Другое"
    ENTER_CATEGORY = State()      # Ввод категории (если выбрано "Другое")
    ENTER_DESCRIPTION = State()   # Ввод описания
    CONFIRM_TRANSACTION = State() # Подтверждение транзакции

class TransactionData:
    def __init__(self):
        self.type: Optional[TransactionType] = None
        self.amount: Optional[float] = None
        # Новое поле для хранения выбранной услуги (если выбрана)
        self.service_id: Optional[int] = None  
        self.category: Optional[str] = None
        self.description: Optional[str] = None

@router.message(Command("transactions"))
@router.message(F.text == "💰 Касса")
async def cmd_transactions(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды для работы с кассой.
    Используем ReplyKeyboardMarkup для нового сообщения.
    """
    if not await check_admin_rights(message):
        await message.answer("У вас нет прав для работы с кассой")
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить транзакцию")],
            [KeyboardButton(text="📊 Дневной отчет"), KeyboardButton(text="📈 Недельный отчет")],
            [KeyboardButton(text="📋 Месячный отчет")],  # удалена лишняя кнопка "🔍 Статистика"
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.message(F.text == "➕ Добавить транзакцию")
async def cmd_add_transaction(message: Message, state: FSMContext) -> None:
    """
    Начало процесса добавления транзакции
    """
    if not await check_admin_rights(message):
        return

    # Инициализируем хранение данных
    await state.update_data(transaction=TransactionData())
    
    await message.answer(
        "Выберите тип транзакции:",
        reply_markup=get_transaction_type_keyboard()
    )
    await state.set_state(PaymentStates.SELECT_TYPE)


@router.callback_query(PaymentStates.SELECT_TYPE)
async def process_type_selection(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Обработка выбора типа транзакции.
    При редактировании сообщения теперь используется inline‑клавиатура отмены.
    """
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "Действие отменено",
            reply_markup=None
        )
        return

    # Получаем тип транзакции из callback
    transaction_type = TransactionType(callback.data.split(":")[1])
    
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]
    transaction.type = transaction_type
    await state.update_data(transaction=transaction)

    # Запрашиваем сумму; используем inline‑клавиатуру отмены
    await callback.message.edit_text(
        "Введите сумму транзакции:",
        reply_markup=get_inline_cancel_keyboard()
    )
    await state.set_state(PaymentStates.ENTER_AMOUNT)

@router.message(PaymentStates.ENTER_AMOUNT)
async def process_amount(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода суммы транзакции
    """
    amount = message.text.strip()

    # Валидация суммы
    is_valid, error = validate_amount(amount)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите сумму:"
        )
        return

    # Сохраняем сумму
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]
    transaction.amount = float(amount)
    await state.update_data(transaction=transaction)

    # Получаем список активных услуг из БД
    # Для этого нам понадобится доступ к объекту БД (DatabaseManager)
    # (предполагается, что он передаётся как аргумент в обработчик)
    services_list = await db.get_active_services()
    # Можно использовать существующую функцию, адаптируя её (например, добавив кнопку "Другое")
    keyboard = get_services_keyboard(services_list)
    # Добавляем дополнительную кнопку "Другое" для ручного ввода категории
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="Другое", callback_data="service:other")]
    )
    await message.answer(
        "Выберите услугу, к которой относится транзакция, или нажмите «Другое» для ввода своей категории:",
        reply_markup=keyboard
    )
    await state.set_state(PaymentStates.SELECT_SERVICE)

@router.message(PaymentStates.ENTER_CATEGORY)
async def process_category(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода категории
    """
    category = message.text.strip()

    # Валидация категории
    is_valid, error = validate_category(category)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите категорию:"
        )
        return

    # Сохраняем категорию
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]
    transaction.category = category
    await state.update_data(transaction=transaction)

    # Запрашиваем описание
    await message.answer(
        "Введите описание транзакции:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PaymentStates.ENTER_DESCRIPTION)


@router.message(PaymentStates.ENTER_DESCRIPTION)
async def process_description(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода описания и подтверждение транзакции
    """
    description = message.text.strip()

    # Сохраняем описание
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]
    transaction.description = description
    await state.update_data(transaction=transaction)

    # Показываем подтверждение
    await show_transaction_confirmation(message, transaction)
    await state.set_state(PaymentStates.CONFIRM_TRANSACTION)


async def show_transaction_confirmation(
    message: Message,
    transaction: TransactionData
) -> None:
    """
    Показ подтверждения транзакции
    """
    type_emoji = "💰" if transaction.type == TransactionType.INCOME else "💸"
    
    confirmation_text = (
        f"{type_emoji} Подтвердите транзакцию:\n\n"
        f"Тип: {transaction.type.value}\n"
        f"Сумма: {format_money(transaction.amount)}\n"
        f"Категория: {transaction.category}\n"
        f"Описание: {transaction.description}\n\n"
        "Всё верно?"
    )

    await message.answer(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )

@router.callback_query(PaymentStates.CONFIRM_TRANSACTION)
async def process_transaction_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    db: DatabaseManager,
    notifications: NotificationService  
) -> None:
    """
    Обработка подтверждения транзакции
    """
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "Транзакция отменена",
            reply_markup=None
        )
        return

    # Получаем данные транзакции
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]

    # Добавляем транзакцию в БД
    success, error, transaction_obj = await db.add_transaction(
        amount=str(transaction.amount),
        type_=transaction.type.value,
        category=transaction.category,
        description=transaction.description
    )

    if not success:
        await callback.message.edit_text(
            f"Ошибка при создании транзакции: {error}\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=None
        )
        await state.clear()
        return

    # Отправляем уведомление о новой транзакции в админку
    admin_chat_id = callback.bot.config.admin_ids[0] if callback.bot.config.admin_ids else None
    if admin_chat_id:
        await notifications.notify_new_transaction(transaction_obj, admin_chat_id)

    # Завершаем процесс
    await callback.message.edit_text(
        "✅ Транзакция успешно добавлена!",
        reply_markup=None
    )
    await state.clear()
    
@router.message(F.text == "📊 Дневной отчет")
async def cmd_daily_report(
    message: Message,
    db: DatabaseManager,
    analytics: AnalyticsService
) -> None:
    """
    Формирование дневного отчета
    """
    if not await check_admin_rights(message):
        await message.answer("У вас нет прав для работы с кассой")
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = await analytics.get_daily_stats(today)

    if not stats or stats['appointments']['total'] == 0:
        await message.answer("Нет записей за выбранный день.", reply_markup=get_main_menu_keyboard())
        return

    report_text = format_daily_report(stats)
    await message.answer(report_text)

@router.message(F.text == "📈 Недельный отчет")
async def cmd_weekly_report(
    message: Message,
    db: DatabaseManager,
    analytics: AnalyticsService
) -> None:
    """
    Формирование недельного отчета
    """
    if not await check_admin_rights(message):
        return

    # Получаем статистику за неделю
    today = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_date = today - timedelta(days=7)
    stats = await analytics.get_period_stats(start_date, today)

    if not stats:
        await message.answer(
            "Ошибка при формировании отчета"
        )
        return

    # Формируем текст отчета
    report_text = format_period_report(stats, "неделю")
    await message.answer(report_text)


@router.message(F.text == "📋 Месячный отчет")
async def cmd_monthly_report(
    message: Message,
    db: DatabaseManager,
    analytics: AnalyticsService
) -> None:
    """
    Формирование месячного отчета
    """
    if not await check_admin_rights(message):
        return

    # Получаем статистику за месяц
    today = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_date = today - timedelta(days=30)
    stats = await analytics.get_period_stats(start_date, today)

    if not stats:
        await message.answer(
            "Ошибка при формировании отчета"
        )
        return

    # Формируем текст отчета
    report_text = format_period_report(stats, "месяц")
    await message.answer(report_text)


def format_daily_report(stats: Dict) -> str:
    """
    Форматирование дневного отчета
    """
    return (
        f"📊 Отчет за {stats['date'].strftime('%d.%m.%Y')}\n\n"
        f"Записи:\n"
        f"- Всего: {stats['appointments']['total']}\n"
        f"- Выполнено: {stats['appointments']['completed']}\n"
        f"- Отменено: {stats['appointments']['cancelled']}\n"
        f"- Конверсия: {stats['appointments']['conversion']}%\n\n"
        f"Финансы:\n"
        f"- Доход: {format_money(stats['finances']['income'])}\n"
        f"- Расход: {format_money(stats['finances']['expense'])}\n"
        f"- Прибыль: {format_money(stats['finances']['profit'])}"
    )


def format_period_report(stats: Dict, period_name: str) -> str:
    """
    Форматирование отчета за период
    """
    return (
        f"📈 Отчет за {period_name}\n"
        f"Период: {stats['period']['start'].strftime('%d.%m.%Y')} - "
        f"{stats['period']['end'].strftime('%d.%m.%Y')}\n\n"
        f"Общие показатели:\n"
        f"- Записей: {stats['total']['appointments']}\n"
        f"- Выполнено: {stats['total']['completed']}\n"
        f"- Отменено: {stats['total']['cancelled']}\n"
        f"- Конверсия: {stats['total']['conversion']}%\n\n"
        f"Финансы:\n"
        f"- Общий доход: {format_money(stats['total']['income'])}\n"
        f"- Общий расход: {format_money(stats['total']['expense'])}\n"
        f"- Общая прибыль: {format_money(stats['total']['profit'])}\n\n"
        f"Средние показатели:\n"
        f"- Записей в день: {stats['average']['daily_appointments']}\n"
        f"- Доход в день: {format_money(stats['average']['daily_income'])}\n"
        f"- Средний чек: {format_money(stats['average']['check'])}"
    )


async def check_admin_rights(message: Message) -> bool:
    try:
        user_id = message.from_user.id
        bot = message.bot
        admin_ids = bot.config.admin_ids
        return user_id in admin_ids
    except Exception as e:
        logger.error(f"Error checking admin rights: {e}")
        return False
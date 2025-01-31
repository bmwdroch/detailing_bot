"""
Модуль обработчиков команд административной части бота.
Включает обработку команд для управления записями, услугами и общими настройками.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup

from core.models import AppointmentStatus, Service
from services.analytics.analytics import AnalyticsService
from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService
from utils.formatters import (
    format_appointment_info, format_datetime, format_money,
    format_service_info
)
from utils.keyboards import (
    get_admin_menu_keyboard, get_appointment_actions_keyboard,
    get_cancel_keyboard, get_confirmation_keyboard,
    get_pagination_keyboard, get_service_edit_keyboard
)
from utils.validators import (
    validate_service_description, validate_service_duration,
    validate_service_name, validate_service_price
)

# Создаем роутер для административных обработчиков
router = Router(name="admin")

# Настраиваем логгер
logger = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    """Состояния FSM для административных сценариев"""
    
    # Управление услугами
    ADD_SERVICE_NAME = State()
    ADD_SERVICE_DESCRIPTION = State()
    ADD_SERVICE_PRICE = State()
    ADD_SERVICE_DURATION = State()
    CONFIRM_SERVICE = State()
    
    # Управление записями
    EDIT_APPOINTMENT = State()
    RESCHEDULE_DATE = State()
    RESCHEDULE_TIME = State()
    ADD_COMMENT = State()

    EDIT_CONTACTS = State()

@router.message(Command("edit_contacts"))
@router.message(F.text == "✏️ Изменить контакты")
async def cmd_edit_contacts(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """Начало редактирования контактов"""
    if not await check_admin(message):
        return

    # Получаем текущие контакты
    current_contacts = await db.get_setting("contacts")
    
    await message.answer(
        "Текущие контакты:\n\n"
        f"{current_contacts}\n\n"
        "Отправьте новый текст контактов или нажмите отмену:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.EDIT_CONTACTS)

@router.message(AdminStates.EDIT_CONTACTS)
async def process_edit_contacts(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """Обработка нового текста контактов"""
    new_contacts = message.text.strip()
    
    # Валидация текста
    if len(new_contacts) < 10:
        await message.answer(
            "Текст контактов слишком короткий. "
            "Пожалуйста, отправьте более подробную информацию:"
        )
        return
        
    if len(new_contacts) > 1000:
        await message.answer(
            "Текст контактов слишком длинный. "
            "Пожалуйста, сократите информацию:"
        )
        return

    # Обновляем контакты
    success, error = await db.update_setting("contacts", new_contacts)
    
    if success:
        await message.answer(
            "✅ Контакты успешно обновлены!",
            reply_markup=get_admin_menu_keyboard()
        )
    else:
        await message.answer(
            f"❌ Ошибка при обновлении контактов: {error}",
            reply_markup=get_admin_menu_keyboard()
        )
    
    await state.clear()

class ServiceData:
    """Класс для хранения данных об услуге в процессе создания/редактирования"""
    
    def __init__(self):
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.price: Optional[str] = None
        self.duration: Optional[int] = None
        self.is_active: bool = True


async def check_admin(message: Union[Message, CallbackQuery]) -> bool:
    """
    Проверка прав администратора
    
    Args:
        message: сообщение или callback
        
    Returns:
        bool: имеет ли пользователь права администратора
    """
    user_id = message.from_user.id
    admin_ids = message.bot.config.admin_ids
    return user_id in admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Вход в административное меню"""
    if not await check_admin(message):
        await message.answer("У вас нет прав администратора")
        return
        
    await message.answer(
        "Административная панель",
        reply_markup=get_admin_menu_keyboard()
    )


@router.message(F.text == "👥 Все записи")
async def cmd_all_appointments(
    message: Message,
    db: DatabaseManager,
    state: FSMContext
) -> None:
    """Просмотр всех записей"""
    if not await check_admin(message):
        return

    # Получаем текущую страницу из состояния или устанавливаем первую
    data = await state.get_data()
    page = data.get("appointments_page", 1)
    per_page = data.get("appointments_per_page", 10)

    # Получаем записи с пагинацией
    appointments = await db.get_appointments_paginated(page, per_page)
    total_pages = (await db.get_appointments_count() + per_page - 1) // per_page

    if not appointments:
        await message.answer("Записей не найдено")
        return

    # Формируем текст со списком записей
    text = "📅 Все записи:\n\n"
    for apt in appointments:
        text += format_appointment_info(apt, include_client=True) + "\n\n"

    # Добавляем пагинацию
    keyboard = get_pagination_keyboard(
        page, total_pages, "appointments", per_page
    )

    await message.answer(text, reply_markup=keyboard)
    await state.update_data(appointments_page=page)


@router.message(F.text == "📝 Управление услугами")
async def cmd_manage_services(
    message: Message,
    db: DatabaseManager,
    state: FSMContext
) -> None:
    """Управление услугами"""
    if not await check_admin(message):
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["➕ Добавить услугу", "📋 Список услуг"],
            ["❌ Отмена"]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Выберите действие:",
        reply_markup=keyboard
    )


@router.message(F.text == "➕ Добавить услугу")
async def cmd_add_service(message: Message, state: FSMContext) -> None:
    """Начало процесса добавления услуги"""
    if not await check_admin(message):
        return

    await state.update_data(service=ServiceData())
    
    await message.answer(
        "Введите название услуги:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.ADD_SERVICE_NAME)


@router.message(AdminStates.ADD_SERVICE_NAME)
async def process_service_name(message: Message, state: FSMContext) -> None:
    """Обработка ввода названия услуги"""
    name = message.text.strip()

    # Валидация названия
    is_valid, error = validate_service_name(name)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите название услуги:"
        )
        return

    # Сохраняем название
    data = await state.get_data()
    service: ServiceData = data["service"]
    service.name = name
    await state.update_data(service=service)

    # Запрашиваем описание
    await message.answer(
        "Введите описание услуги:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.ADD_SERVICE_DESCRIPTION)


@router.message(AdminStates.ADD_SERVICE_DESCRIPTION)
async def process_service_description(
    message: Message,
    state: FSMContext
) -> None:
    """Обработка ввода описания услуги"""
    description = message.text.strip()

    # Валидация описания
    is_valid, error = validate_service_description(description)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите описание услуги:"
        )
        return

    # Сохраняем описание
    data = await state.get_data()
    service: ServiceData = data["service"]
    service.description = description
    await state.update_data(service=service)

    # Запрашиваем цену
    await message.answer(
        "Введите стоимость услуги:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.ADD_SERVICE_PRICE)


@router.message(AdminStates.ADD_SERVICE_PRICE)
async def process_service_price(message: Message, state: FSMContext) -> None:
    """Обработка ввода стоимости услуги"""
    price = message.text.strip()

    # Валидация цены
    is_valid, error = validate_service_price(price)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите стоимость услуги:"
        )
        return

    # Сохраняем цену
    data = await state.get_data()
    service: ServiceData = data["service"]
    service.price = price
    await state.update_data(service=service)

    # Запрашиваем длительность
    await message.answer(
        "Введите длительность услуги в минутах:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.ADD_SERVICE_DURATION)


@router.message(AdminStates.ADD_SERVICE_DURATION)
async def process_service_duration(
    message: Message,
    state: FSMContext
) -> None:
    """Обработка ввода длительности услуги"""
    try:
        duration = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число (длительность в минутах):"
        )
        return

    # Валидация длительности
    is_valid, error = validate_service_duration(duration)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите длительность услуги:"
        )
        return

    # Сохраняем длительность
    data = await state.get_data()
    service: ServiceData = data["service"]
    service.duration = duration
    await state.update_data(service=service)

    # Показываем подтверждение
    await show_service_confirmation(message, service)
    await state.set_state(AdminStates.CONFIRM_SERVICE)


async def show_service_confirmation(
    message: Message,
    service: ServiceData
) -> None:
    """Показ подтверждения создания услуги"""
    text = (
        "Подтвердите данные услуги:\n\n"
        f"Название: {service.name}\n"
        f"Описание: {service.description}\n"
        f"Стоимость: {format_money(service.price)}\n"
        f"Длительность: {service.duration} мин.\n\n"
        "Всё верно?"
    )

    await message.answer(
        text,
        reply_markup=get_confirmation_keyboard()
    )


@router.callback_query(AdminStates.CONFIRM_SERVICE)
async def process_service_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """Обработка подтверждения создания услуги"""
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text(
            "Добавление услуги отменено",
            reply_markup=None
        )
        return

    # Получаем данные услуги
    data = await state.get_data()
    service: ServiceData = data["service"]

    # Добавляем услугу в БД
    success, error, _ = await db.add_service(
        name=service.name,
        description=service.description,
        price=service.price,
        duration=service.duration,
        is_active=service.is_active
    )

    if not success:
        await callback.message.edit_text(
            f"Ошибка при создании услуги: {error}\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=None
        )
        await state.clear()
        return

    # Завершаем процесс
    await callback.message.edit_text(
        "✅ Услуга успешно добавлена!",
        reply_markup=None
    )
    await state.clear()


@router.callback_query(F.data.startswith("appointment:"))
async def process_appointment_action(
    callback: CallbackQuery,
    db: DatabaseManager,
    notifications: NotificationService
) -> None:
    """Обработка действий с записью"""
    if not await check_admin(callback):
        return

    # Разбираем callback data
    _, action, appointment_id = callback.data.split(":")
    appointment_id = int(appointment_id)

    # Получаем запись
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        await callback.answer("Запись не найдена")
        return

    # Получаем клиента
    client = await db.get_client_by_id(appointment.client_id)
    if not client:
        await callback.answer("Клиент не найден")
        return

    # Обрабатываем действие
    old_status = appointment.status
    if action == "confirm":
        success, error = await db.update_appointment_status(
            appointment_id,
            AppointmentStatus.CONFIRMED
        )
    elif action == "cancel":
        success, error = await db.update_appointment_status(
            appointment_id,
            AppointmentStatus.CANCELLED
        )
    elif action == "complete":
        success, error = await db.update_appointment_status(
            appointment_id,
            AppointmentStatus.COMPLETED
        )
    else:
        await callback.answer("Неизвестное действие")
        return

    if not success:
        await callback.answer(f"Ошибка: {error}")
        return

    # Получаем обновленную запись
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        await callback.answer("Запись не найдена")
        return

    # Отправляем уведомления
    await notifications.notify_appointment_status_change(
        appointment=appointment,
        client=client,
        old_status=old_status
    )

    # Обновляем сообщение
    await callback.message.edit_text(
        format_appointment_info(appointment, include_client=True),
        reply_markup=get_appointment_actions_keyboard(
            appointment_id,
            appointment.status
        )
    )


@router.message(F.text == "📈 Статистика")
async def cmd_statistics(
    message: Message,
    analytics: AnalyticsService
) -> None:
    """Просмотр статистики"""
    if not await check_admin(message):
        return

    # Получаем статистику за последний месяц
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    stats = await analytics.get_period_stats(start_date, end_date)

    if not stats:
        await message.answer(
            "Ошибка при получении статистики"
        )
        return

    # Формируем текст ответа
    text = (
        "📊 Статистика за последние 30 дней:\n\n"
        f"Записи:\n"
        f"- Всего: {stats['total']['appointments']}\n"
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

    # Получаем популярные услуги
    popular_services = await analytics.get_popular_services(start_date, end_date, 5)
    if popular_services:
        text += "\n\nПопулярные услуги:\n"
        for i, service in enumerate(popular_services, 1):
            text += (
                f"{i}. {service['name']}\n"
                f"   Записей: {service['count']}\n"
                f"   Доход: {format_money(service['total_amount'])}\n"
            )

    # Получаем загруженность по часам
    busy_hours = await analytics.get_busy_hours(start_date, end_date)
    if busy_hours:
        text += "\n\nЗагруженность по часам:\n"
        max_bookings = max(busy_hours.values())
        for hour in range(9, 21):  # Рабочие часы
            count = busy_hours.get(hour, 0)
            bar = "█" * int(count * 10 / max_bookings) if max_bookings else ""
            text += f"{hour:02d}:00 {bar} ({count})\n"

    await message.answer(text)


@router.message(F.text == "📊 Отчёты")
async def cmd_reports(message: Message) -> None:
    """Меню отчётов"""
    if not await check_admin(message):
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["📅 Дневной отчёт", "📈 Недельный отчёт"],
            ["📊 Месячный отчёт", "💰 Финансовый отчёт"],
            ["❌ Назад"]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Выберите тип отчёта:",
        reply_markup=keyboard
    )


@router.message(F.text.startswith("🔄 Изменить статус"))
async def cmd_change_status(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """Изменение статуса записи"""
    if not await check_admin(message):
        return

    # Получаем ID записи из текста сообщения
    try:
        appointment_id = int(message.text.split("#")[1])
    except (IndexError, ValueError):
        await message.answer("Неверный формат команды")
        return

    # Получаем запись
    appointment = await db.get_appointment(appointment_id)
    if not appointment:
        await message.answer("Запись не найдена")
        return

    # Показываем текущий статус и варианты изменения
    text = (
        f"Запись #{appointment_id}\n"
        f"Текущий статус: {appointment.status.value}\n\n"
        "Выберите новый статус:"
    )
    
    keyboard = get_appointment_actions_keyboard(
        appointment_id,
        appointment.status
    )
    
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🔍 Поиск записей")
async def cmd_search_appointments(
    message: Message,
    state: FSMContext
) -> None:
    """Поиск записей"""
    if not await check_admin(message):
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["🔍 По клиенту", "📅 По дате"],
            ["📱 По телефону", "🚗 По автомобилю"],
            ["❌ Отмена"]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Выберите критерий поиска:",
        reply_markup=keyboard
    )


@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message) -> None:
    """Меню настроек"""
    if not await check_admin(message):
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["🕒 Рабочее время", "📅 Выходные дни"],
            ["💰 Финансовые настройки", "📧 Уведомления"],
            ["❌ Назад"]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Настройки системы:",
        reply_markup=keyboard
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """Рассылка сообщения всем клиентам"""
    if not await check_admin(message):
        return

    class BroadcastStates(StatesGroup):
        ENTER_MESSAGE = State()
        CONFIRM_BROADCAST = State()

    await message.answer(
        "Введите текст сообщения для рассылки:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.ENTER_MESSAGE)
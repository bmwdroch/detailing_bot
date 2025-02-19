"""
Модуль обработчиков команд клиентской части бота.
Включает обработку команд для записи на услуги и управления своими записями.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Union

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from core.models import AppointmentStatus, Client
from handlers.payment_handlers import PaymentStates, TransactionData
from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService
from utils.formatters import format_appointment_info, format_phone
from utils.keyboards import (
    get_appointment_actions_keyboard,
    get_cancel_keyboard,
    get_cancel_menu_keyboard,
    get_confirmation_keyboard,
    get_date_selection_keyboard,
    get_main_menu_keyboard,
    get_phone_keyboard,
    get_services_keyboard,
    get_time_selection_keyboard,
    get_payment_menu_keyboard,
    get_admin_menu_keyboard
)
from utils.validators import (
    validate_car_info,
    validate_category,
    validate_comment,
    validate_name,
    validate_phone,
)

# Создаем роутер для клиентских обработчиков
router = Router(name="client")

# Настраиваем логгер
logger = logging.getLogger(__name__)


class ClientStates(StatesGroup):
    """Состояния FSM для клиентских сценариев"""
    
    # Состояния регистрации
    ENTER_NAME = State()  # Ввод имени
    ENTER_PHONE = State()  # Ввод телефона
    
    # Состояния создания записи
    SELECT_SERVICE = State()  # Выбор услуги
    SELECT_DATE = State()  # Выбор даты
    SELECT_TIME = State()  # Выбор времени
    ENTER_CAR = State()  # Ввод информации об автомобиле
    ENTER_COMMENT = State()  # Ввод комментария
    CONFIRM_APPOINTMENT = State()  # Подтверждение записи


class AppointmentData:
    """Класс для хранения данных о записи в процессе её создания"""
    
    def __init__(self):
        self.service_id: Optional[int] = None
        self.service_name: Optional[str] = None
        self.date: Optional[datetime] = None
        self.time: Optional[str] = None
        self.car_info: Optional[str] = None
        self.comment: Optional[str] = None


async def get_client(message: Message, db: DatabaseManager) -> Optional[Client]:
    """
    Получение или создание клиента
    
    Args:
        message: сообщение пользователя
        db: менеджер базы данных
        
    Returns:
        Optional[Client]: объект клиента или None
    """
    return await db.get_client(message.from_user.id)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    # Получаем конфигурацию (или можно обращаться к message.bot.config)
    config = message.bot.config  # предполагается, что в Bot хранится config

    # Если пользователь админ, сразу отправляем админское меню
    if message.from_user.id in config.admin_ids:
        await message.answer(
            "Добро пожаловать, администратор!",
            reply_markup=get_admin_menu_keyboard()
        )
        return

    # Если пользователь не админ, продолжаем стандартный клиентский сценарий:
    client = await get_client(message, db)
    if client:
        await message.answer(
            f"С возвращением, {client.name}!",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "Добро пожаловать! Для начала работы нужно зарегистрироваться.\n"
            "Пожалуйста, введите ваше имя и фамилию:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ClientStates.ENTER_NAME)


@router.message(Command("cancel"))
@router.message(F.text.in_(["❌ Отменить", "🏠 Главное меню"]))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного процесса.", reply_markup=get_main_menu_keyboard())
        return

    if current_state.startswith("ClientStates"):
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_main_menu_keyboard())
    elif current_state.startswith("PaymentStates"):
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_payment_menu_keyboard())
    elif current_state.startswith("AdminStates"):
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_admin_menu_keyboard())
    else:
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=get_main_menu_keyboard())


@router.message(ClientStates.ENTER_NAME)
async def process_name(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """
    Обработка ввода имени при регистрации
    """
    # Валидация имени
    name = message.text.strip()
    is_valid, error = validate_name(name)
    
    if not is_valid:
        await message.answer(
            f"Некорректное имя: {error}\n"
            "Пожалуйста, введите имя и фамилию:"
        )
        return
    
    # Сохраняем имя
    await state.update_data(name=name)
    
    # Запрашиваем телефон
    await message.answer(
        "Теперь поделитесь номером телефона:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(ClientStates.ENTER_PHONE)


@router.message(ClientStates.ENTER_PHONE)
async def process_phone(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """
    Обработка ввода телефона при регистрации
    """
    # Получаем телефон из контакта или текста
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
    
    # Валидация телефона
    is_valid, error = validate_phone(phone)
    if not is_valid:
        await message.answer(
            f"Некорректный номер: {error}\n"
            "Пожалуйста, введите номер телефона:"
        )
        return
    
    # Получаем сохраненное имя
    data = await state.get_data()
    name = data["name"]
    
    # Создаем клиента
    success, error, client = await db.add_client(
        telegram_id=message.from_user.id,
        name=name,
        phone=phone
    )
    
    if not success:
        await message.answer(
            f"Ошибка при регистрации: {error}\n"
            "Пожалуйста, попробуйте позже."
        )
        await state.clear()
        return
    
    # Завершаем регистрацию
    await message.answer(
        "Регистрация успешно завершена!",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()


@router.message(F.text == "📝 Записаться на услугу")
async def cmd_new_appointment(
    message: Message,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """
    Начало процесса создания записи
    """
    # Проверяем регистрацию
    client = await get_client(message, db)
    if not client:
        await message.answer(
            "Для записи необходимо зарегистрироваться. Используйте /start"
        )
        return
    
    # Получаем список активных услуг
    services = await db.get_active_services()
    if not services:
        await message.answer(
            "К сожалению, сейчас нет доступных услуг.\n"
            "Пожалуйста, попробуйте позже."
        )
        return
    
    # Показываем список услуг
    await message.answer(
        "Выберите услугу:",
        reply_markup=get_services_keyboard(services)
    )
    await state.set_state(ClientStates.SELECT_SERVICE)
    
    # Инициализируем хранение данных
    await state.update_data(appointment=AppointmentData())


@router.callback_query(PaymentStates.SELECT_SERVICE)
async def process_service_selection(
    callback: CallbackQuery,
    state: FSMContext,
    db: DatabaseManager  # если необходимо получить данные услуги из БД
) -> None:
    """
    Обработка выбора услуги для транзакции.
    Если пользователь выбирает конкретную услугу, сохраняем её ID и устанавливаем категорию автоматически.
    Если выбирается "Другое", переходим к вводу категории вручную.
    """
    data = await state.get_data()
    transaction: TransactionData = data["transaction"]

    if callback.data == "service:other":
        # Пользователь выбрал ввод категории вручную
        await callback.message.edit_text(
            "Пожалуйста, введите название категории транзакции:"
        )
        await state.set_state(PaymentStates.ENTER_CATEGORY)
        return

    # Иначе, предполагаем, что callback data имеет вид "service:<ID>"
    try:
        _, service_id_str = callback.data.split(":")
        service_id = int(service_id_str)
    except Exception:
        await callback.answer("Неверный выбор. Попробуйте снова.", show_alert=True)
        return

    # Получаем информацию об услуге по service_id (например, для автоматической установки категории)
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Выбранная услуга не найдена.", show_alert=True)
        return

    transaction.service_id = service_id
    # Например, сохраняем название услуги как категорию транзакции
    transaction.category = service.name
    await state.update_data(transaction=transaction)

    await callback.message.edit_text(
        f"Вы выбрали услугу: {service.name}\n"
        "Если хотите, можете изменить категорию в ручном режиме или продолжить.",
    )
    # Переходим к вводу описания транзакции
    await callback.bot.send_message(
        callback.message.chat.id,
        "Введите описание транзакции:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PaymentStates.ENTER_DESCRIPTION)

@router.callback_query(ClientStates.SELECT_SERVICE)
async def process_service_selection_client(callback: CallbackQuery, state: FSMContext, db: DatabaseManager):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("Запись отменена", reply_markup=get_main_menu_keyboard())
        return
    try:
        # Ожидаем, что callback.data имеет формат "service:<ID>"
        _, service_id_str = callback.data.split(":")
        service_id = int(service_id_str)
    except Exception:
        await callback.answer("Неверный выбор. Попробуйте снова.", show_alert=True)
        return
    
    # Здесь можно получить данные услуги, сохранить их в состоянии и перейти к следующему шагу
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Выбранная услуга не найдена.", show_alert=True)
        return
    
    # Пример сохранения выбранной услуги в состоянии
    data = await state.get_data()
    appointment: AppointmentData = data.get("appointment")
    if appointment is None:
        appointment = AppointmentData()
    appointment.service_id = service_id
    appointment.service_name = service.name
    await state.update_data(appointment=appointment)

    # Перейти к следующему шагу – например, выбор даты:
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=get_date_selection_keyboard(datetime.now())
    )
    await state.set_state(ClientStates.SELECT_DATE)


@router.message(PaymentStates.ENTER_CATEGORY)
async def process_manual_category(message: Message, state: FSMContext) -> None:
    """
    Обработка ввода категории вручную (если выбрано "Другое")
    """
    category = message.text.strip()
    is_valid, error = validate_category(category)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите корректное название категории:"
        )
        return

    data = await state.get_data()
    transaction: TransactionData = data["transaction"]
    transaction.category = category
    await state.update_data(transaction=transaction)

    await message.answer(
        "Введите описание транзакции:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PaymentStates.ENTER_DESCRIPTION)


@router.callback_query(ClientStates.SELECT_DATE)
async def process_date_selection(
    callback: CallbackQuery,
    state: FSMContext,
    db: DatabaseManager
) -> None:
    """
    Обработка выбора даты
    """
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("Запись отменена")
        return
    
    # Получаем выбранную дату
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Получаем занятые слоты на эту дату
    booked_times = await db.get_booked_times(selected_date)
    
    # Сохраняем выбранную дату
    data = await state.get_data()
    appointment: AppointmentData = data["appointment"]
    appointment.date = selected_date
    await state.update_data(appointment=appointment)
    
    # Показываем доступное время
    await callback.message.edit_text(
        f"Дата: {selected_date.strftime('%d.%m.%Y')}\n"
        "Выберите удобное время:",
        reply_markup=get_time_selection_keyboard(selected_date, booked_times)
    )
    await state.set_state(ClientStates.SELECT_TIME)


@router.callback_query(ClientStates.SELECT_TIME)
async def process_time_selection(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Обработка выбора времени
    """
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("Запись отменена")
        return
    
    if callback.data == "back_to_date":
        await callback.message.edit_text(
            "Выберите дату:",
            reply_markup=get_date_selection_keyboard(datetime.now())
        )
        await state.set_state(ClientStates.SELECT_DATE)
        return
    
    # Получаем выбранное время
    time_str = callback.data.split(":", 1)[1]
    
    # Сохраняем выбранное время
    data = await state.get_data()
    appointment: AppointmentData = data["appointment"]
    appointment.time = time_str
    await state.update_data(appointment=appointment)
    
    # Запрашиваем информацию об автомобиле
    await callback.message.edit_text(
        "Введите информацию об автомобиле (марка и модель):"
    )
    await state.set_state(ClientStates.ENTER_CAR)


@router.message(ClientStates.ENTER_CAR)
async def process_car_info(
    message: Message,
    state: FSMContext
) -> None:
    """
    Обработка ввода информации об автомобиле
    """
    car_info = message.text.strip()
    
    # Валидация
    is_valid, error = validate_car_info(car_info)
    if not is_valid:
        await message.answer(
            f"Ошибка: {error}\n"
            "Пожалуйста, введите информацию об автомобиле:",
            reply_markup=get_cancel_menu_keyboard()
        )
        return
        
    # Сохраняем информацию об автомобиле
    data = await state.get_data()
    appointment: AppointmentData = data["appointment"]
    appointment.car_info = car_info
    await state.update_data(appointment=appointment)
    
    await show_appointment_confirmation(message, state)


async def show_appointment_confirmation(
    message: Message,
    state: FSMContext
) -> None:
    """
    Показ подтверждения записи
    """
    data = await state.get_data()
    appointment: AppointmentData = data["appointment"]
    
    # Формируем дату и время записи
    time_parts = appointment.time.split(":")
    appointment_time = appointment.date.replace(
        hour=int(time_parts[0]),
        minute=int(time_parts[1])
    )
    
    # Формируем текст подтверждения
    confirmation_text = (
        "Пожалуйста, проверьте данные записи:\n\n"
        f"Услуга: {appointment.service_name}\n"
        f"Дата: {appointment_time.strftime('%d.%m.%Y')}\n"
        f"Время: {appointment_time.strftime('%H:%M')}\n"
        f"Автомобиль: {appointment.car_info}\n"
    )
    
    if appointment.comment:
        confirmation_text += f"Комментарий: {appointment.comment}\n"
    
    confirmation_text += "\nВсё верно?"
    
    await message.answer(
        confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(ClientStates.CONFIRM_APPOINTMENT)

@router.callback_query(ClientStates.CONFIRM_APPOINTMENT)
async def process_appointment_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    db: DatabaseManager,
    notifications: NotificationService
) -> None:
    """
    Обработка подтверждения создания записи.
    Если пользователь нажал "cancel" – отменяем, иначе создаём запись.
    """
    if callback.data == "cancel":
        await state.clear()
        # Убираем inline-клавиатуру, вместо передачи ReplyKeyboardMarkup
        await callback.message.edit_text("Запись отменена", reply_markup=None)
        # Отправляем новое сообщение с основным меню (ReplyKeyboardMarkup допустима при отправке нового сообщения)
        await callback.bot.send_message(
            callback.message.chat.id,
            "Главное меню",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Получаем данные записи из состояния
    data = await state.get_data()
    appointment_data: AppointmentData = data["appointment"]

    # Исправление: получаем клиента по callback.from_user.id
    client = await db.get_client(callback.from_user.id)
    if not client:
        await callback.message.edit_text(
            "Ошибка: клиент не найден.\nПожалуйста, начните запись заново через /start",
            reply_markup=None
        )
        await state.clear()
        return

    # Формируем дату и время записи
    time_parts = appointment_data.time.split(":")
    appointment_time = appointment_data.date.replace(
        hour=int(time_parts[0]),
        minute=int(time_parts[1])
    )

    # Создаем запись в БД
    success, error, appointment = await db.add_appointment(
        client_id=client.id,
        service_type=appointment_data.service_name,
        car_info=appointment_data.car_info,
        appointment_time=appointment_time,
        comment=appointment_data.comment
    )

    if not success:
        await callback.message.edit_text(
            f"Ошибка при создании записи: {error}\nПожалуйста, попробуйте позже.",
            reply_markup=None
        )
        await state.clear()
        return

    # Отправляем уведомления (например, администратору и клиенту)
    admin_chat_id = callback.bot.config.admin_ids[0] if callback.bot.config.admin_ids else None
    await notifications.notify_new_appointment(
        appointment=appointment,
        client=client,
        admin_chat_id=admin_chat_id
    )

    # Редактируем сообщение – убираем inline‑клавиатуру
    await callback.message.edit_text(
        "✅ Запись успешно создана!\nМы свяжемся с вами для подтверждения.",
        reply_markup=None
    )
    # Отправляем новое сообщение с основным меню
    await callback.bot.send_message(
        callback.message.chat.id,
        "Главное меню",
        reply_markup=get_main_menu_keyboard()
    )

    await state.clear()


@router.message(Command("contacts"))
@router.message(F.text == "📞 Контакты")
async def cmd_contacts(message: Message, db: DatabaseManager) -> None:
    """Вывод контактной информации"""
    contacts_text = await db.get_setting("contacts")
    if not contacts_text:
        contacts_text = "К сожалению, информация о контактах временно недоступна."
        
    await message.answer(contacts_text)

@router.message(F.text == "📅 Мои записи")
async def cmd_my_appointments(
    message: Message,
    db: DatabaseManager
) -> None:
    """
    Просмотр своих записей
    """
    # Получаем клиента
    client = await get_client(message, db)
    if not client:
        await message.answer(
            "Для просмотра записей необходимо зарегистрироваться.\n"
            "Используйте /start"
        )
        return
    
    # Получаем записи клиента
    appointments = await db.get_client_appointments(client.id)
    
    if not appointments:
        await message.answer(
            "У вас пока нет записей.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Разделяем записи на активные и прошедшие
    active_appointments = []
    past_appointments = []
    now = datetime.now()
    
    for apt in appointments:
        if apt.appointment_time > now and apt.status != AppointmentStatus.CANCELLED:
            active_appointments.append(apt)
        else:
            past_appointments.append(apt)
    
    # Формируем ответ
    response = []
    
    if active_appointments:
        response.append("📅 Предстоящие записи:")
        for apt in active_appointments:
            response.append(format_appointment_info(apt))
            if apt.status == AppointmentStatus.PENDING:
                response.append("Ожидайте подтверждения записи.")
            response.append("")
    
    if past_appointments:
        response.append("📅 Прошедшие записи:")
        for apt in past_appointments[:5]:  # Показываем только 5 последних
            response.append(format_appointment_info(apt))
            response.append("")
    
    await message.answer(
        "\n".join(response),
        reply_markup=get_main_menu_keyboard()
    )
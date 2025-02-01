# utils/keyboards.py
"""
Модуль содержит функции для создания клавиатур Telegram бота.
Включает различные типы клавиатур для разных сценариев использования.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from core.models import AppointmentStatus, Service
from utils.formatters import format_date, format_money, format_time


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру для запроса номера телефона"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True
    )


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Создает основное меню бота

    Args:
        is_admin: является ли пользователь администратором
    """
    buttons = [
        [KeyboardButton(text="📝 Записаться на услугу")],
        [KeyboardButton(text="📅 Мои записи")],
        [KeyboardButton(text="📞 Контакты")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="👥 Все записи")])
        buttons.append([KeyboardButton(text="💰 Касса")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def get_cancel_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру с кнопками '❌ Отменить' и '🏠 Главное меню'."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_inline_cancel_keyboard() -> InlineKeyboardMarkup:
    """Создаёт inline‑клавиатуру с кнопкой отмены"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
        ]
    )

def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру административного меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Все записи"), KeyboardButton(text="💰 Касса")],
            [KeyboardButton(text="📝 Управление услугами")],
            [KeyboardButton(text="✏️ Изменить контакты")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )


def get_payment_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для работы с кассой (транзакции, отчёты, статистика).
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить транзакцию")],
            [KeyboardButton(text="📊 Дневной отчет"), KeyboardButton(text="📈 Недельный отчет")],
            [KeyboardButton(text="📋 Месячный отчет"), KeyboardButton(text="🔍 Статистика")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)


def get_services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора услуги

    Args:
        services: список активных услуг
    """
    # Формируем список пар (текст, callback_data)
    service_buttons = [
        (f"{s.name} - {format_money(s.price)}", f"service:{s.id}")
        for s in services if s.is_active
    ]
    # Добавляем кнопку отмены
    service_buttons.append(("❌ Отменить", "cancel"))

    # Группируем кнопки по 2 в ряд
    buttons = []
    for i in range(0, len(service_buttons), 2):
        row = [InlineKeyboardButton(text=text, callback_data=data)
               for text, data in service_buttons[i:i+2]]
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)


def get_date_selection_keyboard(start_date: datetime) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора даты

    Args:
        start_date: начальная дата для выбора
    """
    buttons = []
    temp_row = []
    for i in range(14):
        current_date = start_date + timedelta(days=i)
        btn = InlineKeyboardButton(
            text=format_date(current_date),
            callback_data=f"date:{current_date.strftime('%Y-%m-%d')}"
        )
        temp_row.append(btn)
        if (i + 1) % 3 == 0:
            buttons.append(temp_row)
            temp_row = []
    if temp_row:
        buttons.append(temp_row)
    # Добавляем кнопку отмены в отдельном ряду
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=3)


def get_time_selection_keyboard(date: datetime, booked_times: List[datetime]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора времени

    Args:
        date: выбранная дата
        booked_times: список уже забронированных времен
    """
    buttons = []
    temp_row = []
    start_hour = 9
    end_hour = 20
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            slot_time = date.replace(hour=hour, minute=minute)
            if slot_time <= datetime.now():
                continue
            if slot_time in booked_times:
                continue
            btn = InlineKeyboardButton(
                text=format_time(slot_time),
                callback_data=f"time:{slot_time.strftime('%H:%M')}"
            )
            temp_row.append(btn)
            if len(temp_row) == 4:
                buttons.append(temp_row)
                temp_row = []
    if temp_row:
        buttons.append(temp_row)
    # Добавляем нижний ряд с кнопками "Назад" и "Отменить"
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_date"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=4)


def get_appointment_actions_keyboard(appointment_id: int, status: AppointmentStatus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с записью

    Args:
        appointment_id: ID записи
        status: текущий статус записи
    """
    buttons = []
    if status == AppointmentStatus.PENDING:
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"appointment:confirm:{appointment_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"appointment:cancel:{appointment_id}")
        ])
    elif status == AppointmentStatus.CONFIRMED:
        buttons.append([
            InlineKeyboardButton(text="🏁 Выполнено", callback_data=f"appointment:complete:{appointment_id}"),
            InlineKeyboardButton(text="📅 Перенести", callback_data=f"appointment:reschedule:{appointment_id}")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"appointment:cancel:{appointment_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)


def get_transaction_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа транзакции"""
    buttons = [
        [
            InlineKeyboardButton(text="💰 Приход", callback_data="transaction:income"),
            InlineKeyboardButton(text="💸 Расход", callback_data="transaction:expense")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)


def get_pagination_keyboard(
    page: int,
    total_pages: int,
    prefix: str,
    items_per_page: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру пагинации

    Args:
        page: текущая страница
        total_pages: всего страниц
        prefix: префикс для callback_data
        items_per_page: количество элементов на странице
    """
    buttons = []

    # Первая строка с навигационными кнопками
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{page+1}"))
    buttons.append(nav_row)

    # Строка для выбора количества элементов на странице (если задано)
    if items_per_page:
        items_row = [InlineKeyboardButton(text=f"{n}️⃣", callback_data=f"{prefix}:per_page:{n}")
                     for n in [10, 20, 50]]
        buttons.append(items_row)

    # Строка с кнопкой закрытия
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_service_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline‑клавиатуру для подтверждения создания услуги.
    Callback data начинаются с "service:" для уникальности.
    """
    buttons = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data="service:confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="service:cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

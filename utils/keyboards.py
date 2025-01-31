"""
Модуль содержит функции для создания клавиатур Telegram бота.
Включает различные типы клавиатур для разных сценариев использования.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Sequence, Dict, Any

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)

from core.models import AppointmentStatus, Service
from utils.formatters import format_date, format_money, format_time


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для запроса номера телефона
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📱 Отправить номер телефона", request_contact=True))
    return keyboard


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основное меню бота
    
    Args:
        is_admin: является ли пользователь администратором
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📝 Записаться на услугу"))
    keyboard.add(KeyboardButton("📅 Мои записи"))
    
    if is_admin:
        keyboard.add(KeyboardButton("👥 Все записи"))
        keyboard.add(KeyboardButton("💰 Касса"), KeyboardButton("📊 Статистика"))
        
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отменить"))


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ Да", callback_data="confirm"),
        InlineKeyboardButton("❌ Нет", callback_data="cancel")
    )
    return keyboard


def get_services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора услуги
    
    Args:
        services: список активных услуг
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    service_buttons = [
        (f"{s.name} - {format_money(s.price)}", f"service:{s.id}")
        for s in services if s.is_active
    ]
    service_buttons.append(("❌ Отменить", "cancel"))
    keyboard.add(*[InlineKeyboardButton(text, callback_data=data) for text, data in services])
    return keyboard


def get_date_selection_keyboard(start_date: datetime) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора даты
    
    Args:
        start_date: начальная дата для выбора
    """
    keyboard = InlineKeyboardMarkup(row_width=3)
    dates = []
    
    # Добавляем даты на ближайшие 14 дней
    for i in range(14):
        current_date = start_date + timedelta(days=i)
        text = format_date(current_date)
        callback_data = f"date:{current_date.strftime('%Y-%m-%d')}"
        dates.append(InlineKeyboardButton(text, callback_data=callback_data))
    
    # Группируем по 3 кнопки в ряд
    for i in range(0, len(dates), 3):
        keyboard.row(*dates[i:i+3])
        
    keyboard.row(InlineKeyboardButton("❌ Отменить", callback_data="cancel"))
    return keyboard


def get_time_selection_keyboard(date: datetime, booked_times: List[datetime]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора времени
    
    Args:
        date: выбранная дата
        booked_times: список уже забронированных времен
    """
    keyboard = InlineKeyboardMarkup(row_width=4)
    times = []
    
    # Время работы с 9:00 до 20:00
    start_hour = 9
    end_hour = 20
    
    # Генерируем доступные временные слоты
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:  # Интервал 30 минут
            slot_time = date.replace(hour=hour, minute=minute)
            
            # Пропускаем прошедшее время
            if slot_time <= datetime.now():
                continue
                
            # Пропускаем забронированное время
            if slot_time in booked_times:
                continue
                
            text = format_time(slot_time)
            callback_data = f"time:{slot_time.strftime('%H:%M')}"
            times.append(InlineKeyboardButton(text, callback_data=callback_data))
    
    # Группируем по 4 кнопки в ряд
    for i in range(0, len(times), 4):
        keyboard.row(*times[i:i+4])
        
    keyboard.row(
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_date"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel")
    )
    return keyboard


def get_appointment_actions_keyboard(appointment_id: int, status: AppointmentStatus) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру действий с записью
    
    Args:
        appointment_id: ID записи
        status: текущий статус записи
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Добавляем кнопки в зависимости от статуса
    if status == AppointmentStatus.PENDING:
        keyboard.row(
            InlineKeyboardButton(
                "✅ Подтвердить",
                callback_data=f"appointment:confirm:{appointment_id}"
            ),
            InlineKeyboardButton(
                "❌ Отменить",
                callback_data=f"appointment:cancel:{appointment_id}"
            )
        )
    elif status == AppointmentStatus.CONFIRMED:
        keyboard.row(
            InlineKeyboardButton(
                "🏁 Выполнено",
                callback_data=f"appointment:complete:{appointment_id}"
            ),
            InlineKeyboardButton(
                "📅 Перенести",
                callback_data=f"appointment:reschedule:{appointment_id}"
            )
        )
        keyboard.row(InlineKeyboardButton(
            "❌ Отменить",
            callback_data=f"appointment:cancel:{appointment_id}"
        ))
    
    return keyboard


def get_transaction_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа транзакции"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        InlineKeyboardButton("💰 Приход", callback_data="transaction:income"),
        InlineKeyboardButton("💸 Расход", callback_data="transaction:expense")
    )
    keyboard.row(InlineKeyboardButton("❌ Отменить", callback_data="cancel"))
    return keyboard


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
    keyboard = InlineKeyboardMarkup()
    
    # Добавляем кнопки пагинации
    buttons = []
    
    if page > 1:
        buttons.append(InlineKeyboardButton(
            "◀️", callback_data=f"{prefix}:{page-1}"
        ))
    
    buttons.append(InlineKeyboardButton(
        f"{page}/{total_pages}", callback_data="ignore"
    ))
    
    if page < total_pages:
        buttons.append(InlineKeyboardButton(
            "▶️", callback_data=f"{prefix}:{page+1}"
        ))
    
    keyboard.row(*buttons)
    
    # Добавляем выбор количества элементов если передан items_per_page
    if items_per_page:
        keyboard.row(
            *[InlineKeyboardButton(
                f"{n}️⃣", callback_data=f"{prefix}:per_page:{n}"
            ) for n in [10, 20, 50]]
        )
    
    keyboard.row(InlineKeyboardButton("❌ Закрыть", callback_data="close"))
    return keyboard
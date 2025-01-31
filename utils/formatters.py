"""
Модуль содержит функции для форматирования данных при выводе пользователю.
Включает форматирование дат, времени, денежных сумм и статусов.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union, Optional

from core.models import AppointmentStatus, Transaction, Appointment, Client


def format_phone(phone: str) -> str:
    """
    Форматирует номер телефона в читаемый вид
    
    Args:
        phone: номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX
        
    Returns:
        str: отформатированный номер, например +7 (999) 123-45-67
    """
    # Убираем все не цифры
    digits = ''.join(filter(str.isdigit, phone))
    
    # Добавляем +7 если начинается с 8
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    
    return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"


def format_money(amount: Union[Decimal, float, str]) -> str:
    """
    Форматирует денежную сумму
    
    Args:
        amount: сумма как Decimal, float или строка
        
    Returns:
        str: отформатированная сумма, например 1 234,56 ₽
    """
    # Преобразуем во float для единообразия
    if isinstance(amount, str):
        amount = float(amount)
    elif isinstance(amount, Decimal):
        amount = float(amount)
    
    # Форматируем с разделением разрядов
    whole = int(amount)
    fraction = int((amount - whole) * 100)
    
    formatted = f"{whole:,}".replace(',', ' ')
    if fraction:
        formatted += f",{fraction:02d}"
        
    return f"{formatted} ₽"


def format_date(dt: datetime) -> str:
    """
    Форматирует дату
    
    Args:
        dt: объект datetime
        
    Returns:
        str: дата в формате ДД.ММ.YYYY
    """
    return dt.strftime("%d.%m.%Y")


def format_time(dt: datetime) -> str:
    """
    Форматирует время
    
    Args:
        dt: объект datetime
        
    Returns:
        str: время в формате ЧЧ:ММ
    """
    return dt.strftime("%H:%M")


def format_datetime(dt: datetime) -> str:
    """
    Форматирует дату и время
    
    Args:
        dt: объект datetime
        
    Returns:
        str: дата и время в формате ДД.ММ.YYYY ЧЧ:ММ
    """
    return f"{format_date(dt)} {format_time(dt)}"


def format_relative_date(dt: datetime) -> str:
    """
    Форматирует дату относительно текущего времени
    
    Args:
        dt: объект datetime
        
    Returns:
        str: например, "через 2 часа" или "вчера в 15:30"
    """
    now = datetime.now()
    diff = dt - now
    
    if diff > timedelta():  # Будущее время
        if diff < timedelta(hours=1):
            minutes = diff.seconds // 60
            return f"через {minutes} минут"
        elif diff < timedelta(days=1):
            hours = diff.seconds // 3600
            return f"через {hours} часов"
        elif diff < timedelta(days=2):
            return f"завтра в {format_time(dt)}"
        elif diff < timedelta(days=7):
            return f"{dt.strftime('%A')} в {format_time(dt)}"
        else:
            return format_datetime(dt)
    else:  # Прошедшее время
        diff = abs(diff)
        if diff < timedelta(hours=1):
            minutes = diff.seconds // 60
            return f"{minutes} минут назад"
        elif diff < timedelta(days=1):
            hours = diff.seconds // 3600
            return f"{hours} часов назад"
        elif diff < timedelta(days=2):
            return f"вчера в {format_time(dt)}"
        elif diff < timedelta(days=7):
            return f"в {dt.strftime('%A')} в {format_time(dt)}"
        else:
            return format_datetime(dt)


def format_appointment_status(status: AppointmentStatus) -> str:
    """
    Форматирует статус записи
    
    Args:
        status: значение из AppointmentStatus
        
    Returns:
        str: человекочитаемый статус на русском
    """
    status_map = {
        AppointmentStatus.PENDING: "🕒 Ожидает подтверждения",
        AppointmentStatus.CONFIRMED: "✅ Подтверждена",
        AppointmentStatus.COMPLETED: "🏁 Выполнена",
        AppointmentStatus.CANCELLED: "❌ Отменена",
        AppointmentStatus.RESCHEDULED: "📅 Перенесена"
    }
    return status_map.get(status, str(status))


def format_client_info(client: Client) -> str:
    """
    Форматирует информацию о клиенте
    
    Args:
        client: объект Client
        
    Returns:
        str: отформатированная информация о клиенте
    """
    return (
        f"👤 {client.name}\n"
        f"📱 {format_phone(client.phone)}\n"
        f"Клиент с {format_date(client.created_at)}"
    )


def format_appointment_info(appointment: Appointment, include_client: bool = False) -> str:
    """
    Форматирует информацию о записи
    
    Args:
        appointment: объект Appointment
        include_client: включать ли информацию о клиенте
        
    Returns:
        str: отформатированная информация о записи
    """
    result = (
        f"📅 Запись #{appointment.id}\n"
        f"🕒 {format_datetime(appointment.appointment_time)}\n"
        f"🚗 {appointment.car_info}\n"
        f"🛠 {appointment.service_type}\n"
        f"📊 {format_appointment_status(appointment.status)}"
    )
    
    if appointment.comment:
        result += f"\n💭 {appointment.comment}"
        
    if include_client:
        result = f"Клиент #{appointment.client_id}\n" + result
        
    return result


def format_transaction_info(transaction: Transaction, include_appointment: bool = False) -> str:
    """
    Форматирует информацию о транзакции
    
    Args:
        transaction: объект Transaction
        include_appointment: включать ли информацию о записи
        
    Returns:
        str: отформатированная информация о транзакции
    """
    # Выбираем эмодзи в зависимости от типа
    emoji = "💰" if transaction.type.value == "income" else "💸"
    
    result = (
        f"{emoji} {format_money(transaction.amount)}\n"
        f"📁 {transaction.category}\n"
        f"📝 {transaction.description}\n"
        f"🕒 {format_datetime(transaction.created_at)}"
    )
    
    if include_appointment and transaction.appointment_id:
        result = f"Запись #{transaction.appointment_id}\n" + result
        
    return result


def format_time_slot(dt: datetime) -> str:
    """
    Форматирует временной слот для выбора времени записи
    
    Args:
        dt: объект datetime
        
    Returns:
        str: отформатированное время для кнопки
    """
    return format_time(dt)


def format_duration(minutes: int) -> str:
    """
    Форматирует длительность в минутах
    
    Args:
        minutes: количество минут
        
    Returns:
        str: отформатированная длительность, например "1 час 30 минут"
    """
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} час{'а' if 2 <= hours <= 4 else 'ов' if hours >= 5 else ''}")
    if remaining_minutes > 0:
        parts.append(f"{remaining_minutes} минут{'а' if 2 <= remaining_minutes <= 4 else '' if remaining_minutes == 1 else ''}")
        
    return " ".join(parts)
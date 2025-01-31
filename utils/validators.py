"""
Модуль содержит функции для валидации данных перед сохранением в БД.
Каждый валидатор возвращает кортеж (bool, str), где:
- bool: True если данные валидны, False если есть ошибки
- str: None если данные валидны, текст ошибки если есть проблемы
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple

from core.models import AppointmentStatus, TransactionType
from services.db.database_manager import DatabaseManager


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация номера телефона.
    Принимает номера в формате:
    - +7XXXXXXXXXX
    - 8XXXXXXXXXX
    - +7 XXX XXX XX XX
    - 8 XXX XXX XX XX
    """
    # Убираем все пробелы и дефисы
    phone = re.sub(r'[\s\-]', '', phone)
    
    # Проверяем базовый формат
    if not re.match(r'^(?:\+7|8)\d{10}$', phone):
        return False, "Неверный формат номера. Используйте +7XXXXXXXXXX или 8XXXXXXXXXX"
    
    return True, None


def validate_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация ФИО клиента.
    - Минимум 2 слова
    - Каждое слово от 2 символов
    - Только буквы, дефис и пробелы
    """
    # Убираем лишние пробелы
    name = ' '.join(name.split())
    
    # Проверяем на минимум 2 слова
    parts = name.split()
    if len(parts) < 2:
        return False, "Введите фамилию и имя"
    
    # Проверяем каждое слово
    for part in parts:
        if len(part) < 2:
            return False, f"Слишком короткое слово: {part}"
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\-]+$', part):
            return False, f"Недопустимые символы в слове: {part}"
    
    return True, None


def validate_car_info(car_info: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация информации об автомобиле.
    - Минимум марка и модель
    - От 4 символов
    - Буквы, цифры, пробелы, дефисы
    """
    # Убираем лишние пробелы
    car_info = ' '.join(car_info.split())
    
    if len(car_info) < 4:
        return False, "Слишком короткое описание автомобиля"
    
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9\s\-\.]+$', car_info):
        return False, "Недопустимые символы в описании автомобиля"
    
    return True, None


def validate_appointment_time(time: datetime) -> Tuple[bool, Optional[str]]:
    """
    Валидация времени записи.
    - Только будущее время
    - Минимум через 1 час
    - Максимум через 3 месяца
    - Только в рабочие часы (9:00 - 20:00)
    """
    now = datetime.now()
    
    # Проверяем что время в будущем
    if time <= now:
        return False, "Время записи должно быть в будущем"
    
    # Проверяем минимальное время
    if time < now + timedelta(hours=1):
        return False, "Запись возможна минимум за 1 час"
    
    # Проверяем максимальное время
    if time > now + timedelta(days=90):
        return False, "Запись возможна максимум за 3 месяца"
    
    # Проверяем рабочие часы
    if time.hour < 9 or time.hour >= 20:
        return False, "Запись возможна только с 9:00 до 20:00"
    
    return True, None


def validate_amount(amount: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация денежной суммы.
    - Положительное число
    - Максимум 2 знака после запятой
    """
    try:
        # Пробуем преобразовать в Decimal
        amount_decimal = Decimal(amount)
        
        # Проверяем знак
        if amount_decimal <= 0:
            return False, "Сумма должна быть больше нуля"
        
        # Проверяем количество знаков после запятой
        decimal_places = abs(amount_decimal.as_tuple().exponent)
        if decimal_places > 2:
            return False, "Максимум 2 знака после запятой"
        
        return True, None
    except:
        return False, "Неверный формат суммы"


def validate_comment(comment: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Валидация комментария.
    - Опциональный
    - Максимум 500 символов
    - Без спец. символов
    """
    if comment is None:
        return True, None
        
    # Убираем пробелы по краям
    comment = comment.strip()
    
    if len(comment) > 500:
        return False, "Комментарий слишком длинный (максимум 500 символов)"
    
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9\s\.,!?\-]+$', comment):
        return False, "Недопустимые символы в комментарии"
    
    return True, None


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    """Валидация статуса записи"""
    try:
        AppointmentStatus(status)
        return True, None
    except ValueError:
        return False, f"Неверный статус. Допустимые значения: {', '.join(s.value for s in AppointmentStatus)}"


def validate_transaction_type(type_: str) -> Tuple[bool, Optional[str]]:
    """Валидация типа транзакции"""
    try:
        TransactionType(type_)
        return True, None
    except ValueError:
        return False, f"Неверный тип транзакции. Допустимые значения: {', '.join(t.value for t in TransactionType)}"


def validate_category(category: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация категории транзакции.
    - От 2 до 50 символов
    - Буквы, цифры, пробелы, дефисы
    """
    if len(category) < 2:
        return False, "Категория слишком короткая"
        
    if len(category) > 50:
        return False, "Категория слишком длинная"
    
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9\s\-]+$', category):
        return False, "Недопустимые символы в названии категории"
    
    return True, None

def validate_service_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация названия услуги
    
    Args:
        name: название услуги
        
    Returns:
        (успех, текст ошибки)
    """
    name = name.strip()
    
    if len(name) < 3:
        return False, "Название услуги должно содержать минимум 3 символа"
    
    if len(name) > 100:
        return False, "Название услуги не должно превышать 100 символов"
        
    return True, None

def validate_service_description(description: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация описания услуги
    
    Args:
        description: описание услуги
        
    Returns:
        (успех, текст ошибки)
    """
    description = description.strip()
    
    if len(description) < 10:
        return False, "Описание услуги должно содержать минимум 10 символов"
    
    if len(description) > 1000:
        return False, "Описание услуги не должно превышать 1000 символов"
        
    return True, None

def validate_service_price(price: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация цены услуги
    
    Args:
        price: цена услуги
        
    Returns:
        (успех, текст ошибки)
    """
    try:
        price_decimal = Decimal(str(price))
        
        if price_decimal <= 0:
            return False, "Цена должна быть больше нуля"
            
        if price_decimal > 1000000:
            return False, "Цена не может быть больше 1 000 000"
            
        return True, None
    except:
        return False, "Неверный формат цены"

def validate_service_duration(duration: int) -> Tuple[bool, Optional[str]]:
    """
    Валидация длительности услуги
    
    Args:
        duration: длительность в минутах
        
    Returns:
        (успех, текст ошибки)
    """
    try:
        duration_int = int(duration)
        
        if duration_int < 15:
            return False, "Минимальная длительность услуги 15 минут"
            
        if duration_int > 480:
            return False, "Максимальная длительность услуги 8 часов"
            
        return True, None
    except:
        return False, "Неверный формат длительности"
    
async def validate_appointment_time_conflicts(
    db: DatabaseManager,
    appointment_time: datetime,
    duration: int,
    exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Проверка времени записи на пересечение с другими записями
    
    Args:
        db: менеджер базы данных
        appointment_time: время записи
        duration: длительность в минутах
        exclude_id: ID записи для исключения из проверки
        
    Returns:
        (успех, текст ошибки)
    """
    # Получаем все записи на эту дату
    date_appointments = await db.get_appointments_by_date(
        appointment_time.date()
    )
    
    # Время окончания новой записи
    end_time = appointment_time + timedelta(minutes=duration)
    
    # Проверяем пересечения
    for apt in date_appointments:
        # Пропускаем запись, если указан exclude_id
        if exclude_id and apt.id == exclude_id:
            continue
            
        # Пропускаем отмененные записи
        if apt.status == AppointmentStatus.CANCELLED:
            continue
            
        apt_end_time = apt.appointment_time + timedelta(
            minutes=apt.service_duration
        )
        
        # Проверяем пересечение временных интервалов
        if (appointment_time < apt_end_time and 
            end_time > apt.appointment_time):
            return False, "Выбранное время пересекается с другой записью"
    
    return True, None
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import AppointmentStatus, Transaction, Appointment, Client
from utils.formatters import (
    format_phone,
    format_money,
    format_date,
    format_time,
    format_datetime,
    format_relative_date,
    format_appointment_status,
    format_duration,
    format_client_info,
    format_appointment_info,
    format_transaction_info
)

# Тесты для форматирования телефона
def test_format_phone():
    test_cases = [
        ("+79991234567", "+7 (999) 123-45-67"),
        ("89991234567", "+7 (999) 123-45-67"),
        ("+7 999 123 45 67", "+7 (999) 123-45-67"),
        ("8(999)1234567", "+7 (999) 123-45-67"),
    ]
    for input_phone, expected in test_cases:
        assert format_phone(input_phone) == expected

# Тесты для форматирования денежных сумм
def test_format_money():
    test_cases = [
        (Decimal("1000"), "1 000 ₽"),
        (Decimal("1000.50"), "1 000,50 ₽"),
        (Decimal("999999.99"), "999 999,99 ₽"),
        (float(1000), "1 000 ₽"),
        ("1000.00", "1 000 ₽"),
    ]
    for input_amount, expected in test_cases:
        assert format_money(input_amount) == expected

# Тесты для форматирования даты и времени
def test_format_date():
    dt = datetime(2025, 1, 15)
    assert format_date(dt) == "15.01.2025"

def test_format_time():
    dt = datetime(2025, 1, 15, 14, 30)
    assert format_time(dt) == "14:30"

def test_format_datetime():
    dt = datetime(2025, 1, 15, 14, 30)
    assert format_datetime(dt) == "15.01.2025 14:30"

# Тесты для относительных дат
def test_format_relative_date():
    fixed_now = datetime(2025, 1, 31, 12, 0, 0)
    test_cases = [
        (fixed_now + timedelta(minutes=30), "через 30 минут"),
        (fixed_now + timedelta(hours=2), "через 2 часов"),
        ((fixed_now.replace(hour=14, minute=30) + timedelta(days=1)), "завтра в 14:30"),
        (fixed_now - timedelta(hours=1), "1 часов назад"),
        ((fixed_now.replace(hour=14, minute=30) - timedelta(days=1)), "вчера в 14:30"),
    ]
    for dt, expected in test_cases:
        result = format_relative_date(dt, now=fixed_now)
        assert result.startswith(expected.split(' в')[0])

# Тесты для форматирования статусов
def test_format_appointment_status():
    test_cases = [
        (AppointmentStatus.PENDING, "🕒 Ожидает подтверждения"),
        (AppointmentStatus.CONFIRMED, "✅ Подтверждена"),
        (AppointmentStatus.COMPLETED, "🏁 Выполнена"),
        (AppointmentStatus.CANCELLED, "❌ Отменена"),
        (AppointmentStatus.RESCHEDULED, "📅 Перенесена"),
    ]
    for status, expected in test_cases:
        assert format_appointment_status(status) == expected

# Тесты для форматирования длительности
def test_format_duration():
    test_cases = [
        (30, "30 минут"),
        (60, "1 час"),
        (90, "1 час 30 минут"),
        (120, "2 часа"),
        (150, "2 часа 30 минут"),
    ]
    for minutes, expected in test_cases:
        assert format_duration(minutes) == expected

# Тесты для форматирования информации о клиенте
@pytest.fixture
def sample_client():
    return Client(
        id=1,
        telegram_id=123456789,
        name="Иван Иванов",
        phone="+79991234567",
        created_at=datetime(2025, 1, 15)
    )

def test_format_client_info(sample_client):
    expected = (
        "👤 Иван Иванов\n"
        "📱 +7 (999) 123-45-67\n"
        "Клиент с 15.01.2025"
    )
    assert format_client_info(sample_client) == expected

# Тесты для форматирования информации о записи
@pytest.fixture
def sample_appointment():
    return Appointment(
        id=1,
        client_id=1,
        service_id=1,
        car_info="Toyota Camry",
        appointment_time=datetime(2025, 1, 15, 14, 30),
        status=AppointmentStatus.CONFIRMED,
        comment="Тестовый комментарий",
        created_at=datetime(2025, 1, 14)
    )

def test_format_appointment_info(sample_appointment):
    formatted = format_appointment_info(sample_appointment)
    assert "📅 Запись #1" in formatted
    assert "🕒 15.01.2025 14:30" in formatted
    assert "🚗 Toyota Camry" in formatted
    assert "✅ Подтверждена" in formatted
    assert "💭 Тестовый комментарий" in formatted

# Тесты для форматирования информации о транзакции
@pytest.fixture
def sample_transaction():
    return Transaction(
        id=1,
        appointment_id=1,
        amount=Decimal("1000.50"),
        type="income",
        category="Услуги",
        description="Оплата услуг",
        created_at=datetime(2025, 1, 15, 14, 30)
    )

def test_format_transaction_info(sample_transaction):
    formatted = format_transaction_info(sample_transaction)
    assert "💰 1 000,50 ₽" in formatted
    assert "📁 Услуги" in formatted
    assert "📝 Оплата услуг" in formatted
    assert "🕒 15.01.2025 14:30" in formatted
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from utils.validators import (
    validate_phone,
    validate_name,
    validate_car_info,
    validate_appointment_time,
    validate_amount,
    validate_comment,
    validate_status,
    validate_transaction_type,
    validate_category,
    validate_service_name,
    validate_service_description,
    validate_service_price,
    validate_service_duration
)

# Тесты для validate_phone
def test_valid_phone_numbers():
    valid_phones = [
        "+79991234567",
        "89991234567",
        "+7 999 123 45 67",
        "8 999 123 45 67",
        "+7 (999) 123-45-67"
    ]
    for phone in valid_phones:
        is_valid, error = validate_phone(phone)
        assert is_valid
        assert error is None

def test_invalid_phone_numbers():
    invalid_phones = [
        "+7999123456",  # короткий номер
        "123456789012",  # неверный формат
        "abc1234567",   # буквы
        "+7+9991234567" # лишние символы
    ]
    for phone in invalid_phones:
        is_valid, error = validate_phone(phone)
        assert not is_valid
        assert error is not None

# Тесты для validate_name
def test_valid_names():
    valid_names = [
        "Иван Иванов",
        "Петр Петров-Водкин",
        "Anna Smith",
        "John Doe-Smith"
    ]
    for name in valid_names:
        is_valid, error = validate_name(name)
        assert is_valid
        assert error is None

def test_invalid_names():
    invalid_names = [
        "И",                # слишком короткое
        "Иван",            # только имя
        "Иван123 Петров",  # цифры
        "Ivan! Doe"        # спецсимволы
    ]
    for name in invalid_names:
        is_valid, error = validate_name(name)
        assert not is_valid
        assert error is not None

# Тесты для validate_car_info
def test_valid_car_info():
    valid_cars = [
        "Toyota Camry",
        "BMW X5 2020",
        "Лада Веста",
        "Mercedes-Benz E200"
    ]
    for car in valid_cars:
        is_valid, error = validate_car_info(car)
        assert is_valid
        assert error is None

def test_invalid_car_info():
    invalid_cars = [
        "БМВ",     # слишком короткое
        "Car!!!",  # спецсимволы
        "A" * 101  # слишком длинное
    ]
    for car in invalid_cars:
        is_valid, error = validate_car_info(car)
        assert not is_valid
        assert error is not None

# Тесты для validate_appointment_time
def test_valid_appointment_times():
    now = datetime.now()
    valid_times = [
        now + timedelta(hours=2),
        now + timedelta(days=1),
        now + timedelta(days=7),
        now.replace(hour=10, minute=0) + timedelta(days=1)
    ]
    for time in valid_times:
        is_valid, error = validate_appointment_time(time)
        assert is_valid
        assert error is None

def test_invalid_appointment_times():
    now = datetime.now()
    invalid_times = [
        now - timedelta(hours=1),  # прошедшее время
        now + timedelta(minutes=30),  # слишком скоро
        now + timedelta(days=100),  # слишком далеко
        now.replace(hour=8, minute=0)  # нерабочее время
    ]
    for time in invalid_times:
        is_valid, error = validate_appointment_time(time)
        assert not is_valid
        assert error is not None

# Тесты для validate_amount
def test_valid_amounts():
    valid_amounts = [
        "100",
        "1000.50",
        "99999.99",
        "0.01"
    ]
    for amount in valid_amounts:
        is_valid, error = validate_amount(amount)
        assert is_valid
        assert error is None

def test_invalid_amounts():
    invalid_amounts = [
        "0",
        "-100",
        "abc",
        "100.999",
        "1000000000"
    ]
    for amount in invalid_amounts:
        is_valid, error = validate_amount(amount)
        assert not is_valid
        assert error is not None

# Тесты для остальных валидаторов
def test_validate_status():
    assert validate_status("pending")[0]
    assert validate_status("confirmed")[0]
    assert validate_status("completed")[0]
    assert validate_status("cancelled")[0]
    assert not validate_status("invalid_status")[0]

def test_validate_transaction_type():
    assert validate_transaction_type("income")[0]
    assert validate_transaction_type("expense")[0]
    assert not validate_transaction_type("invalid_type")[0]

def test_validate_category():
    assert validate_category("Мойка")[0]
    assert validate_category("Ремонт двигателя")[0]
    assert not validate_category("A")[0]  # слишком короткое
    assert not validate_category("A" * 51)[0]  # слишком длинное

def test_validate_service_name():
    assert validate_service_name("Замена масла")[0]
    assert not validate_service_name("")[0]
    assert not validate_service_name("A" * 101)[0]

def test_validate_service_description():
    assert validate_service_description("Полная замена масла в двигателе")[0]
    assert not validate_service_description("Краткое")[0]
    assert not validate_service_description("A" * 1001)[0]

def test_validate_service_price():
    assert validate_service_price("1000")[0]
    assert validate_service_price("999999.99")[0]
    assert not validate_service_price("-100")[0]
    assert not validate_service_price("1000000.001")[0]

def test_validate_service_duration():
    assert validate_service_duration(30)[0]
    assert validate_service_duration(120)[0]
    assert not validate_service_duration(10)[0]
    assert not validate_service_duration(500)[0]
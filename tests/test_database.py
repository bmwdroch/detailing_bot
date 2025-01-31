import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import AppointmentStatus, TransactionType

async def test_add_client(test_db):
    """Тест создания клиента"""
    success, error, client = await test_db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    
    assert success
    assert error is None
    assert client is not None
    assert client.telegram_id == 123456789
    assert client.name == "Test Client"
    assert client.phone == "+79991234567"

async def test_add_duplicate_client(test_db, test_client):
    """Тест обработки дублирования клиентов"""
    success, error, _ = await test_db.add_client(
        telegram_id=test_client.telegram_id,
        name="Another Client",
        phone="+79999999999"
    )
    
    assert not success
    assert "уже существует" in error.lower()

async def test_add_appointment(test_db, test_client, test_service):
    """Тест создания записи"""
    appointment_time = datetime.now() + timedelta(days=1)
    success, error, appointment = await test_db.add_appointment(
        client_id=test_client.id,
        service_id=test_service.id,
        car_info="Test Car",
        appointment_time=appointment_time,
        comment="Test comment"
    )
    
    assert success
    assert error is None
    assert appointment is not None
    assert appointment.client_id == test_client.id
    assert appointment.service_id == test_service.id
    assert appointment.status == AppointmentStatus.PENDING

async def test_update_appointment_status(test_db, test_appointment):
    """Тест обновления статуса записи"""
    success, error = await test_db.update_appointment_status(
        test_appointment.id,
        AppointmentStatus.CONFIRMED
    )
    
    assert success
    assert error is None
    
    # Проверяем что статус обновился
    updated = await test_db.get_appointment(test_appointment.id)
    assert updated.status == AppointmentStatus.CONFIRMED

async def test_add_transaction(test_db, test_appointment):
    """Тест создания транзакции"""
    success, error, transaction = await test_db.add_transaction(
        amount="1000.00",
        type_=TransactionType.INCOME.value,
        category="Test",
        description="Test transaction",
        appointment_id=test_appointment.id
    )
    
    assert success
    assert error is None
    assert transaction is not None
    assert transaction.amount == Decimal("1000.00")
    assert transaction.type == TransactionType.INCOME
    
async def test_get_upcoming_appointments(test_db, test_appointment):
    """Тест получения предстоящих записей"""
    appointments = await test_db.get_upcoming_appointments()
    
    assert len(appointments) > 0
    assert test_appointment.id in [a.id for a in appointments]

async def test_get_client_appointments(test_db, test_client, test_appointment):
    """Тест получения записей клиента"""
    appointments = await test_db.get_client_appointments(test_client.id)
    
    assert len(appointments) > 0
    assert test_appointment.id in [a.id for a in appointments]
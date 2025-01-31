import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import AppointmentStatus, Client, Appointment, Transaction
from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService

# Фикстура для создания тестовой БД
@pytest.fixture
async def db():
    db = DatabaseManager(":memory:")  # Используем SQLite в памяти для тестов
    await db.init_db()
    return db

# Фикстура для создания тестового клиента
@pytest.fixture
async def test_client(db):
    success, _, client = await db.add_client(
        telegram_id=123456789,
        name="Тест Тестов",
        phone="+79991234567"
    )
    assert success
    return client

@pytest.mark.asyncio
async def test_create_appointment(db, test_client):
    service_success, _, service = await db.add_service(
        name="Тестовая услуга",
        description="Описание тестовой услуги",  # изменено с "Описание" на более длинное
        price="1000",
        duration=60,
        is_active=True
    )
    assert service_success
    appointment_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    success, error, appointment = await db.add_appointment(
        client_id=test_client.id,
        service_type=service.name,  # передаём service.name
        car_info="Toyota Camry",
        appointment_time=appointment_time,
        comment="Тестовый комментарий"
    )
    assert success
    assert error is None
    assert appointment is not None
    assert appointment.status == AppointmentStatus.PENDING
    assert appointment.client_id == test_client.id
    assert appointment.service_id == service.id


@pytest.mark.asyncio
async def test_appointment_status_flow(db, test_client):
    # Добавляем услугу для корректного создания записи
    service_success, _, service = await db.add_service(
        name="Тест",
        description="Описание тестовой услуги", 
        price="1000",
        duration=60,
        is_active=True
    )
    assert service_success
    appointment_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    success, _, appointment = await db.add_appointment(
        client_id=test_client.id,
        service_type=service.name,  # используем service.name, т.е. "Тест"
        car_info="Toyota Camry",
        appointment_time=appointment_time
    )
    assert success
    statuses = [ "confirmed", "completed", "cancelled" ]
    for status in statuses:
        success, error = await db.update_appointment_status(appointment.id, status)
        assert success
        assert error is None
        updated_appointment = await db.get_appointment(appointment.id)
        assert updated_appointment.status.value == status


@pytest.mark.asyncio
async def test_create_transaction(db):
    success, error, transaction = await db.add_transaction(
        amount="1000.50",
        type_="income",
        category="Услуги",
        description="Тестовая транзакция"
    )
    assert success
    assert error is None
    assert transaction is not None
    from decimal import Decimal
    assert transaction.amount == Decimal("1000.50")
    assert transaction.type.value == "income"

@pytest.mark.asyncio
async def test_appointment_time_validation(db, test_client):
    appointment_time = datetime.now() + timedelta(days=1)
    
    # Добавляем услугу с именем "Тест" для успешного поиска
    service_success, service_error, service = await db.add_service(
        name="Тест",
        description="Описание тестовой услуги",
        price="1000",
        duration=60,
        is_active=True
    )
    assert service_success, f"Ошибка добавления услуги: {service_error}"

    # Создаем первую запись
    success1, _, _ = await db.add_appointment(
        client_id=test_client.id,
        service_type="Тест",
        car_info="Toyota Camry",
        appointment_time=appointment_time
    )
    assert success1

    # Пробуем создать вторую запись на то же время
    success2, error2, _ = await db.add_appointment(
        client_id=test_client.id,
        service_type="Тест",
        car_info="BMW X5",
        appointment_time=appointment_time
    )
    assert not success2
    assert "пересекается" in error2.lower()
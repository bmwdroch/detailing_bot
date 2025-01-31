import asyncio
import pytest
from datetime import datetime, timedelta
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List

from services.db.database_manager import DatabaseManager
from core.models import Client, Appointment, AppointmentStatus

# Фикстуры для нагрузочного тестирования
@pytest.fixture
async def test_db():
    db = DatabaseManager(":memory:")
    await db.init_db()
    return db

@pytest.fixture
def sample_client_data():
    return [
        (i, f"Test Client {i}", f"+7999{str(i).zfill(7)}")
        for i in range(1000)
    ]

@pytest.fixture
def sample_appointment_data():
    base_date = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    return [
        {
            "service_type": f"Service {i % 5}",
            "car_info": f"Car {i}",
            "appointment_time": base_date + timedelta(hours=i % 8),
            "comment": f"Comment {i}"
        }
        for i in range(1000)
    ]
    
@pytest.mark.asyncio
async def test_concurrent_client_creation(test_db, sample_client_data):
    """Тест параллельного создания клиентов"""
    
    async def create_client(data):
        telegram_id, name, phone = data
        return await test_db.add_client(telegram_id, name, phone)

    # Создаем клиентов параллельно
    tasks = [create_client(data) for data in sample_client_data]
    results = await asyncio.gather(*tasks)

    # Проверяем результаты
    success_count = sum(1 for success, _, _ in results if success)
    assert success_count > 0
    
    # Проверяем, что все клиенты сохранены
    all_clients = await test_db.get_all_clients()
    assert len(all_clients) == success_count
    
@pytest.mark.asyncio
async def test_concurrent_appointments(test_db, sample_client_data, sample_appointment_data):
    """Тест параллельного создания записей"""
    
    # Сначала создаем клиента
    success, _, client = await test_db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success

    # Добавляем услуги для всех возможных service_type ("Service 0" ... "Service 4")
    for i in range(5):
        s_success, s_error, _ = await test_db.add_service(
            name=f"Service {i}",
            description="Test service",
            price="1000",
            duration=60,
            is_active=True
        )
        assert s_success, f"Ошибка добавления услуги Service {i}: {s_error}"

    async def create_appointment(data):
        return await test_db.add_appointment(
            client_id=client.id,
            **data
        )

    # Создаем записи параллельно
    tasks = [create_appointment(data) for data in sample_appointment_data]
    results = await asyncio.gather(*tasks)

    # Проверяем результаты
    success_count = sum(1 for success, _, _ in results if success)
    assert success_count > 0
    
@pytest.mark.asyncio
async def test_database_recovery(test_db):
    """Тест восстановления после сбоя БД"""
    
    # Имитируем сбой БД путем закрытия соединения
    await test_db.close()
    
    # Пробуем выполнить операции после восстановления
    success = False
    retry_count = 3
    
    while not success and retry_count > 0:
        try:
            await test_db.init_db()
            success, _, _ = await test_db.add_client(
                telegram_id=123456789,
                name="Test Client",
                phone="+79991234567"
            )
            assert success
            break
        except Exception:
            retry_count -= 1
            await asyncio.sleep(1)
    
    assert success

@pytest.mark.asyncio
async def test_high_load_queries(test_db):
    """Тест производительности при большом количестве запросов"""
    
    # Создаем тестовые данные
    clients = []
    appointments = []
    
    # Создаем 100 клиентов
    for i in range(100):
        success, _, client = await test_db.add_client(
            telegram_id=i,
            name=f"Client {i}",
            phone=f"+7999{str(i).zfill(7)}"
        )
        if success:
            clients.append(client)
    
    # Создаем 1000 записей
    base_date = datetime.now() + timedelta(days=1)
    for i in range(1000):
        client = random.choice(clients)
        success, _, appointment = await test_db.add_appointment(
            client_id=client.id,
            service_type=f"Service {i % 5}",
            car_info=f"Car {i}",
            appointment_time=base_date + timedelta(hours=i % 24),
            comment=f"Comment {i}"
        )
        if success:
            appointments.append(appointment)

    # Выполняем серию сложных запросов
    start_time = datetime.now()
    
    tasks = [
        test_db.get_client_appointments(client.id) for client in clients
    ] + [
        test_db.get_upcoming_appointments(),
        test_db.get_appointments_by_date_range(
            datetime.now(),
            datetime.now() + timedelta(days=7)
        )
    ]
    
    results = await asyncio.gather(*tasks)
    
    end_time = datetime.now()
    execution_time = (end_time - start_time).total_seconds()
    
    # Проверяем время выполнения
    assert execution_time < 5  # не более 5 секунд на все запросы
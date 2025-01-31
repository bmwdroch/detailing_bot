import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Dict, List

import aiosqlite
from aiogram import Bot
from aiogram.types import User, Message, Chat

from services.db.database_manager import DatabaseManager
from services.analytics.analytics import AnalyticsService
from services.notifications.notification_service import NotificationService
from core.models import Client, Service, Appointment, AppointmentStatus

# Фикстуры для тестовой базы данных
@pytest.fixture
async def test_db() -> AsyncGenerator[DatabaseManager, None]:
    """Создает тестовую БД в памяти"""
    db = DatabaseManager(":memory:")
    await db.init_db()
    yield db
    await db.close()

# Фикстура для мока бота
class MockBot:
    def __init__(self):
        self.sent_messages: List[Dict] = []
        
    async def send_message(self, chat_id: int, text: str, **kwargs):
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': text,
            **kwargs
        })
        
@pytest.fixture
def mock_bot() -> MockBot:
    return MockBot()

# Фикстура для тестового клиента
@pytest.fixture
async def test_client(test_db) -> Client:
    """Создает тестового клиента"""
    success, _, client = await test_db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success
    return client

# Фикстура для тестовой услуги  
@pytest.fixture
async def test_service(test_db) -> Service:
    """Создает тестовую услугу"""
    success, _, service = await test_db.add_service(
        name="Test Service",
        description="Test Description",
        price="1000.00",
        duration=60,
        is_active=True
    )
    assert success
    return service

# Фикстура для тестовой записи
@pytest.fixture
async def test_appointment(test_db, test_client, test_service) -> Appointment:
    """Создает тестовую запись"""
    # Задаём время с завтрашним днем, но устанавливаем допустимый час (например, 10:00)
    appointment_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    success, _, appointment = await test_db.add_appointment(
        client_id=test_client.id,
        service_id=test_service.id,  # теперь поддерживается
        car_info="Test Car",
        appointment_time=appointment_time,
        comment="Test comment"
    )
    assert success
    return appointment

# Фикстура для тестовых сервисов
@pytest.fixture
async def services(test_db, mock_bot) -> Dict:
    """Создает все необходимые сервисы для тестирования"""
    notifications = NotificationService(mock_bot)
    analytics = AnalyticsService(test_db)
    return {
        'db': test_db,
        'notifications': notifications,
        'analytics': analytics,
        'mock_bot': mock_bot
    }

# Фикстуры для моков объектов aiogram
@pytest.fixture
def mock_user() -> User:
    return User(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en"
    )

@pytest.fixture
def mock_chat() -> Chat:
    return Chat(
        id=123456789,
        type="private"
    )

@pytest.fixture
def mock_message(mock_user, mock_chat) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(),
        chat=mock_chat,
        from_user=mock_user,
        text="Test message"
    )
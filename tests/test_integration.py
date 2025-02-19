import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService
from services.analytics.analytics import AnalyticsService
from core.models import AppointmentStatus, TransactionType

class MockBot:
    """Мок для бота Telegram"""
    
    def __init__(self):
        self.sent_messages = []
        
    async def send_message(self, chat_id, text, **kwargs):
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': text,
            **kwargs
        })

@pytest.mark.asyncio
@pytest.fixture
async def services():
    """Фикстура для инициализации всех сервисов"""
    db = DatabaseManager(":memory:")
    await db.init_db()
    
    mock_bot = MockBot()
    notifications = NotificationService(mock_bot)
    analytics = AnalyticsService(db)
    
    return {
        'db': db,
        'notifications': notifications,
        'analytics': analytics,
        'mock_bot': mock_bot
    }

@pytest.mark.asyncio
async def test_full_appointment_flow(services):
    db = services['db']
    notifications = services['notifications']
    analytics = services['analytics']
    mock_bot = services['mock_bot']
    success, _, client = await db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success
    success, _, service = await db.add_service(
        name="Test Service",
        description="Test Description",
        price="1000",
        duration=60,
        is_active=True
    )
    assert success
    appointment_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    success, _, appointment = await db.add_appointment(
        client_id=client.id,
        service_type=service.name,
        car_info="Test Car",
        appointment_time=appointment_time
    )
    assert success
    await notifications.notify_new_appointment(
        appointment=appointment,
        client=client,
        admin_chat_id=987654321
    )
    success, _ = await db.update_appointment_status(appointment.id, AppointmentStatus.CONFIRMED.value)
    assert success
    success, _, transaction = await db.add_transaction(
        amount=str(service.price),
        type_=TransactionType.INCOME.value,
        category="Services",
        description="Payment for service",
        appointment_id=appointment.id
    )
    assert success
    success, _ = await db.update_appointment_status(appointment.id, AppointmentStatus.COMPLETED.value)
    assert success
    stats = await analytics.get_daily_stats(appointment_time.date())
    assert stats['appointments']['completed'] > 0
    from decimal import Decimal
    assert Decimal(stats['finances']['income']) > 0

@pytest.mark.asyncio
async def test_concurrent_operations(services):
    db = services['db']
    success, _, client = await db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success
    # Добавляем услугу "Test Service"
    service_success, service_error, service = await db.add_service(
        name="Test Service",
        description="Test Description",
        price="1000",
        duration=60,
        is_active=True
    )
    assert service_success, f"Ошибка добавления услуги: {service_error}"

    appointment_time = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    tasks = [
        db.add_appointment(
            client_id=client.id,
            service_type=service.name,
            car_info=f"Car {i}",
            appointment_time=appointment_time + timedelta(hours=i)
        )
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)
    success_count = sum(1 for success, _, _ in results if success)
    assert success_count == 5
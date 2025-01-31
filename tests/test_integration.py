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

async def test_full_appointment_flow(services):
    """Тест полного процесса создания и обработки записи"""
    
    db = services['db']
    notifications = services['notifications']
    analytics = services['analytics']
    mock_bot = services['mock_bot']
    
    # 1. Создаем клиента
    success, _, client = await db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success
    
    # 2. Создаем услугу
    success, _, service = await db.add_service(
        name="Test Service",
        description="Test Description",
        price="1000",
        duration=60,
        is_active=True
    )
    assert success
    
    # 3. Создаем запись
    appointment_time = datetime.now() + timedelta(days=1)
    success, _, appointment = await db.add_appointment(
        client_id=client.id,
        service_type=service.name,
        car_info="Test Car",
        appointment_time=appointment_time
    )
    assert success
    
    # 4. Отправляем уведомление о новой записи
    await notifications.notify_new_appointment(
        appointment=appointment,
        client=client,
        admin_chat_id=987654321
    )
    
    # Проверяем, что уведомления отправлены
    assert len(mock_bot.sent_messages) >= 2
    
    # 5. Подтверждаем запись
    success, _ = await db.update_appointment_status(
        appointment.id,
        AppointmentStatus.CONFIRMED
    )
    assert success
    
    # 6. Создаем транзакцию оплаты
    success, _, transaction = await db.add_transaction(
        amount=str(service.price),
        type_=TransactionType.INCOME.value,
        category="Services",
        description="Payment for service",
        appointment_id=appointment.id
    )
    assert success
    
    # 7. Завершаем запись
    success, _ = await db.update_appointment_status(
        appointment.id,
        AppointmentStatus.COMPLETED
    )
    assert success
    
    # 8. Проверяем статистику
    stats = await analytics.get_daily_stats(appointment_time.date())
    assert stats['appointments']['completed'] > 0
    assert Decimal(stats['finances']['income']) > 0

async def test_error_handling(services):
    """Тест обработки ошибок"""
    
    db = services['db']
    
    # Тест дублирования клиента
    success1, _, _ = await db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success1
    
    success2, error, _ = await db.add_client(
        telegram_id=123456789,
        name="Test Client 2",
        phone="+79991234567"
    )
    assert not success2
    assert error is not None
    
    # Тест некорректного ID записи
    success, error = await db.update_appointment_status(
        9999,
        AppointmentStatus.CONFIRMED
    )
    assert not success
    assert error is not None

async def test_concurrent_operations(services):
    """Тест параллельных операций"""
    
    db = services['db']
    
    # Создаем тестовые данные
    success, _, client = await db.add_client(
        telegram_id=123456789,
        name="Test Client",
        phone="+79991234567"
    )
    assert success
    
    # Выполняем параллельные операции
    appointment_time = datetime.now() + timedelta(days=1)
    tasks = [
        db.add_appointment(
            client_id=client.id,
            service_type="Test Service",
            car_info=f"Car {i}",
            appointment_time=appointment_time + timedelta(hours=i)
        )
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    success_count = sum(1 for success, _, _ in results if success)
    assert success_count == 5
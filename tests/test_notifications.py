import pytest
from datetime import datetime, timedelta
    
@pytest.mark.asyncio
async def test_notify_new_appointment(services, test_client, test_appointment):
    """Тест уведомления о новой записи"""
    await services['notifications'].notify_new_appointment(
        appointment=test_appointment,
        client=test_client,
        admin_chat_id=987654321
    )
    
    # Проверяем что сообщения были отправлены
    messages = services['mock_bot'].sent_messages
    assert len(messages) >= 2  # Минимум 2 сообщения (клиенту и админу)
    
    # Проверяем получателей
    recipients = {m['chat_id'] for m in messages}
    assert test_client.telegram_id in recipients
    assert 987654321 in recipients
    
@pytest.mark.asyncio
async def test_notify_status_change(services, test_client, test_appointment):
    """Тест уведомления об изменении статуса"""
    await services['notifications'].notify_appointment_status_change(
        appointment=test_appointment,
        client=test_client,
        old_status="pending",
        admin_chat_id=987654321
    )
    
    messages = services['mock_bot'].sent_messages
    assert len(messages) > 0
    
    # Проверяем содержимое сообщения
    status_message = messages[0]['text']
    assert test_appointment.status.value in status_message.lower()
    
@pytest.mark.asyncio
async def test_send_appointment_reminder(services, test_client, test_appointment):
    """Тест отправки напоминания"""
    await services['notifications'].send_appointment_reminder(
        appointment=test_appointment,
        client=test_client,
        hours_before=24
    )
    
    messages = services['mock_bot'].sent_messages
    assert len(messages) > 0
    assert messages[0]['chat_id'] == test_client.telegram_id
    assert "напоминание" in messages[0]['text'].lower()
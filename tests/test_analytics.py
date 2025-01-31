import pytest
from datetime import datetime, timedelta
from decimal import Decimal

@pytest.mark.asyncio
async def test_daily_stats(services, test_appointment):
    """Тест получения дневной статистики"""
    stats = await services['analytics'].get_daily_stats(
        test_appointment.appointment_time.date()
    )
    
    assert stats
    assert 'appointments' in stats
    assert 'finances' in stats
    assert stats['appointments']['total'] > 0

@pytest.mark.asyncio
async def test_period_stats(services, test_appointment):
    """Тест получения статистики за период"""
    start_date = test_appointment.appointment_time - timedelta(days=1)
    end_date = test_appointment.appointment_time + timedelta(days=1)
    
    stats = await services['analytics'].get_period_stats(start_date, end_date)
    
    assert stats
    assert 'total' in stats
    assert 'average' in stats
    assert stats['total']['appointments'] > 0

@pytest.mark.asyncio
async def test_popular_services(services, test_appointment):
    """Тест получения популярных услуг"""
    # Обновляем статус записи, чтобы она попала в выборку (выбираются только completed)
    await services['db'].update_appointment_status(test_appointment.id, "completed")
    
    start_date = test_appointment.appointment_time - timedelta(days=30)
    end_date = test_appointment.appointment_time + timedelta(days=30)

    pop_services = await services['analytics'].get_popular_services(
        start_date, 
        end_date,
        limit=5
    )
    
    assert isinstance(pop_services, list)
    assert len(pop_services) > 0
    assert 'service_id' in pop_services[0]
    assert 'count' in pop_services[0]

@pytest.mark.asyncio
async def test_busy_hours(services, test_appointment):
    """Тест получения загруженности по часам"""
    start_date = test_appointment.appointment_time - timedelta(days=1)
    end_date = test_appointment.appointment_time + timedelta(days=1)
    
    hours = await services['analytics'].get_busy_hours(start_date, end_date)
    
    assert isinstance(hours, dict)
    assert len(hours) > 0
    assert test_appointment.appointment_time.hour in hours
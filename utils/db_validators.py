# utils/db_validators.py
from datetime import datetime, timedelta
from typing import Optional, Tuple

from services.db.database_manager import DatabaseManager
from core.models import AppointmentStatus

async def validate_appointment_time_conflicts(
    db: DatabaseManager,
    appointment_time: datetime,
    duration: int,
    exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Проверка времени записи на пересечение с другими записями
    
    Args:
        db: менеджер базы данных
        appointment_time: время записи
        duration: длительность в минутах
        exclude_id: ID записи для исключения из проверки
        
    Returns:
        (успех, текст ошибки)
    """
    # Получаем все записи на эту дату
    date_appointments = await db.get_appointments_by_date(
        appointment_time.date()
    )
    
    # Время окончания новой записи
    end_time = appointment_time + timedelta(minutes=duration)
    
    # Проверяем пересечения
    for apt in date_appointments:
        # Пропускаем запись, если указан exclude_id
        if exclude_id and apt.id == exclude_id:
            continue
            
        # Пропускаем отмененные записи
        if apt.status == AppointmentStatus.CANCELLED:
            continue
            
        apt_end_time = apt.appointment_time + timedelta(
            minutes=apt.service_duration
        )
        
        # Проверяем пересечение временных интервалов
        if (appointment_time < apt_end_time and 
            end_time > apt.appointment_time):
            return False, "Выбранное время пересекается с другой записью"
    
    return True, None
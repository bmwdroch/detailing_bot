"""
Модуль для контроля доступа к данным
"""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AccessControlMiddleware(BaseMiddleware):
    """Мидлварь для контроля доступа к данным"""

    def __init__(self, db: DatabaseManager):
        self.db = db
        super().__init__()

    async def _check_appointment_access(
        self, 
        user_id: int, 
        appointment_id: int
    ) -> bool:
        """
        Проверка доступа к записи
        
        Args:
            user_id: ID пользователя
            appointment_id: ID записи
            
        Returns:
            bool: имеет ли пользователь доступ
        """
        try:
            # Получаем данные о клиенте
            client = await self.db.get_client(user_id)
            if not client:
                return False
                
            # Получаем запись
            appointment = await self.db.get_appointment(appointment_id)
            if not appointment:
                return False
                
            # Проверяем принадлежность записи клиенту
            return appointment.client_id == client.id
            
        except Exception as e:
            logger.error(f"Error checking appointment access: {e}")
            return False

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем админов
        if data.get("is_admin"):
            return await handler(event, data)

        # Извлекаем ID записи из callback_data или текста сообщения
        appointment_id = None
        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith("appointment:"):
                appointment_id = int(event.data.split(":")[2])
        elif isinstance(event, Message) and event.text:
            if "#" in event.text:
                try:
                    appointment_id = int(event.text.split("#")[1])
                except (IndexError, ValueError):
                    pass

        # Если есть ID записи, проверяем доступ
        if appointment_id:
            user_id = event.from_user.id
            has_access = await self._check_appointment_access(
                user_id, 
                appointment_id
            )
            
            if not has_access:
                logger.warning(
                    f"Unauthorized access attempt to appointment {appointment_id} "
                    f"by user {user_id}"
                )
                await event.answer(
                    "У вас нет доступа к этой записи",
                    show_alert=True
                )
                return

        return await handler(event, data)
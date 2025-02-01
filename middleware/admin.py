# middleware/admin.py
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class AdminMiddleware(BaseMiddleware):
    """Мидлварь для проверки прав администратора"""

    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из сообщения или колбэка
        user_id = event.from_user.id if event.from_user else None

        # Проверяем, является ли пользователь администратором
        is_admin = user_id in self.admin_ids if user_id else False

        # Добавляем флаг is_admin в data
        data["is_admin"] = is_admin

        # Если событие – сообщение и текст присутствует, выполняем дополнительную проверку
        if not is_admin and isinstance(event, Message) and event.text and "admin" in event.text.lower():
            logging.warning(
                f"Unauthorized access attempt to admin functions by user {user_id}"
            )
            await event.answer("У вас нет прав администратора")
            return

        return await handler(event, data)

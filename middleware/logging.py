"""
Middleware для автоматического логирования запросов
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from services.logging.log_service import LogService

class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих запросов"""

    def __init__(self, log_service: LogService):
        self.log_service = log_service
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящий запрос
        self.log_service.log_request(event, {
            "state": data.get("raw_state"),
            "is_admin": data.get("is_admin", False)
        })
        
        try:
            return await handler(event, data)
        except Exception as e:
            # Логируем ошибку
            self.log_service.log_error(e, {
                "event": str(event),
                "state": data.get("raw_state")
            })
            raise
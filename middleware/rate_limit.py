"""
Модуль для ограничения количества попыток ввода
"""

import logging
from typing import Any, Awaitable, Callable, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    """Мидлварь для ограничения количества попыток ввода"""

    def __init__(self, rate_limit: int = 5, reset_timeout: int = 300):
        """
        Инициализация мидлвари
        
        Args:
            rate_limit: максимальное количество попыток
            reset_timeout: время сброса в секундах
        """
        self.rate_limit = rate_limit
        self.reset_timeout = reset_timeout
        self.attempts = defaultdict(list)
        super().__init__()

    def _cleanup_old_attempts(self, user_id: int) -> None:
        """Очистка старых попыток"""
        now = datetime.now()
        self.attempts[user_id] = [
            time for time in self.attempts[user_id]
            if now - time < timedelta(seconds=self.reset_timeout)
        ]

    def _check_rate_limit(self, user_id: int) -> bool:
        """Проверка лимита попыток"""
        self._cleanup_old_attempts(user_id)
        return len(self.attempts[user_id]) < self.rate_limit

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        # Проверяем только текстовые сообщения в состояниях ввода
        if event.text and data.get("raw_state") in [
            "ClientStates:ENTER_PHONE",
            "PaymentStates:ENTER_AMOUNT",
            "AdminStates:ADD_SERVICE_PRICE"
        ]:
            if not self._check_rate_limit(user_id):
                await event.answer(
                    "Превышен лимит попыток. Пожалуйста, подождите немного."
                )
                logger.warning(
                    f"Rate limit exceeded for user {user_id} in state {data['raw_state']}"
                )
                return
            
            self.attempts[user_id].append(datetime.now())
            
        return await handler(event, data)
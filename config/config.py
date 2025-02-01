import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator

class Config(BaseSettings):
    """Настройки приложения."""
    # Настройки бота
    bot_token: str
    admin_ids: List[int]

    # Настройки БД
    database_path: str
    database_pool_size: int = 5
    database_timeout: int = 30

    # Рабочие часы
    working_hours_start: int = 9 
    working_hours_end: int = 20

    # Настройки уведомлений
    reminder_interval: int = 1800
    day_reminder: int = 24
    hour_reminder: int = 2

    # Настройки аналитики 
    low_balance_threshold: int = 1000

    # Настройки логирования
    log_level: str = "INFO"

    @validator("admin_ids", pre=True)
    def parse_admin_ids(cls, v):
        # Если значение уже целое число – оборачиваем в список
        if isinstance(v, int):
            return [v]
        # Если значение – строка, например "[402152027]" или "402152027"
        if isinstance(v, str):
            v = v.strip()
            if v.startswith('[') and v.endswith(']'):
                v = v[1:-1]
            # Разбиваем по запятой и преобразуем элементы в int
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        # Если значение уже список – возвращаем как есть
        if isinstance(v, list):
            return v
        raise ValueError("admin_ids must be a list of integers")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
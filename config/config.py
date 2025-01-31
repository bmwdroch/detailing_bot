import os
from pathlib import Path
from typing import List

from pydantic import BaseSettings

class Settings(BaseSettings):
    """Настройки приложения"""
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        
def load_config() -> Settings:
    """Загрузка конфигурации из файлов"""
            
    # Приоритет у переменных окружения
    return Settings(
        bot_token=os.getenv("BOT_TOKEN"),
        admin_ids=list(map(int, os.getenv("ADMIN_IDS", "").split(","))),
        database_path=os.getenv("DATABASE_PATH"),
    )
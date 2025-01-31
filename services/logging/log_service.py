"""
Модуль для централизованного логирования
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict, Optional

from aiogram.types import Message, CallbackQuery
from core.models import AppointmentStatus

class LogService:
    """Сервис логирования"""

    def __init__(
        self, 
        log_path: str = "logs",
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 10
    ):
        self.log_path = log_path
        os.makedirs(log_path, exist_ok=True)
        
        # Настраиваем основной логгер
        self._setup_main_logger(max_bytes, backup_count)
        
        # Создаем отдельные логгеры для разных типов событий
        self.request_logger = self._setup_logger(
            "request_log",
            os.path.join(log_path, "requests.log"),
            max_bytes,
            backup_count
        )
        self.error_logger = self._setup_logger(
            "error_log",
            os.path.join(log_path, "errors.log"),
            max_bytes,
            backup_count
        )
        self.transaction_logger = self._setup_logger(
            "transaction_log",
            os.path.join(log_path, "transactions.log"),
            max_bytes,
            backup_count
        )
        self.status_logger = self._setup_logger(
            "status_log",
            os.path.join(log_path, "status_changes.log"),
            max_bytes,
            backup_count
        )

    def _setup_main_logger(
        self,
        max_bytes: int,
        backup_count: int
    ) -> None:
        """Настройка основного логгера"""
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Файловый обработчик с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_path, "bot.log"),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(file_handler)

    def _setup_logger(
        self,
        name: str,
        filename: str,
        max_bytes: int,
        backup_count: int
    ) -> logging.Logger:
        """Создание отдельного логгера"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        handler = logging.handlers.RotatingFileHandler(
            filename,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(message)s"
            )
        )
        logger.addHandler(handler)
        
        return logger

    def log_request(
        self,
        event: Message | CallbackQuery,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирование входящего запроса"""
        user_id = event.from_user.id if event.from_user else "Unknown"
        
        if isinstance(event, Message):
            content = event.text or event.caption or "No text"
            event_type = "Message"
        else:
            content = event.data
            event_type = "Callback"
            
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "event_type": event_type,
            "content": content
        }
        
        if context:
            log_data.update(context)
            
        self.request_logger.info(str(log_data))

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирование ошибки"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        if context:
            log_data["context"] = context
            
        self.error_logger.error(str(log_data))

    def log_status_change(
        self,
        appointment_id: int,
        old_status: AppointmentStatus,
        new_status: AppointmentStatus,
        user_id: int
    ) -> None:
        """Логирование изменения статуса"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "appointment_id": appointment_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "changed_by": user_id
        }
        
        self.status_logger.info(str(log_data))

    def log_transaction(
        self,
        transaction_id: int,
        amount: float,
        type_: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирование транзакции"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id,
            "amount": amount,
            "type": type_,
            "created_by": user_id
        }
        
        if context:
            log_data.update(context)
            
        self.transaction_logger.info(str(log_data))
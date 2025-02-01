"""
Модуль для отправки различных типов уведомлений пользователям через Telegram.
Включает функции для отправки напоминаний о записях, уведомлений об изменении статуса и системных уведомлений.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from aiogram import Bot
from core.models import Appointment, AppointmentStatus, Client, Transaction
from utils.formatters import (
    format_appointment_info,
    format_datetime,
    format_money,
    format_relative_date
)


class NotificationService:
    """Сервис для отправки уведомлений"""

    def __init__(self, bot: Bot):
        """
        Инициализация сервиса
        
        Args:
            bot: объект бота для отправки сообщений
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        **kwargs
    ) -> bool:
        """
        Отправка сообщения с обработкой ошибок
        
        Args:
            chat_id: ID чата
            text: текст сообщения
            parse_mode: режим разметки
            **kwargs: дополнительные параметры
            
        Returns:
            bool: успешность отправки
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                **kwargs
            )
            return True
        except Exception as e:
            self.logger.error(f"Error sending message to {chat_id}: {e}")
            return False

    async def notify_new_appointment(
        self,
        appointment: Appointment,
        client: Client,
        admin_chat_id: int
    ) -> None:
        """
        Уведомление о новой записи
        
        Args:
            appointment: данные записи
            client: данные клиента
            admin_chat_id: ID чата администратора
        """
        # Уведомляем администратора
        admin_text = (
            "🆕 Новая запись!\n\n"
            f"От: {client.name}\n"
            f"📱 {client.phone}\n\n"
            f"{format_appointment_info(appointment)}"
        )
        await self.send_message(admin_chat_id, admin_text)

        # Уведомляем клиента
        client_text = (
            "✅ Ваша запись успешно создана!\n\n"
            f"{format_appointment_info(appointment)}\n\n"
            "Мы свяжемся с вами для подтверждения записи."
        )
        await self.send_message(client.telegram_id, client_text)

    async def notify_appointment_status_change(
        self,
        appointment: Appointment,
        client: Client,
        old_status: str,
        admin_chat_id: Optional[int] = None
    ) -> None:
        """
        Уведомление об изменении статуса записи
        
        Args:
            appointment: данные записи
            client: данные клиента
            old_status: предыдущий статус
            admin_chat_id: ID чата администратора
        """
        # Текст для клиента
        status_messages = {
            "confirmed": "✅ Ваша запись подтверждена!",
            "cancelled": "❌ Ваша запись отменена.",
            "completed": "🏁 Услуга оказана. Спасибо за обращение!",
            "rescheduled": "📅 Ваша запись перенесена."
        }

        if appointment.status.value in status_messages:
            client_text = (
                f"{status_messages[appointment.status.value]}\n\n"
                f"{format_appointment_info(appointment)}"
            )
            await self.send_message(client.telegram_id, client_text)

        # Уведомляем администратора если указан chat_id
        if admin_chat_id:
            admin_text = (
                f"📝 Изменение статуса записи #{appointment.id}\n"
                f"Клиент: {client.name}\n"
                f"Старый статус: {old_status}\n"
                f"Новый статус: {appointment.status.value}\n\n"
                f"{format_appointment_info(appointment)}"
            )
            await self.send_message(admin_chat_id, admin_text)

    async def send_appointment_reminder(
        self,
        appointment: Appointment,
        client: Client,
        hours_before: int
    ) -> None:
        """
        Отправка напоминания о записи
        
        Args:
            appointment: данные записи
            client: данные клиента
            hours_before: за сколько часов до записи
        """
        relative_time = format_relative_date(appointment.appointment_time)
        
        text = (
            f"⏰ Напоминание о записи {relative_time}!\n\n"
            f"{format_appointment_info(appointment)}\n\n"
        )
        
        # Добавляем инструкции в зависимости от времени
        if hours_before >= 24:
            text += (
                "Если вам нужно отменить или перенести запись, "
                "пожалуйста, сообщите об этом заранее."
            )
        else:
            text += (
                "Пожалуйста, не опаздывайте. "
                "Если возникли непредвиденные обстоятельства, сообщите нам."
            )
            
        await self.send_message(client.telegram_id, text)

    async def notify_low_balance(
        self,
        balance: Union[int, float],
        admin_chat_id: int,
        threshold: Union[int, float] = 1000
    ) -> None:
        """
        Уведомление о низком балансе
        
        Args:
            balance: текущий баланс
            admin_chat_id: ID чата администратора
            threshold: пороговое значение
        """
        if balance < threshold:
            text = (
                "⚠️ Внимание! Низкий баланс!\n\n"
                f"Текущий баланс: {format_money(balance)}\n"
                f"Пороговое значение: {format_money(threshold)}"
            )
            await self.send_message(admin_chat_id, text)

    async def notify_daily_summary(
        self,
        date: datetime,
        appointments: List[Appointment],
        transactions: List[Transaction],
        admin_chat_id: int
    ) -> None:
        """
        Отправка ежедневной сводки
        
        Args:
            date: дата сводки
            appointments: записи за день
            transactions: транзакции за день
            admin_chat_id: ID чата администратора
        """
        # Считаем статистику по записям
        total_appointments = len(appointments)
        completed = sum(1 for a in appointments if a.status == "completed")
        cancelled = sum(1 for a in appointments if a.status == "cancelled")
        
        # Считаем статистику по транзакциям
        income = sum(t.amount for t in transactions if t.type.value == "income")
        expense = sum(t.amount for t in transactions if t.type.value == "expense")
        profit = income - expense
        
        text = (
            f"📊 Сводка за {format_datetime(date)}\n\n"
            f"Записи:\n"
            f"- Всего: {total_appointments}\n"
            f"- Выполнено: {completed}\n"
            f"- Отменено: {cancelled}\n\n"
            f"Финансы:\n"
            f"- Доход: {format_money(income)}\n"
            f"- Расход: {format_money(expense)}\n"
            f"- Прибыль: {format_money(profit)}"
        )
        
        await self.send_message(admin_chat_id, text)

    async def notify_system_error(
        self,
        error: Exception,
        admin_chat_id: int,
        context: Optional[dict] = None
    ) -> None:
        """
        Уведомление об ошибке в системе
        
        Args:
            error: объект ошибки
            admin_chat_id: ID чата администратора
            context: дополнительный контекст (опционально)
        """
        text = (
            "🚨 Системная ошибка!\n\n"
            f"Тип: {type(error).__name__}\n"
            f"Сообщение: {str(error)}\n"
        )
        
        if context:
            text += "\nКонтекст:\n"
            for key, value in context.items():
                text += f"- {key}: {value}\n"
                
        await self.send_message(admin_chat_id, text)

    async def notify_new_transaction(
        self,
        transaction: Transaction,
        admin_chat_id: int
    ) -> None:
        """
        Уведомление о новой транзакции для администратора.

        Args:
            transaction: объект Transaction
            admin_chat_id: ID чата администратора
        """
        text = (
            "🆕 Новая транзакция:\n\n"
            f"Сумма: {format_money(transaction.amount)}\n"
            f"Тип: {transaction.type.value}\n"
            f"Категория: {transaction.category}\n"
            f"Описание: {transaction.description}\n"
            f"Дата: {format_datetime(transaction.created_at)}"
        )
        await self.send_message(admin_chat_id, text)

    async def check_and_send_reminders(
        self,
        appointments: List[Appointment],
        clients: Dict[int, Client]
    ) -> None:
        """
        Проверка и отправка напоминаний о записях
        
        Args:
            appointments: список активных записей
            clients: словарь клиентов {client_id: Client}
        """
        now = datetime.now()
        
        for appointment in appointments:
            # Пропускаем отмененные записи
            if appointment.status == AppointmentStatus.CANCELLED:
                continue
                
            # Получаем клиента
            client = clients.get(appointment.client_id)
            if not client:
                continue
                
            time_diff = appointment.appointment_time - now
            hours_until = time_diff.total_seconds() / 3600
            
            # Отправляем уведомление за 24 часа
            if 23.5 <= hours_until <= 24.5:
                await self.send_appointment_reminder(
                    appointment,
                    client,
                    hours_before=24
                )
                
            # Отправляем уведомление за 2 часа
            elif 1.5 <= hours_until <= 2.5:
                await self.send_appointment_reminder(
                    appointment,
                    client,
                    hours_before=2
                )
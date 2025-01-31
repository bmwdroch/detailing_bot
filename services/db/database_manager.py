"""
Модуль для работы с базой данных.
Предоставляет асинхронные методы для всех операций с БД.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple

import aiosqlite

from core.models import Appointment, Client, Service, Transaction
from services.db.queries import AppointmentQueries, ClientQueries, ServiceQueries, SettingsQueries, TransactionQueries
from utils.validators import (
    validate_amount, validate_appointment_time, validate_car_info,
    validate_category, validate_comment, validate_name, validate_phone, validate_service_description, validate_service_duration, validate_service_name, validate_service_price,
    validate_status, validate_transaction_type
)


class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, database_path: str):
        """
        Инициализация менеджера БД
        
        Args:
            database_path: путь к файлу SQLite
        """
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)

    async def init_db(self) -> None:
        """Инициализация базы данных"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(ClientQueries.CREATE_TABLE)
                await db.execute(AppointmentQueries.CREATE_TABLE)
                await db.execute(TransactionQueries.CREATE_TABLE)
                await db.execute(SettingsQueries.CREATE_TABLE)
                
                # Добавляем значения по умолчанию для контактов
                default_contacts = (
                    "📞 Наши контакты:\n\n"
                    "Администраторы:\n"
                    "- Александр: +7 (999) 765-43-21\n\n"
                    "Мастера:\n"
                    "- Андрей (основной мастер): +7 (999) 111-22-33\n"
                    "- Дмитрий (помощник): +7 (999) 444-55-66\n\n"
                    "Адрес: ул. Примерная, д. 1\n"
                    "Время работы: 9:00 - 20:00\n\n"
                    "Для записи используйте бот или звоните администраторам."
                )
                await db.execute(
                    SettingsQueries.INSERT,
                    ("contacts", default_contacts, datetime.now())
                )
                
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    async def get_setting(self, key: str) -> Optional[str]:
        """
        Получение значения настройки
        
        Args:
            key: ключ настройки
            
        Returns:
            Optional[str]: значение настройки
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(SettingsQueries.GET_BY_KEY, (key,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {e}")
            return None

    async def update_setting(
        self,
        key: str,
        value: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Обновление значения настройки
        
        Args:
            key: ключ настройки
            value: новое значение
            
        Returns:
            Tuple[bool, Optional[str]]: (успех, текст ошибки)
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(
                    SettingsQueries.UPDATE,
                    (value, datetime.now(), key)
                )
                await db.commit()
                return True, None
        except Exception as e:
            self.logger.error(f"Error updating setting {key}: {e}")
            return False, str(e)

    async def add_client(self, telegram_id: int, name: str, phone: str) -> Tuple[bool, Optional[str], Optional[Client]]:
        """
        Добавление нового клиента
        
        Args:
            telegram_id: ID пользователя в Telegram
            name: ФИО клиента
            phone: номер телефона

        Returns:
            Tuple[bool, Optional[str], Optional[Client]]: 
            - успех операции
            - текст ошибки (если есть)
            - объект клиента (если создан успешно)
        """
        # Валидация данных
        name_valid, name_error = validate_name(name)
        if not name_valid:
            return False, name_error, None

        phone_valid, phone_error = validate_phone(phone)
        if not phone_valid:
            return False, phone_error, None

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Проверяем существование клиента
                async with db.execute(ClientQueries.GET_BY_TELEGRAM_ID, (telegram_id,)) as cursor:
                    if await cursor.fetchone():
                        return False, "Клиент уже существует", None

                # Добавляем клиента
                created_at = datetime.now()
                await db.execute(ClientQueries.INSERT, (telegram_id, name, phone, created_at))
                await db.commit()

                # Получаем созданного клиента
                async with db.execute(ClientQueries.GET_BY_TELEGRAM_ID, (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    client = Client.from_db(row)
                    self.logger.info(f"Added new client: {client}")
                    return True, None, client

        except Exception as e:
            self.logger.error(f"Error adding client: {e}")
            return False, "Ошибка при добавлении клиента", None

    async def get_client(self, telegram_id: int) -> Optional[Client]:
        """Получение клиента по Telegram ID"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(ClientQueries.GET_BY_TELEGRAM_ID, (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    return Client.from_db(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting client: {e}")
            return None

    async def add_appointment(
        self, 
        client_id: int,
        service_type: str,
        car_info: str,
        appointment_time: datetime,
        comment: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Appointment]]:
        """
        Добавление новой записи
        
        Args:
            client_id: ID клиента
            service_type: тип услуги
            car_info: информация об автомобиле
            appointment_time: время записи
            comment: комментарий (опционально)

        Returns:
            Tuple[bool, Optional[str], Optional[Appointment]]:
            - успех операции
            - текст ошибки (если есть)
            - объект записи (если создана успешно)
        """
        # Валидация данных
        car_valid, car_error = validate_car_info(car_info)
        if not car_valid:
            return False, car_error, None

        time_valid, time_error = validate_appointment_time(appointment_time)
        if not time_valid:
            return False, time_error, None

        if comment:
            comment_valid, comment_error = validate_comment(comment)
            if not comment_valid:
                return False, comment_error, None

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Проверяем существование клиента
                async with db.execute(ClientQueries.GET_BY_ID, (client_id,)) as cursor:
                    if not await cursor.fetchone():
                        return False, "Клиент не найден", None

                # Добавляем запись
                created_at = datetime.now()
                await db.execute(
                    AppointmentQueries.INSERT,
                    (
                        client_id,
                        service_type,
                        car_info,
                        appointment_time,
                        'pending',  # Начальный статус
                        comment,
                        created_at
                    )
                )
                await db.commit()

                # Получаем созданную запись
                cursor = await db.execute(
                    "SELECT id FROM appointments WHERE client_id = ? ORDER BY created_at DESC LIMIT 1",
                    (client_id,)
                )
                row = await cursor.fetchone()
                if row:
                    appointment_id = row[0]
                    async with db.execute(AppointmentQueries.GET_BY_ID, (appointment_id,)) as cursor:
                        row = await cursor.fetchone()
                        appointment = Appointment.from_db(row)
                        self.logger.info(f"Added new appointment: {appointment}")
                        return True, None, appointment

                return False, "Ошибка при создании записи", None

        except Exception as e:
            self.logger.error(f"Error adding appointment: {e}")
            return False, "Ошибка при добавлении записи", None

    async def update_appointment_status(
        self, 
        appointment_id: int, 
        status: str
    ) -> Tuple[bool, Optional[str]]:
        """Обновление статуса записи"""
        # Валидация статуса
        status_valid, status_error = validate_status(status)
        if not status_valid:
            return False, status_error

        try:
            async with aiosqlite.connect(self.database_path) as db:
                await db.execute(AppointmentQueries.UPDATE_STATUS, (status, appointment_id))
                await db.commit()
                self.logger.info(f"Updated appointment {appointment_id} status to {status}")
                return True, None
        except Exception as e:
            self.logger.error(f"Error updating appointment status: {e}")
            return False, "Ошибка при обновлении статуса"

    async def add_transaction(
        self,
        amount: str,
        type_: str,
        category: str,
        description: str,
        appointment_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Optional[Transaction]]:
        """
        Добавление новой транзакции
        
        Args:
            amount: сумма
            type_: тип транзакции (income/expense)
            category: категория
            description: описание
            appointment_id: ID записи (опционально)

        Returns:
            Tuple[bool, Optional[str], Optional[Transaction]]:
            - успех операции
            - текст ошибки (если есть)
            - объект транзакции (если создана успешно)
        """
        # Валидация данных
        amount_valid, amount_error = validate_amount(amount)
        if not amount_valid:
            return False, amount_error, None

        type_valid, type_error = validate_transaction_type(type_)
        if not type_valid:
            return False, type_error, None

        category_valid, category_error = validate_category(category)
        if not category_valid:
            return False, category_error, None

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Если указан appointment_id, проверяем его существование
                if appointment_id:
                    async with db.execute(AppointmentQueries.GET_BY_ID, (appointment_id,)) as cursor:
                        if not await cursor.fetchone():
                            return False, "Запись не найдена", None

                # Добавляем транзакцию
                created_at = datetime.now()
                await db.execute(
                    TransactionQueries.INSERT,
                    (appointment_id, amount, type_, category, description, created_at)
                )
                await db.commit()

                # Получаем созданную транзакцию
                cursor = await db.execute(
                    "SELECT id FROM transactions ORDER BY created_at DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                if row:
                    transaction_id = row[0]
                    async with db.execute(TransactionQueries.GET_BY_ID, (transaction_id,)) as cursor:
                        row = await cursor.fetchone()
                        transaction = Transaction.from_db(row)
                        self.logger.info(f"Added new transaction: {transaction}")
                        return True, None, transaction

                return False, "Ошибка при создании транзакции", None

        except Exception as e:
            self.logger.error(f"Error adding transaction: {e}")
            return False, "Ошибка при добавлении транзакции", None

    async def get_upcoming_appointments(self) -> List[Appointment]:
        """Получение предстоящих записей"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                now = datetime.now()
                async with db.execute(AppointmentQueries.GET_UPCOMING, (now,)) as cursor:
                    rows = await cursor.fetchall()
                    return [Appointment.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting upcoming appointments: {e}")
            return []

    async def get_client_appointments(self, client_id: int) -> List[Appointment]:
        """Получение всех записей клиента"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(AppointmentQueries.GET_BY_CLIENT, (client_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [Appointment.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting client appointments: {e}")
            return []

    async def get_transactions_by_date(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Transaction]:
        """Получение транзакций за период"""
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(
                    TransactionQueries.GET_BY_DATE_RANGE,
                    (start_date, end_date)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [Transaction.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting transactions by date: {e}")
            return []
            
    async def add_service(
        self,
        name: str,
        description: str,
        price: str,
        duration: int,
        is_active: bool = True
    ) -> Tuple[bool, Optional[str], Optional[Service]]:
        """
        Добавление новой услуги
        
        Args:
            name: название услуги
            description: описание услуги
            price: стоимость услуги
            duration: длительность в минутах
            is_active: активна ли услуга
            
        Returns:
            (успех, текст ошибки, объект услуги)
        """
        # Валидация данных
        name_valid, name_error = validate_service_name(name)
        if not name_valid:
            return False, name_error, None
            
        desc_valid, desc_error = validate_service_description(description)
        if not desc_valid:
            return False, desc_error, None
            
        price_valid, price_error = validate_service_price(price)
        if not price_valid:
            return False, price_error, None
            
        duration_valid, duration_error = validate_service_duration(duration)
        if not duration_valid:
            return False, duration_error, None

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Проверяем уникальность названия
                async with db.execute(
                    "SELECT id FROM services WHERE name = ?", 
                    (name,)
                ) as cursor:
                    if await cursor.fetchone():
                        return False, "Услуга с таким названием уже существует", None

                # Добавляем услугу
                now = datetime.now()
                await db.execute(
                    ServiceQueries.INSERT,
                    (name, description, str(price), duration, is_active, now, now)
                )
                await db.commit()

                # Получаем созданную услугу
                async with db.execute(
                    "SELECT * FROM services WHERE name = ?",
                    (name,)
                ) as cursor:
                    row = await cursor.fetchone()
                    service = Service.from_db(row)
                    self.logger.info(f"Added new service: {service}")
                    return True, None, service

        except Exception as e:
            self.logger.error(f"Error adding service: {e}")
            return False, "Ошибка при добавлении услуги", None

    async def update_service(
        self,
        service_id: int,
        name: str,
        description: str,
        price: str,
        duration: int,
        is_active: bool
    ) -> Tuple[bool, Optional[str], Optional[Service]]:
        """
        Обновление существующей услуги
        
        Args:
            service_id: ID услуги
            name: новое название
            description: новое описание
            price: новая стоимость
            duration: новая длительность
            is_active: новый статус активности
            
        Returns:
            (успех, текст ошибки, обновленный объект услуги)
        """
        # Валидация данных
        name_valid, name_error = validate_service_name(name)
        if not name_valid:
            return False, name_error, None
            
        desc_valid, desc_error = validate_service_description(description)
        if not desc_valid:
            return False, desc_error, None
            
        price_valid, price_error = validate_service_price(price)
        if not price_valid:
            return False, price_error, None
            
        duration_valid, duration_error = validate_service_duration(duration)
        if not duration_valid:
            return False, duration_error, None

        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Проверяем существование услуги
                async with db.execute(
                    "SELECT id FROM services WHERE id = ?", 
                    (service_id,)
                ) as cursor:
                    if not await cursor.fetchone():
                        return False, "Услуга не найдена", None

                # Проверяем уникальность названия
                async with db.execute(
                    "SELECT id FROM services WHERE name = ? AND id != ?", 
                    (name, service_id)
                ) as cursor:
                    if await cursor.fetchone():
                        return False, "Услуга с таким названием уже существует", None

                # Обновляем услугу
                now = datetime.now()
                await db.execute(
                    ServiceQueries.UPDATE,
                    (name, description, str(price), duration, is_active, now, service_id)
                )
                await db.commit()

                # Получаем обновленную услугу
                async with db.execute(ServiceQueries.GET_BY_ID, (service_id,)) as cursor:
                    row = await cursor.fetchone()
                    service = Service.from_db(row)
                    self.logger.info(f"Updated service: {service}")
                    return True, None, service

        except Exception as e:
            self.logger.error(f"Error updating service: {e}")
            return False, "Ошибка при обновлении услуги", None

    async def get_service(self, service_id: int) -> Optional[Service]:
        """
        Получение услуги по ID
        
        Args:
            service_id: ID услуги
            
        Returns:
            объект услуги или None
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(ServiceQueries.GET_BY_ID, (service_id,)) as cursor:
                    row = await cursor.fetchone()
                    return Service.from_db(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting service: {e}")
            return None

    async def get_active_services(self) -> List[Service]:
        """
        Получение списка активных услуг
        
        Returns:
            список активных услуг
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(ServiceQueries.GET_ACTIVE) as cursor:
                    rows = await cursor.fetchall()
                    return [Service.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting active services: {e}")
            return []

    async def get_all_services(self) -> List[Service]:
        """
        Получение списка всех услуг
        
        Returns:
            список всех услуг
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                async with db.execute(ServiceQueries.GET_ALL) as cursor:
                    rows = await cursor.fetchall()
                    return [Service.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting all services: {e}")
            return []
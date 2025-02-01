# services/db/database_manager.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import aiosqlite

from core.models import Appointment, Client, Service, Transaction, AppointmentStatus
from services.db.queries import AppointmentQueries, ClientQueries, ServiceQueries, SettingsQueries, TransactionQueries
from utils.validators import (
    validate_amount, validate_appointment_time, validate_car_info,
    validate_category, validate_comment, validate_name, validate_phone,
    validate_service_description, validate_service_duration,
    validate_service_name, validate_service_price,
    validate_status, validate_transaction_type
)

class DatabaseManager:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)
        self.conn: Optional[aiosqlite.Connection] = None
        self._client_lock = asyncio.Lock()

    async def init_db(self) -> None:
        try:
            self.conn = await aiosqlite.connect(self.database_path)
            # Настраиваем row_factory, чтобы получать строки в виде кортежей:
            self.conn.row_factory = lambda cursor, row: row
            await self.conn.execute("PRAGMA foreign_keys = ON;")
            await self.conn.execute(ClientQueries.CREATE_TABLE)
            await self.conn.execute(ServiceQueries.CREATE_TABLE)
            await self.conn.execute(AppointmentQueries.CREATE_TABLE)
            await self.conn.execute(TransactionQueries.CREATE_TABLE)
            await self.conn.execute(SettingsQueries.CREATE_TABLE)
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
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.conn.execute(
                SettingsQueries.INSERT,
                ("contacts", default_contacts, now_str)
            )
            await self.conn.commit()
            self.logger.info("Database initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def get_setting(self, key: str) -> Optional[str]:
        """
        Получение значения настройки по ключу
        """
        if not self.conn:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        try:
            cursor = await self.conn.execute(SettingsQueries.GET_BY_KEY, (key,))
            row = await cursor.fetchone()
            await cursor.close()
            return row[0] if row else None
        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {e}")
            return None

    async def update_setting(self, key: str, value: str) -> Tuple[bool, Optional[str]]:
        """
        Обновление (замена) значения настройки
        """
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.conn.execute(
                SettingsQueries.UPDATE,
                (value, now_str, key)
            )
            await self.conn.commit()
            return True, None
        except Exception as e:
            self.logger.error(f"Error updating setting {key}: {e}")
            return False, str(e)

    async def add_client(
        self,
        telegram_id: int,
        name: str,
        phone: str
    ) -> Tuple[bool, Optional[str], Optional[Client]]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        async with self._client_lock:
            try:
                cursor = await self.conn.execute(
                    ClientQueries.GET_BY_TELEGRAM_ID,
                    (telegram_id,)
                )
                exists = await cursor.fetchone()
                await cursor.close()
                if exists:
                    return False, "Клиент уже существует", None

                created_at = datetime.now()
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
                await self.conn.execute(
                    ClientQueries.INSERT,
                    (telegram_id, name, phone, created_at_str)
                )
                await self.conn.commit()
                cursor = await self.conn.execute(
                    ClientQueries.GET_BY_TELEGRAM_ID,
                    (telegram_id,)
                )
                row = await cursor.fetchone()
                await cursor.close()
                if row:
                    client = Client.from_db(row)
                    self.logger.info(f"Added new client: {client}")
                    return True, None, client
                return False, "Не удалось создать клиента", None
            except Exception as e:
                self.logger.error(f"Error adding client: {e}")
                return False, "Ошибка при добавлении клиента", None

    async def get_client(self, telegram_id: int) -> Optional[Client]:
        """Получение клиента по telegram_id."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        try:
            cursor = await self.conn.execute(
                ClientQueries.GET_BY_TELEGRAM_ID, (telegram_id,)
            )
            row = await cursor.fetchone()
            await cursor.close()
            return Client.from_db(row) if row else None

        except Exception as e:
            self.logger.error(f"Error getting client: {e}")
            return None

    async def get_client_by_id(self, client_id: int) -> Optional[Client]:
        """Получение клиента по его id в таблице clients."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(
                ClientQueries.GET_BY_ID, (client_id,)
            )
            row = await cursor.fetchone()
            await cursor.close()
            return Client.from_db(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting client by id: {e}")
            return None

    async def get_all_clients(self) -> List[Client]:
        """Возвращает список всех клиентов."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(ClientQueries.GET_ALL)
            rows = await cursor.fetchall()
            await cursor.close()
            return [Client.from_db(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Error getting all clients: {e}")
            return []

    async def add_appointment(
        self,
        client_id: int,
        *,
        service_id: Optional[int] = None,
        service_type: Optional[str] = None,
        car_info: str,
        appointment_time: datetime,
        comment: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Appointment]]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        is_valid, err = validate_car_info(car_info)
        if not is_valid:
            return False, err, None
        is_valid, err = validate_appointment_time(appointment_time)
        if not is_valid:
            return False, err, None
        if comment:
            is_valid, err = validate_comment(comment)
            if not is_valid:
                return False, err, None

        try:
            # Определяем service_id
            if service_id is None:
                if service_type is None:
                    return False, "Не указана услуга", None
                try:
                    service_id = int(service_type)
                    cursor = await self.conn.execute(
                        "SELECT id FROM services WHERE id = ?",
                        (service_id,)
                    )
                    srow = await cursor.fetchone()
                    await cursor.close()
                    if not srow:
                        return False, "Услуга (ID) не найдена", None
                except ValueError:
                    cursor = await self.conn.execute(
                        "SELECT id FROM services WHERE name = ?",
                        (service_type,)
                    )
                    srow = await cursor.fetchone()
                    await cursor.close()
                    if not srow:
                        return False, "Услуга (name) не найдена", None
                    service_id = srow[0]

            service = await self.get_service(service_id)
            if not service:
                return False, "Услуга не найдена", None

            new_end_time = appointment_time + timedelta(minutes=service.duration)
            existing_appointments = await self.get_appointments_by_date(appointment_time)
            for apt in existing_appointments:
                if apt.status == AppointmentStatus.CANCELLED:
                    continue
                apt_duration = apt.service_duration
                if apt_duration is None:
                    apt_service = await self.get_service(apt.service_id)
                    apt_duration = apt_service.duration if apt_service else 0
                apt_end_time = apt.appointment_time + timedelta(minutes=apt_duration)
                if appointment_time < apt_end_time and new_end_time > apt.appointment_time:
                    return False, "Выбранное время пересекается с другой записью", None

            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            appointment_time_str = appointment_time.strftime("%Y-%m-%d %H:%M:%S")
            status = "pending"
            await self.conn.execute(
                AppointmentQueries.INSERT,
                (client_id, service_id, car_info, appointment_time_str, status, comment, now_str)
            )
            await self.conn.commit()

            cursor = await self.conn.execute("SELECT last_insert_rowid()")
            rowid = await cursor.fetchone()
            await cursor.close()
            if not rowid:
                return False, "Ошибка при создании записи (no rowid)", None

            appointment_id = rowid[0]
            cursor = await self.conn.execute(
                AppointmentQueries.GET_BY_ID,
                (appointment_id,)
            )
            apt_row = await cursor.fetchone()
            await cursor.close()
            if apt_row:
                appointment = Appointment.from_db(apt_row)
                self.logger.info(f"Added new appointment: {appointment}")
                return True, None, appointment
            return False, "Ошибка при создании записи", None

        except Exception as e:
            self.logger.error(f"Error adding appointment: {e}")
            return False, "Ошибка при добавлении записи", None

    async def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        """Получение записи по её ID."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(AppointmentQueries.GET_BY_ID, (appointment_id,))
            row = await cursor.fetchone()
            await cursor.close()
            return Appointment.from_db(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting appointment: {e}")
            return None

    async def update_appointment_status(
        self,
        appointment_id: int,
        status: str
    ) -> Tuple[bool, Optional[str]]:
        """Обновление статуса записи"""
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        from core.models import AppointmentStatus
        if isinstance(status, AppointmentStatus):
            status = status.value

        is_valid, err = validate_status(status)
        if not is_valid:
            return False, err

        try:
            await self.conn.execute(
                AppointmentQueries.UPDATE_STATUS,
                (status, appointment_id)
            )
            await self.conn.commit()
            self.logger.info(f"Updated appointment {appointment_id} status to {status}")
            return True, None
        except Exception as e:
            self.logger.error(f"Error updating appointment status: {e}")
            return False, "Ошибка при обновлении статуса"

    async def get_booked_times(self, date: datetime) -> List[datetime]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            date_str = date.strftime("%Y-%m-%d")
            cursor = await self.conn.execute(AppointmentQueries.GET_BOOKED_TIMES, (date_str,))
            rows = await cursor.fetchall()
            await cursor.close()
            return [datetime.fromisoformat(dt_str) for (dt_str,) in rows]
        except Exception as e:
            self.logger.error(f"Error getting booked times: {e}")
            return []

    async def get_appointments_by_date(self, date: datetime) -> List[Appointment]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            date_str = date.strftime("%Y-%m-%d")
            cursor = await self.conn.execute(AppointmentQueries.GET_BY_DATE_RANGE, (date_str, date_str))
            rows = await cursor.fetchall()
            await cursor.close()
            return [Appointment.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting appointments by date: {e}")
            return []

    async def get_appointments_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Appointment]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cursor = await self.conn.execute(AppointmentQueries.GET_BY_DATE_RANGE, (start_str, end_str))
            rows = await cursor.fetchall()
            await cursor.close()
            return [Appointment.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting appointments by date range: {e}")
            return []

    async def get_upcoming_appointments(self) -> List[Appointment]:
        """Предстоящие (future) записи."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = await self.conn.execute(
                AppointmentQueries.GET_UPCOMING,
                (now_str,)
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [Appointment.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting upcoming appointments: {e}")
            return []

    async def get_client_appointments(self, client_id: int) -> List[Appointment]:
        """Все записи для заданного клиента."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(
                AppointmentQueries.GET_BY_CLIENT,
                (client_id,)
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [Appointment.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting client appointments: {e}")
            return []

    async def add_transaction(
        self,
        amount: str,
        type_: str,
        category: str,
        description: str,
        appointment_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Optional[Transaction]]:
        """Создание финансовой транзакции (income/expense)."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        ok, err = validate_amount(amount)
        if not ok:
            return False, err, None
        ok, err = validate_transaction_type(type_)
        if not ok:
            return False, err, None
        ok, err = validate_category(category)
        if not ok:
            return False, err, None

        try:
            if appointment_id is not None:
                cursor = await self.conn.execute(
                    AppointmentQueries.GET_BY_ID, (appointment_id,)
                )
                apt = await cursor.fetchone()
                await cursor.close()
                if not apt:
                    return False, "Запись (appointment_id) не найдена", None

            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            await self.conn.execute(
                TransactionQueries.INSERT,
                (appointment_id, amount, type_, category, description, now_str)
            )

            cursor = await self.conn.execute("SELECT last_insert_rowid()")
            rowid = await cursor.fetchone()
            await cursor.close()
            if not rowid:
                return False, "Ошибка при создании транзакции (no rowid)", None
            transaction_id = rowid[0]

            cursor = await self.conn.execute(
                TransactionQueries.GET_BY_ID,
                (transaction_id,)
            )
            trow = await cursor.fetchone()
            await cursor.close()
            if trow:
                transaction = Transaction.from_db(trow)
                self.logger.info(f"Added new transaction: {transaction}")
                return True, None, transaction

            return False, "Ошибка при создании транзакции", None

        except Exception as e:
            self.logger.error(f"Error adding transaction: {e}")
            return False, "Ошибка при добавлении транзакции", None

    async def get_transactions_by_date(
        self,
        date: datetime
    ) -> List[Transaction]:
        """
        Транзакции за конкретные сутки (date..date)
        """
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(
                TransactionQueries.GET_BY_DATE_RANGE,
                (date.strftime("%Y-%m-%d"), date.strftime("%Y-%m-%d"))
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [Transaction.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting transactions by date: {e}")
            return []

    async def get_transactions_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Transaction]:
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            cursor = await self.conn.execute(TransactionQueries.GET_BY_DATE_RANGE, (start_str, end_str))
            rows = await cursor.fetchall()
            await cursor.close()
            return [Transaction.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting transactions by date range: {e}")
            return []

    async def get_appointments_count(self) -> int:
        """Просто пример: общее число записей"""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute("SELECT COUNT(*) FROM appointments")
            (cnt,) = await cursor.fetchone()
            await cursor.close()
            return cnt
        except Exception as e:
            self.logger.error(f"Error counting appointments: {e}")
            return 0

    async def get_appointments_paginated(self, page: int, per_page: int) -> List[Appointment]:
        """Пример пагинации: выбираем appointments c limit/offset."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        offset = (page - 1) * per_page
        try:
            query = """
            SELECT a.id, a.client_id, a.service_id, a.car_info,
                   a.appointment_time, a.status, a.comment, a.created_at,
                   s.name as service_name, s.price as service_price, s.duration as service_duration
            FROM appointments a
            JOIN services s ON a.service_id = s.id
            ORDER BY a.appointment_time DESC
            LIMIT ? OFFSET ?
            """
            cursor = await self.conn.execute(query, (per_page, offset))
            rows = await cursor.fetchall()
            await cursor.close()
            return [Appointment.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting paginated appointments: {e}")
            return []

    async def add_service(
        self,
        name: str,
        description: str,
        price: str,
        duration: int,
        is_active: bool = True
    ) -> Tuple[bool, Optional[str], Optional[Service]]:
        """Добавляем новую услугу (service)."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")

        ok, err = validate_service_name(name)
        if not ok:
            return False, err, None
        ok, err = validate_service_description(description)
        if not ok:
            return False, err, None
        ok, err = validate_service_price(price)
        if not ok:
            return False, err, None
        ok, err = validate_service_duration(duration)
        if not ok:
            return False, err, None

        try:
            cursor = await self.conn.execute(
                "SELECT id FROM services WHERE name = ?",
                (name,)
            )
            row = await cursor.fetchone()
            await cursor.close()
            if row:
                return False, "Услуга с таким названием уже существует", None

            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            await self.conn.execute(
                ServiceQueries.INSERT,
                (name, description, price, duration, is_active, now_str, now_str)
            )
            await self.conn.commit()

            cursor = await self.conn.execute("SELECT last_insert_rowid()")
            (new_id,) = await cursor.fetchone()
            await cursor.close()

            cursor = await self.conn.execute(ServiceQueries.GET_BY_ID, (new_id,))
            srow = await cursor.fetchone()
            await cursor.close()
            if srow:
                service = Service.from_db(srow)
                return True, None, service
            return False, "Ошибка при создании услуги (no row)", None

        except Exception as e:
            self.logger.error(f"Error adding service: {e}")
            return False, "Ошибка при добавлении услуги", None

    async def get_service(self, service_id: int) -> Optional[Service]:
        """Получение услуги по её id."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(ServiceQueries.GET_BY_ID, (service_id,))
            row = await cursor.fetchone()
            await cursor.close()
            if not row:
                return None
            return Service.from_db(row)
        except Exception as e:
            self.logger.error(f"Error getting service: {e}")
            return None

    async def get_active_services(self) -> List[Service]:
        """Список только активных услуг."""
        if not self.conn:
            raise RuntimeError("Database not initialized.")
        try:
            cursor = await self.conn.execute(ServiceQueries.GET_ACTIVE)
            rows = await cursor.fetchall()
            await cursor.close()
            return [Service.from_db(r) for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting active services: {e}")
            return []

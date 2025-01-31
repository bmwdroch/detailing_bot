from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class AppointmentStatus(Enum):
    """Статусы записи на услугу"""
    PENDING = "pending"  # Ожидает подтверждения
    CONFIRMED = "confirmed"  # Подтверждена
    COMPLETED = "completed"  # Выполнена
    CANCELLED = "cancelled"  # Отменена
    RESCHEDULED = "rescheduled"  # Перенесена


class TransactionType(Enum):
    """Типы транзакций"""
    INCOME = "income"  # Приход
    EXPENSE = "expense"  # Расход


@dataclass
class Service:
    """Модель услуги"""
    id: Optional[int]  # ID в базе данных
    name: str  # Название услуги
    description: str  # Описание услуги
    price: Decimal  # Стоимость услуги
    duration: int  # Длительность в минутах
    is_active: bool  # Активна ли услуга
    created_at: datetime  # Дата создания
    updated_at: datetime  # Дата последнего обновления

    @classmethod
    def from_db(cls, row: tuple) -> "Service":
        """Создает объект из строки БД"""
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            price=Decimal(str(row[3])),
            duration=row[4],
            is_active=bool(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7])
        )


@dataclass
class Client:
    """Модель клиента"""
    id: Optional[int]  # ID в базе данных
    telegram_id: int  # Telegram ID пользователя
    name: str  # ФИО клиента
    phone: str  # Номер телефона
    created_at: datetime  # Дата создания записи

    @classmethod
    def from_db(cls, row: tuple) -> "Client":
        """Создает объект из строки БД"""
        return cls(
            id=row[0],
            telegram_id=row[1],
            name=row[2],
            phone=row[3],
            created_at=datetime.fromisoformat(row[4])
        )


@dataclass
class Appointment:
    """Модель записи на услугу"""
    id: Optional[int]  # ID в базе данных
    client_id: int  # ID клиента
    service_id: int  # ID услуги
    car_info: str  # Информация об автомобиле
    appointment_time: datetime  # Время записи
    status: AppointmentStatus  # Статус записи
    comment: Optional[str]  # Комментарий
    created_at: datetime  # Дата создания записи

    @classmethod
    def from_db(cls, row: tuple) -> "Appointment":
        """Создает объект из строки БД"""
        return cls(
            id=row[0],
            client_id=row[1],
            service_id=row[2],
            car_info=row[3],
            appointment_time=datetime.fromisoformat(row[4]),
            status=AppointmentStatus(row[5]),
            comment=row[6],
            created_at=datetime.fromisoformat(row[7])
        )


@dataclass
class Transaction:
    """Модель транзакции"""
    id: Optional[int]  # ID в базе данных
    appointment_id: Optional[int]  # ID записи (может быть None для расходов)
    amount: Decimal  # Сумма
    type: TransactionType  # Тип транзакции
    category: str  # Категория
    description: str  # Описание
    created_at: datetime  # Дата создания записи

    @classmethod
    def from_db(cls, row: tuple) -> "Transaction":
        """Создает объект из строки БД"""
        return cls(
            id=row[0],
            appointment_id=row[1],
            amount=Decimal(str(row[2])),
            type=TransactionType(row[3]),
            category=row[4],
            description=row[5],
            created_at=datetime.fromisoformat(row[6])
        )
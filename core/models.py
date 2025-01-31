# core/models.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

class AppointmentStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"

@dataclass
class Service:
    id: Optional[int]
    name: str
    description: str
    price: Decimal
    duration: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, row: tuple) -> "Service":
        return cls(
            id=row[0],
            name=row[1],
            description=row[2],
            price=Decimal(str(row[3])),
            duration=row[4],
            is_active=bool(row[5]),
            created_at=datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
        )

@dataclass
class Client:
    id: Optional[int]
    telegram_id: int
    name: str
    phone: str
    created_at: datetime

    @classmethod
    def from_db(cls, row: tuple) -> "Client":
        return cls(
            id=row[0],
            telegram_id=row[1],
            name=row[2],
            phone=row[3],
            created_at=datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")
        )

@dataclass
class Appointment:
    id: Optional[int]
    client_id: int
    service_id: int
    car_info: str
    appointment_time: datetime
    status: AppointmentStatus
    comment: Optional[str]
    created_at: datetime
    # Дополнительные поля, получаемые из join с таблицей services:
    service_name: Optional[str] = None
    service_price: Optional[Decimal] = None
    service_duration: Optional[int] = None

    @classmethod
    def from_db(cls, row: tuple) -> "Appointment":
        base = cls(
            id=row[0],
            client_id=row[1],
            service_id=row[2],
            car_info=row[3],
            appointment_time=datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S"),
            status=AppointmentStatus(row[5]),
            comment=row[6],
            created_at=datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
        )
        if len(row) >= 10:
            base.service_name = row[8]
            base.service_price = Decimal(str(row[9]))
        if len(row) >= 11:
            base.service_duration = row[10]
        return base

@dataclass
class Transaction:
    id: Optional[int]
    appointment_id: Optional[int]
    amount: Decimal
    type: TransactionType
    category: str
    description: str
    created_at: datetime

    @classmethod
    def from_db(cls, row: tuple) -> "Transaction":
        return cls(
            id=row[0],
            appointment_id=row[1],
            amount=Decimal(str(row[2])),
            type=TransactionType(row[3]),
            category=row[4],
            description=row[5],
            created_at=datetime.strptime(row[6], "%Y-%m-%d %H:%M:%S")
        )

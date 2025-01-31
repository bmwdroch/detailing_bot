"""
Модуль для анализа данных и формирования статистики.
Включает функции для анализа записей, транзакций и общих показателей бизнеса.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from services.db.database_manager import DatabaseManager
from core.models import Appointment, Transaction
from utils.formatters import format_money


class AnalyticsService:
    """Сервис аналитики"""

    def __init__(self, db: DatabaseManager):
        """
        Инициализация сервиса
        
        Args:
            db: объект для работы с БД
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def get_daily_stats(self, date: datetime) -> Dict:
        """
        Получение статистики за день
        
        Args:
            date: дата для анализа
            
        Returns:
            Dict: статистика за день
        """
        try:
            # Получаем все записи за указанный день (по appointment_time)
            appointments = await self.db.get_appointments_by_date(date)
            # Получаем транзакции, связанные с записями, у которых appointment_time соответствует заданной дате
            cursor = await self.db.conn.execute("""
            SELECT id, appointment_id, amount, type, category, description, created_at
            FROM transactions
            WHERE appointment_id IN (
                SELECT id FROM appointments WHERE date(appointment_time) = date(?)
            )
            """, (date,))
            rows = await cursor.fetchall()
            await cursor.close()
            transactions = [Transaction.from_db(r) for r in rows]

            total_appointments = len(appointments)
            completed = sum(1 for a in appointments if a.status.value == 'completed')
            cancelled = sum(1 for a in appointments if a.status.value == 'cancelled')

            income = sum(t.amount for t in transactions if t.type.value == 'income')
            expense = sum(t.amount for t in transactions if t.type.value == 'expense')
            profit = income - expense

            return {
                'date': date,
                'appointments': {
                    'total': total_appointments,
                    'completed': completed,
                    'cancelled': cancelled,
                    'conversion': round(completed / total_appointments * 100 if total_appointments else 0, 2)
                },
                'finances': {
                    'income': income,
                    'expense': expense,
                    'profit': profit
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            return {}

    async def get_period_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Получение статистики за период
        
        Args:
            start_date: начало периода
            end_date: конец периода
            
        Returns:
            Dict: статистика за период
        """
        try:
            # Получаем все записи за период
            appointments = await self.db.get_appointments_by_date_range(
                start_date, end_date
            )
            
            # Получаем все транзакции за период
            transactions = await self.db.get_transactions_by_date_range(
                start_date, end_date
            )
            
            # Считаем статистику по дням
            daily_stats = {}
            current_date = start_date
            while current_date <= end_date:
                # Фильтруем записи и транзакции за текущий день
                day_appointments = [
                    a for a in appointments 
                    if a.appointment_time.date() == current_date.date()
                ]
                day_transactions = [
                    t for t in transactions
                    if t.created_at.date() == current_date.date()
                ]
                
                # Считаем показатели
                appointments_count = len(day_appointments)
                completed = sum(1 for a in day_appointments if a.status.value == 'completed')
                income = sum(t.amount for t in day_transactions if t.type.value == 'income')
                expense = sum(t.amount for t in day_transactions if t.type.value == 'expense')
                
                daily_stats[current_date.date()] = {
                    'appointments': appointments_count,
                    'completed': completed,
                    'income': income,
                    'expense': expense,
                    'profit': income - expense
                }
                
                current_date += timedelta(days=1)
            
            # Считаем общие показатели
            total_appointments = len(appointments)
            total_completed = sum(1 for a in appointments if a.status.value == 'completed')
            total_cancelled = sum(1 for a in appointments if a.status.value == 'cancelled')
            total_income = sum(t.amount for t in transactions if t.type.value == 'income')
            total_expense = sum(t.amount for t in transactions if t.type.value == 'expense')
            
            # Считаем средние показатели
            avg_daily_appointments = total_appointments / len(daily_stats) if daily_stats else 0
            avg_daily_income = total_income / len(daily_stats) if daily_stats else 0
            avg_check = total_income / total_completed if total_completed else 0
            
            return {
                'period': {
                    'start': start_date,
                    'end': end_date,
                    'days': len(daily_stats)
                },
                'total': {
                    'appointments': total_appointments,
                    'completed': total_completed,
                    'cancelled': total_cancelled,
                    'conversion': round(total_completed / total_appointments * 100 if total_appointments else 0, 2),
                    'income': total_income,
                    'expense': total_expense,
                    'profit': total_income - total_expense
                },
                'average': {
                    'daily_appointments': round(avg_daily_appointments, 2),
                    'daily_income': avg_daily_income,
                    'check': avg_check
                },
                'daily': daily_stats
            }
        except Exception as e:
            self.logger.error(f"Error getting period stats: {e}")
            return {}

    async def get_popular_services(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> List[Dict]:
        """
        Получение списка популярных услуг
        
        Args:
            start_date: начало периода
            end_date: конец периода
            limit: количество услуг в выборке
            
        Returns:
            List[Dict]: список популярных услуг с метриками
        """
        try:
            # Получаем все выполненные записи за период
            appointments = await self.db.get_appointments_by_date_range(
                start_date, end_date
            )
            completed = [a for a in appointments if a.status.value == 'completed']
            
            # Группируем по услугам
            services_stats = {}
            for appointment in completed:
                if appointment.service_id not in services_stats:
                    services_stats[appointment.service_id] = {
                        'count': 0,
                        'total_amount': Decimal('0')
                    }
                services_stats[appointment.service_id]['count'] += 1
                services_stats[appointment.service_id]['total_amount'] += appointment.service_price
            
            # Формируем результат
            result = []
            for service_id, stats in services_stats.items():
                service = await self.db.get_service(service_id)
                if service:
                    result.append({
                        'service_id': service_id,
                        'name': service.name,
                        'count': stats['count'],
                        'total_amount': stats['total_amount'],
                        'average_amount': stats['total_amount'] / stats['count'],
                        'share': round(stats['count'] / len(completed) * 100 if completed else 0, 2)
                    })
            
            # Сортируем по количеству записей
            result.sort(key=lambda x: x['count'], reverse=True)
            return result[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting popular services: {e}")
            return []

    async def get_busy_hours(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[int, int]:
        """
        Анализ загруженности по часам
        
        Args:
            start_date: начало периода
            end_date: конец периода
            
        Returns:
            Dict[int, int]: количество записей по часам
        """
        try:
            # Получаем все подтвержденные и выполненные записи
            appointments = await self.db.get_appointments_by_date_range(
                start_date, end_date
            )
            valid_appointments = [
                a for a in appointments 
                if a.status.value in ('confirmed', 'completed')
            ]
            
            # Считаем количество записей по часам
            hours_stats = {hour: 0 for hour in range(24)}
            for appointment in valid_appointments:
                hour = appointment.appointment_time.hour
                hours_stats[hour] += 1
                
            return hours_stats
            
        except Exception as e:
            self.logger.error(f"Error getting busy hours: {e}")
            return {}

    async def get_conversion_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Анализ конверсии из заявки в выполненный заказ
        
        Args:
            start_date: начало периода
            end_date: конец периода
            
        Returns:
            Dict: статистика конверсии
        """
        try:
            # Получаем все записи за период
            appointments = await self.db.get_appointments_by_date_range(
                start_date, end_date
            )
            
            # Считаем количество по статусам
            total = len(appointments)
            by_status = {
                'pending': 0,
                'confirmed': 0,
                'completed': 0,
                'cancelled': 0,
                'rescheduled': 0
            }
            
            for appointment in appointments:
                by_status[appointment.status.value] += 1
            
            # Считаем конверсии
            return {
                'total_appointments': total,
                'by_status': by_status,
                'conversion_rates': {
                    'pending_to_confirmed': round(by_status['confirmed'] / by_status['pending'] * 100 if by_status['pending'] else 0, 2),
                    'confirmed_to_completed': round(by_status['completed'] / by_status['confirmed'] * 100 if by_status['confirmed'] else 0, 2),
                    'total_conversion': round(by_status['completed'] / total * 100 if total else 0, 2)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversion stats: {e}")
            return {}

    async def get_clients_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Анализ клиентской базы
        
        Args:
            start_date: начало периода
            end_date: конец периода
            
        Returns:
            Dict: статистика по клиентам
        """
        try:
            # Получаем все записи за период
            appointments = await self.db.get_appointments_by_date_range(
                start_date, end_date
            )
            
            # Группируем записи по клиентам
            clients_stats = {}
            for appointment in appointments:
                if appointment.client_id not in clients_stats:
                    clients_stats[appointment.client_id] = {
                        'total_appointments': 0,
                        'completed_appointments': 0,
                        'cancelled_appointments': 0,
                        'total_spent': Decimal('0')
                    }
                
                stats = clients_stats[appointment.client_id]
                stats['total_appointments'] += 1
                
                if appointment.status.value == 'completed':
                    stats['completed_appointments'] += 1
                    stats['total_spent'] += appointment.service_price
                elif appointment.status.value == 'cancelled':
                    stats['cancelled_appointments'] += 1
            
            # Считаем средние показатели
            total_clients = len(clients_stats)
            if total_clients:
                avg_appointments = sum(s['total_appointments'] for s in clients_stats.values()) / total_clients
                avg_completed = sum(s['completed_appointments'] for s in clients_stats.values()) / total_clients
                avg_spent = sum(s['total_spent'] for s in clients_stats.values()) / total_clients
            else:
                avg_appointments = avg_completed = avg_spent = 0
            
            # Считаем распределение клиентов по количеству записей
            appointments_distribution = {
                '1': sum(1 for s in clients_stats.values() if s['total_appointments'] == 1),
                '2-3': sum(1 for s in clients_stats.values() if 2 <= s['total_appointments'] <= 3),
                '4-5': sum(1 for s in clients_stats.values() if 4 <= s['total_appointments'] <= 5),
                '6+': sum(1 for s in clients_stats.values() if s['total_appointments'] >= 6)
            }
            
            return {
                'total_clients': total_clients,
                'average': {
                    'appointments': round(avg_appointments, 2),
                    'completed': round(avg_completed, 2),
                    'spent': avg_spent
                },
                'appointments_distribution': appointments_distribution
            }
            
        except Exception as e:
            self.logger.error(f"Error getting clients stats: {e}")
            return {}
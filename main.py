# main.py
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from config.config import Config
from handlers import admin_handlers, client_handlers, payment_handlers
from middleware.admin import AdminMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.access_control import AccessControlMiddleware
from middleware.logging import LoggingMiddleware
from services.analytics.analytics import AnalyticsService
from services.db.database_manager import DatabaseManager
from services.notifications.notification_service import NotificationService
from services.logging.log_service import LogService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

async def setup_services(bot: Bot) -> dict:
    """
    Инициализация сервисов бота
    
    Args:
        bot: объект бота
        
    Returns:
        dict: словарь с сервисами
    """
    try:
        # Инициализируем базу данных
        db_path = Path("data/database.sqlite")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager(str(db_path))
        await db.init_db()
        
        # Инициализируем логирование
        log_service = LogService()
        
        # Инициализируем остальные сервисы
        notifications = NotificationService(bot)
        analytics = AnalyticsService(db)
        
        return {
            "db": db,
            "log": log_service,
            "notifications": notifications,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.critical(f"Error setting up services: {e}")
        raise

async def setup_middlewares(dp: Dispatcher, config: Config, services: dict) -> None:
    """
    Регистрация мидлварей
    
    Args:
        dp: диспетчер
        config: конфигурация
        services: словарь сервисов
    """
    dp.message.middleware.register(AdminMiddleware(config.admin_ids))
    dp.callback_query.middleware.register(AdminMiddleware(config.admin_ids))
    dp.message.middleware.register(RateLimitMiddleware())
    dp.message.middleware.register(AccessControlMiddleware(services["db"]))
    dp.callback_query.middleware.register(AccessControlMiddleware(services["db"]))
    dp.message.middleware.register(LoggingMiddleware(services["log"]))
    dp.callback_query.middleware.register(LoggingMiddleware(services["log"]))

async def register_handlers(dp: Dispatcher) -> None:
    """
    Регистрация обработчиков команд
    
    Args:
        dp: диспетчер
    """
    # Регистрируем все роутеры
    dp.include_router(client_handlers.router)
    dp.include_router(admin_handlers.router) 
    dp.include_router(payment_handlers.router)

async def start_services(services: dict) -> None:
    """
    Запуск фоновых задач сервисов
    
    Args:
        services: словарь с сервисами
    """
    # Здесь можно запустить периодические задачи
    pass

async def check_reminders(services: dict) -> None:
    """
    Периодическая проверка и отправка напоминаний
    
    Args:
        services: словарь сервисов
    """
    while True:
        try:
            now = datetime.now()
            end_date = now + timedelta(days=2)
            appointments = await services["db"].get_appointments_by_date_range(now, end_date)
            client_ids = {a.client_id for a in appointments}
            clients = {}
            for client_id in client_ids:
                client = await services["db"].get_client_by_id(client_id)
                if client:
                    clients[client_id] = client
            await services["notifications"].check_and_send_reminders(appointments, clients)
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")
        await asyncio.sleep(1800)

async def main() -> None:
    """Точка входа"""
    bot = None  # Инициализируем bot заранее
    reminder_task = None
    try:
        # Загружаем конфигурацию
        config = Config()
        
        # Создаем объект бота, используя DefaultBotProperties для установки parse_mode
        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        bot.config = config
        
        # Инициализируем диспетчер
        dp = Dispatcher()
        
        # Настраиваем сервисы
        services = await setup_services(bot)
        
        # Регистрируем мидлвари
        await setup_middlewares(dp, config, services)
        
        # Регистрируем обработчики
        await register_handlers(dp)
        
        # Запускаем фоновые задачи
        reminder_task = asyncio.create_task(check_reminders(services))
        
        # Пропускаем накопившиеся апдейты и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            **services
        )
        
    except Exception as e:
        logger.critical(f"Error starting bot: {e}")
        sys.exit(1)
    finally:
        if reminder_task is not None:
            reminder_task.cancel()  # Отменяем задачу при выходе
        if bot is not None:
            await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")

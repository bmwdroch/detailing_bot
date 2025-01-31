# services/db/connection_pool.py
import asyncio
import aiosqlite
from typing import AsyncGenerator
import logging

class DatabasePool:
    """Пул подключений к БД"""
    
    def __init__(self, database_path: str, pool_size: int = 5):
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool = asyncio.Queue(maxsize=pool_size)
        self.logger = logging.getLogger(__name__)
        
    async def init(self):
        """Инициализация пула"""
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.database_path)
            await self.pool.put(conn)
            
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Получение соединения из пула"""
        try:
            conn = await self.pool.get()
            yield conn
            await self.pool.put(conn)
        except Exception as e:
            self.logger.error(f"Error getting connection: {e}")
            raise
            
    async def close(self):
        """Закрытие всех соединений"""
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()
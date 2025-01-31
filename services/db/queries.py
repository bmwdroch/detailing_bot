"""
Модуль содержит SQL-запросы для работы с базой данных.
Каждый класс представляет набор запросов для соответствующей таблицы.
"""


class ServiceQueries:
    """SQL-запросы для работы с таблицей services"""
    
    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price DECIMAL NOT NULL,
        duration INTEGER NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """

    INSERT = """
    INSERT INTO services (
        name, description, price, duration,
        is_active, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    UPDATE = """
    UPDATE services
    SET name = ?,
        description = ?,
        price = ?,
        duration = ?,
        is_active = ?,
        updated_at = ?
    WHERE id = ?
    """

    GET_BY_ID = """
    SELECT id, name, description, price,
           duration, is_active, created_at, updated_at
    FROM services
    WHERE id = ?
    """

    GET_ACTIVE = """
    SELECT id, name, description, price,
           duration, is_active, created_at, updated_at
    FROM services
    WHERE is_active = 1
    ORDER BY name
    """

    GET_ALL = """
    SELECT id, name, description, price,
           duration, is_active, created_at, updated_at
    FROM services
    ORDER BY name
    """


class ClientQueries:
    """SQL-запросы для работы с таблицей clients"""
    
    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    """

    INSERT = """
    INSERT INTO clients (telegram_id, name, phone, created_at)
    VALUES (?, ?, ?, ?)
    """

    UPDATE = """
    UPDATE clients
    SET name = ?, phone = ?
    WHERE telegram_id = ?
    """

    GET_BY_TELEGRAM_ID = """
    SELECT id, telegram_id, name, phone, created_at
    FROM clients
    WHERE telegram_id = ?
    """

    GET_BY_ID = """
    SELECT id, telegram_id, name, phone, created_at
    FROM clients
    WHERE id = ?
    """

    GET_ALL = """
    SELECT id, telegram_id, name, phone, created_at
    FROM clients
    ORDER BY id
    """

    DELETE = """
    DELETE FROM clients
    WHERE telegram_id = ?
    """


class AppointmentQueries:
    """SQL-запросы для работы с таблицей appointments"""

    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY,
        client_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        car_info TEXT NOT NULL,
        appointment_time TIMESTAMP NOT NULL,
        status TEXT NOT NULL,
        comment TEXT,
        created_at TIMESTAMP NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (service_id) REFERENCES services(id)
    )
    """

    INSERT = """
    INSERT INTO appointments (
        client_id, service_id, car_info, 
        appointment_time, status, comment, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    UPDATE = """
    UPDATE appointments
    SET service_id = ?,
        car_info = ?,
        appointment_time = ?,
        status = ?,
        comment = ?
    WHERE id = ?
    """

    UPDATE_STATUS = """
    UPDATE appointments
    SET status = ?
    WHERE id = ?
    """

    GET_BY_ID = """
    SELECT a.id, a.client_id, a.service_id, a.car_info,
           a.appointment_time, a.status, a.comment, a.created_at,
           s.name as service_name, s.price as service_price
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    WHERE a.id = ?
    """

    GET_BY_CLIENT = """
    SELECT a.id, a.client_id, a.service_id, a.car_info,
           a.appointment_time, a.status, a.comment, a.created_at,
           s.name as service_name, s.price as service_price
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    WHERE a.client_id = ?
    ORDER BY a.appointment_time DESC
    """

    GET_UPCOMING = """
    SELECT a.id, a.client_id, a.service_id, a.car_info,
           a.appointment_time, a.status, a.comment, a.created_at,
           s.name as service_name, s.price as service_price
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    WHERE a.appointment_time > ?
        AND a.status IN ('pending', 'confirmed')
    ORDER BY a.appointment_time
    """

    GET_FOR_REMINDER = """
    SELECT a.id, a.client_id, a.service_id, a.car_info,
           a.appointment_time, a.status, a.comment, a.created_at,
           s.name as service_name, s.price as service_price,
           c.telegram_id
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    JOIN clients c ON a.client_id = c.id
    WHERE a.appointment_time BETWEEN ? AND ?
        AND a.status = 'confirmed'
    """

    GET_BY_DATE_RANGE = """
    SELECT a.id, a.client_id, a.service_id, a.car_info,
           a.appointment_time, a.status, a.comment, a.created_at,
           s.name as service_name, s.price as service_price, s.duration as service_duration
    FROM appointments a
    JOIN services s ON a.service_id = s.id
    WHERE date(a.appointment_time) BETWEEN date(?) AND date(?)
    ORDER BY a.appointment_time
    """

    GET_BOOKED_TIMES = """
    SELECT appointment_time
    FROM appointments
    WHERE date(appointment_time) = date(?)
        AND status IN ('pending', 'confirmed')
    """

    DELETE = """
    DELETE FROM appointments
    WHERE id = ?
    """


class TransactionQueries:
    """SQL-запросы для работы с таблицей transactions"""

    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        appointment_id INTEGER,
        amount DECIMAL NOT NULL,
        type TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        FOREIGN KEY (appointment_id) REFERENCES appointments(id)
    )
    """

    INSERT = """
    INSERT INTO transactions (
        appointment_id, amount, type,
        category, description, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """

    GET_BY_ID = """
    SELECT id, appointment_id, amount, type,
           category, description, created_at
    FROM transactions
    WHERE id = ?
    """

    GET_BY_APPOINTMENT = """
    SELECT id, appointment_id, amount, type,
           category, description, created_at
    FROM transactions
    WHERE appointment_id = ?
    ORDER BY created_at
    """

    GET_BY_DATE_RANGE = """
    SELECT id, appointment_id, amount, type,
           category, description, created_at
    FROM transactions
    WHERE date(created_at) BETWEEN date(?) AND date(?)
    ORDER BY created_at
    """

    GET_STATS_BY_CATEGORY = """
    SELECT category,
           SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
           SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
    FROM transactions
    WHERE date(created_at) BETWEEN date(?) AND date(?)
    GROUP BY category
    """

    DELETE = """
    DELETE FROM transactions
    WHERE id = ?
    """

class SettingsQueries:
    """SQL-запросы для работы с таблицей settings"""
    
    CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    """

    INSERT = """
    INSERT OR REPLACE INTO settings (key, value, updated_at)
    VALUES (?, ?, ?)
    """

    GET_BY_KEY = """
    SELECT value FROM settings WHERE key = ?
    """

    UPDATE = """
    UPDATE settings 
    SET value = ?, updated_at = ?
    WHERE key = ?
    """
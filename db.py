"""
SQLite database layer for the course-selling Telegram bot.
Uses plain sqlite3 (no ORM) so it's easy to read, debug, and extend.
"""
import sqlite3
import os
import time
import secrets
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "database/bot.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit=False):
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't already exist. Safe to call every startup."""
    with db_cursor(commit=True) as cur:
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            language TEXT DEFAULT 'en',
            notifications_on INTEGER DEFAULT 1,
            role TEXT DEFAULT 'student',        -- student / admin
            is_banned INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            content_url TEXT,          -- link/invite sent after purchase
            is_active INTEGER DEFAULT 1,
            created_at INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE IF NOT EXISTS coupons (
            coupon_id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_percent INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 0,   -- 0 = unlimited
            times_used INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            coupon_code TEXT,
            original_price REAL NOT NULL,
            final_price REAL NOT NULL,
            payment_method TEXT,          -- bKash / Nagad / Rocket / Bank / Other
            payment_txn_id TEXT,          -- transaction ID submitted by student
            status TEXT DEFAULT 'pending', -- pending / verified / rejected
            created_at INTEGER,
            verified_at INTEGER,
            verified_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (course_id) REFERENCES courses(course_id)
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            order_id INTEGER,
            enrolled_at INTEGER,
            UNIQUE(user_id, course_id)
        );

        CREATE TABLE IF NOT EXISTS referral_earnings (
            earning_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',  -- pending / withdrawn
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT,
            account_info TEXT,
            status TEXT DEFAULT 'pending',  -- pending / paid / rejected
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'open',    -- open / answered / closed
            admin_reply TEXT,
            created_at INTEGER,
            updated_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,             -- INFO / ERROR
            source TEXT,
            message TEXT,
            created_at INTEGER
        );
        """)


def log_event(level: str, source: str, message: str):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO logs (level, source, message, created_at) VALUES (?, ?, ?, ?)",
            (level, source, message, int(time.time())),
        )


def gen_referral_code(user_id: int) -> str:
    return f"REF{user_id}{secrets.token_hex(2).upper()}"

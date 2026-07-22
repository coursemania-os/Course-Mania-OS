import time
from database.db import db_cursor


def get_categories():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM categories ORDER BY name")
        return [dict(r) for r in cur.fetchall()]


def add_category(name):
    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        return cur.lastrowid


def get_courses_by_category(category_id):
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM courses WHERE category_id = ? AND is_active = 1 ORDER BY title
        """, (category_id,))
        return [dict(r) for r in cur.fetchall()]


def get_all_courses(active_only=False):
    with db_cursor() as cur:
        if active_only:
            cur.execute("SELECT * FROM courses WHERE is_active = 1 ORDER BY created_at DESC")
        else:
            cur.execute("SELECT * FROM courses ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


def get_course(course_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_course(category_id, title, description, price, content_url):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO courses (category_id, title, description, price, content_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (category_id, title, description, price, content_url, int(time.time())))
        return cur.lastrowid


def update_course(course_id, **fields):
    allowed = {"title", "description", "price", "content_url", "category_id", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with db_cursor(commit=True) as cur:
        cur.execute(f"UPDATE courses SET {set_clause} WHERE course_id = ?",
                    (*updates.values(), course_id))


def delete_course(course_id):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE courses SET is_active = 0 WHERE course_id = ?", (course_id,))


def get_user_courses(user_id):
    """Courses a user is enrolled in."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT c.* FROM courses c
            JOIN enrollments e ON e.course_id = c.course_id
            WHERE e.user_id = ?
            ORDER BY e.enrolled_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def is_enrolled(user_id, course_id):
    with db_cursor() as cur:
        cur.execute("SELECT 1 FROM enrollments WHERE user_id = ? AND course_id = ?",
                    (user_id, course_id))
        return cur.fetchone() is not None


def enroll_user(user_id, course_id, order_id):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT OR IGNORE INTO enrollments (user_id, course_id, order_id, enrolled_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, course_id, order_id, int(time.time())))

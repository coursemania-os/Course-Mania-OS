import time
from database.db import db_cursor, gen_referral_code


def get_or_create_user(user_id, username, full_name, referred_by_code=None):
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)

        referred_by = None
        if referred_by_code:
            cur.execute("SELECT user_id FROM users WHERE referral_code = ?", (referred_by_code,))
            ref_row = cur.fetchone()
            if ref_row and ref_row["user_id"] != user_id:
                referred_by = ref_row["user_id"]

        code = gen_referral_code(user_id)
        cur.execute("""
            INSERT INTO users (user_id, username, full_name, referral_code, referred_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, full_name, code, referred_by, int(time.time())))

        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return dict(cur.fetchone())


def get_user(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def is_admin(user_id, admin_ids):
    return user_id in admin_ids


def update_user_field(user_id, field, value):
    allowed = {"phone", "language", "notifications_on", "role", "is_banned", "full_name"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not editable")
    with db_cursor(commit=True) as cur:
        cur.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))


def search_users(query):
    """Search by user_id, username, or full_name."""
    with db_cursor() as cur:
        like = f"%{query}%"
        cur.execute("""
            SELECT * FROM users
            WHERE CAST(user_id AS TEXT) LIKE ? OR username LIKE ? OR full_name LIKE ?
            LIMIT 20
        """, (like, like, like))
        return [dict(r) for r in cur.fetchall()]


def ban_user(user_id, banned=True):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))


def get_referral_stats(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?", (user_id,))
        total_referrals = cur.fetchone()["cnt"]

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM referral_earnings
            WHERE referrer_id = ? AND status = 'pending'
        """, (user_id,))
        pending_earnings = cur.fetchone()["total"]

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM referral_earnings
            WHERE referrer_id = ? AND status = 'withdrawn'
        """, (user_id,))
        withdrawn_earnings = cur.fetchone()["total"]

        return {
            "total_referrals": total_referrals,
            "pending_earnings": pending_earnings,
            "withdrawn_earnings": withdrawn_earnings,
        }


def get_all_user_ids(only_active=True):
    with db_cursor() as cur:
        if only_active:
            cur.execute("SELECT user_id FROM users WHERE is_banned = 0")
        else:
            cur.execute("SELECT user_id FROM users")
        return [r["user_id"] for r in cur.fetchall()]

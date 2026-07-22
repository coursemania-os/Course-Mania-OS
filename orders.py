import time
from database.db import db_cursor

REFERRAL_COMMISSION_PERCENT = 10  # % of final price credited to referrer on verified order


# ---------- Coupons ----------

def get_coupon(code):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_coupon(code, discount_percent, max_uses=0):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO coupons (code, discount_percent, max_uses, created_at)
            VALUES (?, ?, ?, ?)
        """, (code, discount_percent, max_uses, int(time.time())))


def use_coupon(code):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE coupons SET times_used = times_used + 1 WHERE code = ?", (code,))


def get_all_coupons():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM coupons ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


def deactivate_coupon(code):
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE coupons SET is_active = 0 WHERE code = ?", (code,))


def is_coupon_valid(coupon):
    if not coupon or not coupon["is_active"]:
        return False
    if coupon["max_uses"] and coupon["times_used"] >= coupon["max_uses"]:
        return False
    return True


# ---------- Orders ----------

def create_order(user_id, course_id, original_price, final_price, coupon_code=None):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO orders (user_id, course_id, coupon_code, original_price, final_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, course_id, coupon_code, original_price, final_price, int(time.time())))
        return cur.lastrowid


def attach_payment_info(order_id, payment_method, txn_id):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE orders SET payment_method = ?, payment_txn_id = ? WHERE order_id = ?
        """, (payment_method, txn_id, order_id))


def get_order(order_id):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_orders(user_id):
    with db_cursor() as cur:
        cur.execute("""
            SELECT o.*, c.title as course_title FROM orders o
            JOIN courses c ON c.course_id = o.course_id
            WHERE o.user_id = ? ORDER BY o.created_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]


def get_pending_orders():
    with db_cursor() as cur:
        cur.execute("""
            SELECT o.*, c.title as course_title, u.username, u.full_name FROM orders o
            JOIN courses c ON c.course_id = o.course_id
            JOIN users u ON u.user_id = o.user_id
            WHERE o.status = 'pending'
            ORDER BY o.created_at ASC
        """)
        return [dict(r) for r in cur.fetchall()]


def set_order_status(order_id, status, verified_by=None):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE orders SET status = ?, verified_at = ?, verified_by = ? WHERE order_id = ?
        """, (status, int(time.time()), verified_by, order_id))


def credit_referral_if_any(order_id):
    """Call after an order is verified. Credits the referrer, if the buyer was referred."""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT o.order_id, o.final_price, u.referred_by
            FROM orders o JOIN users u ON u.user_id = o.user_id
            WHERE o.order_id = ?
        """, (order_id,))
        row = cur.fetchone()
        if not row or not row["referred_by"]:
            return None

        amount = round(row["final_price"] * REFERRAL_COMMISSION_PERCENT / 100, 2)
        cur.execute("""
            INSERT INTO referral_earnings (referrer_id, referred_user_id, order_id, amount, created_at)
            VALUES (?, (SELECT user_id FROM orders WHERE order_id = ?), ?, ?, ?)
        """, (row["referred_by"], order_id, order_id, amount, int(time.time())))
        return {"referrer_id": row["referred_by"], "amount": amount}


# ---------- Withdrawals ----------

def request_withdrawal(user_id, amount, method, account_info):
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO withdrawals (user_id, amount, method, account_info, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, method, account_info, int(time.time())))
        # mark that amount as no longer "pending" (moves to awaiting payout)
        return cur.lastrowid

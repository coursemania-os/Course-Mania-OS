"""
Admin panel: /admin command + all admin callbacks.
Access restricted to user IDs listed in config.ADMIN_IDS.
"""
import time
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    ADMIN_IDS, CURRENCY,
    ADMIN_AWAITING_CATEGORY_NAME, ADMIN_AWAITING_COURSE_TITLE, ADMIN_AWAITING_COURSE_DESC,
    ADMIN_AWAITING_COURSE_PRICE, ADMIN_AWAITING_COURSE_CONTENT, ADMIN_AWAITING_NEW_PRICE,
    ADMIN_AWAITING_COUPON_CODE, ADMIN_AWAITING_COUPON_PERCENT, ADMIN_AWAITING_USER_SEARCH,
    ADMIN_AWAITING_BROADCAST_MSG,
)
from database import users as db_users
from database import courses as db_courses
from database import orders as db_orders
from database.db import db_cursor, log_event
from keyboards import admin_kb as kb


def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("⛔ Admins only.", show_alert=True)
            else:
                await update.message.reply_text("⛔ This command is for admins only.")
            return
        return await func(update, context)
    return wrapper


# ---------------- Entry point ----------------

@admin_only
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ *Admin Panel*", reply_markup=kb.admin_main_menu(), parse_mode="Markdown"
    )


@admin_only
async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛠️ *Admin Panel*", reply_markup=kb.admin_main_menu(), parse_mode="Markdown"
    )


# ---------------- Dashboard ----------------

@admin_only
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM users")
        total_users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) c FROM orders WHERE status='verified'")
        verified_orders = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) c FROM orders WHERE status='pending'")
        pending_orders = cur.fetchone()["c"]
        cur.execute("SELECT COALESCE(SUM(final_price),0) s FROM orders WHERE status='verified'")
        revenue = cur.fetchone()["s"]
        cur.execute("SELECT COUNT(*) c FROM courses WHERE is_active=1")
        active_courses = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) c FROM tickets WHERE status='open'")
        open_tickets = cur.fetchone()["c"]

    text = (
        "📊 *Dashboard*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📦 Active Courses: {active_courses}\n"
        f"✅ Verified Orders: {verified_orders}\n"
        f"🟡 Pending Orders: {pending_orders}\n"
        f"💰 Total Revenue: {revenue} {CURRENCY}\n"
        f"🎫 Open Tickets: {open_tickets}"
    )
    await query.edit_message_text(text, reply_markup=kb.admin_back(), parse_mode="Markdown")


# ---------------- Users ----------------

@admin_only
async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👥 *Users*\n\nSend a user ID, username, or name to search:",
        parse_mode="Markdown",
    )
    return ADMIN_AWAITING_USER_SEARCH


@admin_only
async def admin_search_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = db_users.search_users(update.message.text.strip())
    if not results:
        await update.message.reply_text("No users found.", reply_markup=kb.admin_back("admin_home"))
        return ConversationHandler.END

    for u in results[:10]:
        status = "🚫 Banned" if u["is_banned"] else "✅ Active"
        text = (
            f"👤 *{u['full_name']}* (@{u['username'] or '—'})\n"
            f"ID: `{u['user_id']}`\n"
            f"Role: {u['role']}\n"
            f"Status: {status}"
        )
        await update.message.reply_text(
            text, reply_markup=kb.admin_user_row_kb(u["user_id"], u["is_banned"]), parse_mode="Markdown"
        )
    return ConversationHandler.END


@admin_only
async def admin_toggle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    user = db_users.get_user(user_id)
    db_users.ban_user(user_id, banned=not user["is_banned"])
    log_event("INFO", "admin", f"{'Banned' if not user['is_banned'] else 'Unbanned'} user {user_id}")
    await query.edit_message_text(f"✅ Updated ban status for user {user_id}.")


@admin_only
async def admin_make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    db_users.update_user_field(user_id, "role", "admin")
    log_event("INFO", "admin", f"User {user_id} promoted to admin role")
    await query.edit_message_text(
        f"✅ User {user_id} marked as admin in DB.\n\n"
        f"⚠️ Also add `{user_id}` to ADMIN_IDS in your .env for full command access."
    )


# ---------------- Courses (Add/Edit/Delete) ----------------

@admin_only
async def admin_courses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📦 *Courses*", reply_markup=kb.admin_courses_kb(), parse_mode="Markdown"
    )


@admin_only
async def admin_list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    courses = db_courses.get_all_courses()
    if not courses:
        await query.edit_message_text("No courses yet.", reply_markup=kb.admin_back("admin_courses"))
        return
    await query.edit_message_text(f"📦 {len(courses)} course(s) found:", reply_markup=kb.admin_back("admin_courses"))
    for c in courses:
        status = "✅ Active" if c["is_active"] else "🗑️ Deleted"
        text = f"*{c['title']}*\nPrice: {c['price']} {CURRENCY}\nStatus: {status}"
        await context.bot.send_message(
            query.from_user.id, text, reply_markup=kb.admin_course_row_kb(c["course_id"]), parse_mode="Markdown"
        )


@admin_only
async def admin_add_course_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    categories = db_courses.get_categories()
    if not categories:
        cat_id = db_courses.add_category("General")
        context.user_data["new_course_category_id"] = cat_id
    else:
        context.user_data["new_course_category_id"] = categories[0]["category_id"]
    await query.edit_message_text("➕ *Add Course*\n\nSend the course title:", parse_mode="Markdown")
    return ADMIN_AWAITING_COURSE_TITLE


@admin_only
async def admin_add_course_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_course_title"] = update.message.text.strip()
    await update.message.reply_text("Send a short description:")
    return ADMIN_AWAITING_COURSE_DESC


@admin_only
async def admin_add_course_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_course_desc"] = update.message.text.strip()
    await update.message.reply_text(f"Send the price (number only, in {CURRENCY}):")
    return ADMIN_AWAITING_COURSE_PRICE


@admin_only
async def admin_add_course_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a valid number for the price.")
        return ADMIN_AWAITING_COURSE_PRICE
    context.user_data["new_course_price"] = price
    await update.message.reply_text("Send the content link (Drive/Group invite link students get after buying):")
    return ADMIN_AWAITING_COURSE_CONTENT


@admin_only
async def admin_add_course_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content_url = update.message.text.strip()
    d = context.user_data
    course_id = db_courses.add_course(
        d["new_course_category_id"], d["new_course_title"], d["new_course_desc"],
        d["new_course_price"], content_url,
    )
    log_event("INFO", "admin", f"Course #{course_id} created: {d['new_course_title']}")
    await update.message.reply_text(f"✅ Course *{d['new_course_title']}* created (#{course_id}).", parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


@admin_only
async def admin_delete_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[-1])
    db_courses.delete_course(course_id)
    log_event("INFO", "admin", f"Course #{course_id} deleted")
    await query.edit_message_text(f"🗑️ Course #{course_id} deleted (deactivated).")


@admin_only
async def admin_edit_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[-1])
    context.user_data["editing_course_id"] = course_id
    await query.edit_message_text(f"Send the new price for course #{course_id}:")
    return ADMIN_AWAITING_NEW_PRICE


@admin_only
async def admin_edit_price_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a valid number.")
        return ADMIN_AWAITING_NEW_PRICE
    course_id = context.user_data.get("editing_course_id")
    db_courses.update_course(course_id, price=price)
    log_event("INFO", "admin", f"Course #{course_id} price updated to {price}")
    await update.message.reply_text(f"✅ Price updated to {price} {CURRENCY}.")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------- Payments ----------------

@admin_only
async def admin_payments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pending = db_orders.get_pending_orders()
    if not pending:
        await query.edit_message_text("💰 No pending payments. All caught up!", reply_markup=kb.admin_back())
        return
    await query.edit_message_text(f"💰 {len(pending)} pending order(s):", reply_markup=kb.admin_back())
    for o in pending:
        text = (
            f"Order #{o['order_id']}\n"
            f"Buyer: {o['full_name']} (@{o['username'] or '—'})\n"
            f"Course: {o['course_title']}\n"
            f"Amount: {o['final_price']} {CURRENCY}\n"
            f"Method: {o['payment_method']}\n"
            f"Txn ID: `{o['payment_txn_id']}`"
        )
        await context.bot.send_message(
            query.from_user.id, text, reply_markup=kb.admin_payment_row_kb(o["order_id"]), parse_mode="Markdown"
        )


@admin_only
async def admin_verify_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[-1])
    order = db_orders.get_order(order_id)

    db_orders.set_order_status(order_id, "verified", verified_by=query.from_user.id)
    db_courses.enroll_user(order["user_id"], order["course_id"], order_id)
    credit = db_orders.credit_referral_if_any(order_id)
    log_event("INFO", "admin", f"Order #{order_id} verified by {query.from_user.id}")

    await query.edit_message_text(f"✅ Order #{order_id} verified. Student enrolled.")

    course = db_courses.get_course(order["course_id"])
    try:
        await context.bot.send_message(
            order["user_id"],
            f"✅ *Payment verified!*\n\nYou're now enrolled in *{course['title']}*.\n"
            f"🔗 Access it anytime via 🎓 My Courses.",
            parse_mode="Markdown",
        )
    except Exception:
        pass

    if credit:
        try:
            await context.bot.send_message(
                credit["referrer_id"],
                f"🌟 You earned {credit['amount']} {CURRENCY} referral commission!",
            )
        except Exception:
            pass


@admin_only
async def admin_reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[-1])
    order = db_orders.get_order(order_id)
    db_orders.set_order_status(order_id, "rejected", verified_by=query.from_user.id)
    log_event("INFO", "admin", f"Order #{order_id} rejected by {query.from_user.id}")
    await query.edit_message_text(f"❌ Order #{order_id} rejected.")
    try:
        await context.bot.send_message(
            order["user_id"],
            f"❌ Your order #{order_id} payment could not be verified. "
            f"Please contact support if you believe this is an error.",
        )
    except Exception:
        pass


# ---------------- Coupons ----------------

@admin_only
async def admin_coupons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎟️ *Coupons*", reply_markup=kb.admin_coupons_kb(), parse_mode="Markdown")


@admin_only
async def admin_add_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Send the coupon code (e.g. SAVE20):")
    return ADMIN_AWAITING_COUPON_CODE


@admin_only
async def admin_add_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_coupon_code"] = update.message.text.strip().upper()
    await update.message.reply_text("Send the discount percentage (number only, e.g. 20):")
    return ADMIN_AWAITING_COUPON_PERCENT


@admin_only
async def admin_add_coupon_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        percent = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a whole number, e.g. 20.")
        return ADMIN_AWAITING_COUPON_PERCENT
    code = context.user_data.get("new_coupon_code")
    db_orders.create_coupon(code, percent)
    log_event("INFO", "admin", f"Coupon {code} created ({percent}% off)")
    await update.message.reply_text(f"✅ Coupon *{code}* created — {percent}% off.", parse_mode="Markdown")
    context.user_data.clear()
    return ConversationHandler.END


@admin_only
async def admin_list_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    coupons = db_orders.get_all_coupons()
    if not coupons:
        await query.edit_message_text("No coupons yet.", reply_markup=kb.admin_back("admin_coupons"))
        return
    lines = ["🎟️ *Coupons*\n"]
    for c in coupons:
        status = "✅" if c["is_active"] else "🚫"
        lines.append(f"{status} `{c['code']}` — {c['discount_percent']}% off — used {c['times_used']} time(s)")
    await query.edit_message_text("\n".join(lines), reply_markup=kb.admin_back("admin_coupons"), parse_mode="Markdown")


# ---------------- Broadcast ----------------

@admin_only
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 *Broadcast*", reply_markup=kb.admin_broadcast_kb(), parse_mode="Markdown"
    )


@admin_only
async def admin_broadcast_all_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["broadcast_target"] = "all"
    await query.edit_message_text("📢 Send the message you want to broadcast to *all users*:", parse_mode="Markdown")
    return ADMIN_AWAITING_BROADCAST_MSG


@admin_only
async def admin_broadcast_enrolled_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["broadcast_target"] = "enrolled"
    await query.edit_message_text("📢 Send the message for *enrolled students only*:", parse_mode="Markdown")
    return ADMIN_AWAITING_BROADCAST_MSG


@admin_only
async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    target = context.user_data.get("broadcast_target", "all")

    if target == "enrolled":
        with db_cursor() as cur:
            cur.execute("SELECT DISTINCT user_id FROM enrollments")
            user_ids = [r["user_id"] for r in cur.fetchall()]
    else:
        user_ids = db_users.get_all_user_ids()

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(uid, f"📢 {message}")
            sent += 1
        except Exception:
            failed += 1

    log_event("INFO", "admin", f"Broadcast sent to {sent} users ({failed} failed)")
    await update.message.reply_text(f"✅ Broadcast complete. Sent: {sent}, Failed: {failed}.")
    context.user_data.clear()
    return ConversationHandler.END


# ---------------- Logs ----------------

@admin_only
async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 20")
        logs = [dict(r) for r in cur.fetchall()]
    if not logs:
        await query.edit_message_text("No logs yet.", reply_markup=kb.admin_back())
        return
    lines = ["📋 *Recent Activity Logs*\n"]
    for l in logs:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(l["created_at"]))
        icon = "❌" if l["level"] == "ERROR" else "ℹ️"
        lines.append(f"{icon} `{ts}` — {l['message']}")
    await query.edit_message_text("\n".join(lines), reply_markup=kb.admin_back(), parse_mode="Markdown")

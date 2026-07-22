"""
All student-facing handlers: /start, home menu, courses, my courses,
orders, profile, affiliate, support, settings, about.
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    ADMIN_IDS, CURRENCY,
    AWAITING_TXN_ID, AWAITING_COUPON_CODE,
    AWAITING_TICKET_SUBJECT, AWAITING_TICKET_MESSAGE,
    AWAITING_WITHDRAW_METHOD, AWAITING_WITHDRAW_ACCOUNT,
)
from database import users as db_users
from database import courses as db_courses
from database import orders as db_orders
from database.db import db_cursor
from keyboards import student_kb as kb


# ---------------- /start ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    referred_by_code = None
    if context.args:
        referred_by_code = context.args[0]

    user = db_users.get_or_create_user(
        tg_user.id, tg_user.username, tg_user.full_name, referred_by_code
    )

    if user["is_banned"]:
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    text = (
        f"👋 Welcome, {tg_user.first_name}!\n\n"
        "🏠 *Home* — browse and manage your courses here.\n"
        "Use the menu below to get started."
    )
    await update.message.reply_text(text, reply_markup=kb.main_menu(), parse_mode="Markdown")


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏠 *Home*\n\nWhat would you like to do?",
        reply_markup=kb.main_menu(),
        parse_mode="Markdown",
    )


# ---------------- Courses browsing ----------------

async def show_courses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    categories = db_courses.get_categories()
    if not categories:
        await query.edit_message_text(
            "📚 No categories yet. Please check back soon!",
            reply_markup=kb.back_button(),
        )
        return
    await query.edit_message_text(
        "📚 *Browse Courses*\n\nChoose a category:",
        reply_markup=kb.categories_kb(categories),
        parse_mode="Markdown",
    )


async def show_category_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category_id = int(query.data.split("_")[1])
    courses = db_courses.get_courses_by_category(category_id)
    if not courses:
        await query.edit_message_text(
            "No courses in this category yet.",
            reply_markup=kb.back_button("menu_courses"),
        )
        return
    await query.edit_message_text(
        f"📚 *Courses* ({CURRENCY} price shown)\n\nTap a course to view details:",
        reply_markup=kb.courses_kb(courses, category_id),
        parse_mode="Markdown",
    )


async def show_course_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[1])
    course = db_courses.get_course(course_id)
    if not course:
        await query.edit_message_text("Course not found.", reply_markup=kb.back_button("menu_courses"))
        return

    already = db_courses.is_enrolled(query.from_user.id, course_id)
    status_line = "\n\n✅ *You are already enrolled.*" if already else ""
    text = (
        f"🎓 *{course['title']}*\n\n"
        f"{course['description'] or 'No description provided.'}\n\n"
        f"💵 Price: *{course['price']} {CURRENCY}*"
        f"{status_line}"
    )
    await query.edit_message_text(
        text, reply_markup=kb.course_detail_kb(course_id, already), parse_mode="Markdown"
    )


# ---------------- Buy flow (checkout -> coupon -> payment method -> txn id -> pending order) ----------------

async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[1])
    course = db_courses.get_course(course_id)
    context.user_data["checkout_course_id"] = course_id
    context.user_data["checkout_price"] = course["price"]
    context.user_data.pop("checkout_coupon", None)

    text = (
        f"🛒 *Checkout*\n\n"
        f"Course: {course['title']}\n"
        f"Price: {course['price']} {CURRENCY}\n\n"
        f"Apply a coupon code, or confirm to proceed to payment."
    )
    await query.edit_message_text(text, reply_markup=kb.checkout_kb(course_id), parse_mode="Markdown")


async def ask_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[2])
    context.user_data["checkout_course_id"] = course_id
    await query.edit_message_text("🎟️ Please type your coupon code:")
    return AWAITING_COUPON_CODE


async def receive_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    coupon = db_orders.get_coupon(code)
    course_id = context.user_data.get("checkout_course_id")
    course = db_courses.get_course(course_id)

    if not db_orders.is_coupon_valid(coupon):
        await update.message.reply_text(
            "❌ Invalid or expired coupon. Try again or go back.",
            reply_markup=kb.checkout_kb(course_id),
        )
        return ConversationHandler.END

    context.user_data["checkout_coupon"] = code
    discount = coupon["discount_percent"]
    final_price = round(course["price"] * (1 - discount / 100), 2)
    context.user_data["checkout_price"] = final_price

    text = (
        f"✅ Coupon *{code}* applied! ({discount}% off)\n\n"
        f"Original: {course['price']} {CURRENCY}\n"
        f"Final price: *{final_price} {CURRENCY}*\n\n"
        f"Tap Confirm & Pay to continue."
    )
    await update.message.reply_text(text, reply_markup=kb.checkout_kb(course_id), parse_mode="Markdown")
    return ConversationHandler.END


async def confirm_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    course_id = int(query.data.split("_")[2])
    await query.edit_message_text(
        "💳 *Select your payment method:*\n\n"
        "After choosing, you'll get payment instructions and be asked to submit "
        "your transaction ID. An admin will manually verify it.",
        reply_markup=kb.payment_methods_kb(course_id),
        parse_mode="Markdown",
    )


async def choose_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, course_id, method = query.data.split("_", 2)
    course_id = int(course_id)
    context.user_data["checkout_course_id"] = course_id
    context.user_data["checkout_method"] = method

    # NOTE: replace these with your real payment numbers/details
    instructions = {
        "bKash": "Send payment to bKash Personal: 01XXXXXXXXX (Send Money)",
        "Nagad": "Send payment to Nagad Personal: 01XXXXXXXXX (Send Money)",
        "Rocket": "Send payment to Rocket: 01XXXXXXXXX-X",
        "Bank Transfer": "Bank: Example Bank, A/C Name: Your Company, A/C No: 0000000000",
    }

    price = context.user_data.get("checkout_price")
    text = (
        f"💳 *{method}*\n\n"
        f"{instructions.get(method, 'Contact support for payment details.')}\n\n"
        f"Amount to send: *{price} {CURRENCY}*\n\n"
        f"After sending, reply with your *Transaction ID*."
    )
    await query.edit_message_text(text, parse_mode="Markdown")
    return AWAITING_TXN_ID


async def receive_txn_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txn_id = update.message.text.strip()
    course_id = context.user_data.get("checkout_course_id")
    method = context.user_data.get("checkout_method")
    price = context.user_data.get("checkout_price")
    coupon = context.user_data.get("checkout_coupon")
    course = db_courses.get_course(course_id)
    user_id = update.effective_user.id

    order_id = db_orders.create_order(
        user_id=user_id,
        course_id=course_id,
        original_price=course["price"],
        final_price=price,
        coupon_code=coupon,
    )
    db_orders.attach_payment_info(order_id, method, txn_id)
    if coupon:
        db_orders.use_coupon(coupon)

    await update.message.reply_text(
        f"✅ *Order #{order_id} submitted!*\n\n"
        f"Status: 🟡 Pending admin verification.\n"
        f"You'll be notified once it's verified — usually within a few hours.\n\n"
        f"Check status anytime under 🛒 Orders.",
        parse_mode="Markdown",
    )

    # Notify all admins
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💰 *New order needs verification*\n\n"
                f"Order #{order_id}\n"
                f"Course: {course['title']}\n"
                f"Amount: {price} {CURRENCY}\n"
                f"Method: {method}\n"
                f"Txn ID: `{txn_id}`\n"
                f"Buyer: {update.effective_user.full_name} (@{update.effective_user.username})\n\n"
                f"Use /admin → 💰 Payments to verify.",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END


# ---------------- My Courses ----------------

async def show_my_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    courses = db_courses.get_user_courses(query.from_user.id)
    if not courses:
        await query.edit_message_text(
            "🎓 You haven't enrolled in any course yet.\n\nBrowse 📚 Courses to get started!",
            reply_markup=kb.back_button(),
        )
        return
    lines = ["🎓 *My Courses*\n"]
    for c in courses:
        link = c["content_url"] or "(link will be shared soon)"
        lines.append(f"• *{c['title']}*\n  🔗 {link}")
    await query.edit_message_text("\n".join(lines), reply_markup=kb.back_button(), parse_mode="Markdown")


# ---------------- Orders ----------------

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    orders = db_orders.get_user_orders(query.from_user.id)
    if not orders:
        await query.edit_message_text("🛒 You have no orders yet.", reply_markup=kb.back_button())
        return
    icons = {"pending": "🟡", "verified": "✅", "rejected": "❌"}
    lines = ["🛒 *Order History*\n"]
    for o in orders:
        icon = icons.get(o["status"], "❔")
        lines.append(
            f"{icon} Order #{o['order_id']} — {o['course_title']}\n"
            f"   {o['final_price']} {CURRENCY} • {o['status'].upper()}"
        )
    await query.edit_message_text("\n\n".join(lines), reply_markup=kb.back_button(), parse_mode="Markdown")


# ---------------- Profile ----------------

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = db_users.get_user(query.from_user.id)
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    text = (
        f"👤 *Profile*\n\n"
        f"Name: {user['full_name']}\n"
        f"Username: @{user['username'] or '—'}\n"
        f"Phone: {user['phone'] or 'Not set'}\n\n"
        f"🔗 *Your Referral Link:*\n{ref_link}"
    )
    await query.edit_message_text(text, reply_markup=kb.back_button(), parse_mode="Markdown")


# ---------------- Affiliate ----------------

async def show_affiliate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = db_users.get_referral_stats(query.from_user.id)
    text = (
        f"🌟 *Affiliate Dashboard*\n\n"
        f"👥 Total Referrals: {stats['total_referrals']}\n"
        f"💰 Pending Earnings: {stats['pending_earnings']} {CURRENCY}\n"
        f"✅ Withdrawn: {stats['withdrawn_earnings']} {CURRENCY}\n\n"
        f"Share your referral link (Profile menu) to earn commission on every "
        f"verified purchase made by people you refer!"
    )
    await query.edit_message_text(text, reply_markup=kb.affiliate_kb(), parse_mode="Markdown")


async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = db_users.get_referral_stats(query.from_user.id)
    if stats["pending_earnings"] <= 0:
        await query.edit_message_text(
            "You have no pending earnings to withdraw.", reply_markup=kb.back_button("menu_affiliate")
        )
        return ConversationHandler.END
    context.user_data["withdraw_amount"] = stats["pending_earnings"]
    await query.edit_message_text(
        f"💸 Withdrawing {stats['pending_earnings']} {CURRENCY}.\n\n"
        f"Which payment method? (e.g. bKash, Nagad, Bank)"
    )
    return AWAITING_WITHDRAW_METHOD


async def receive_withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["withdraw_method"] = update.message.text.strip()
    await update.message.reply_text("Please provide your account number / details:")
    return AWAITING_WITHDRAW_ACCOUNT


async def receive_withdraw_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account_info = update.message.text.strip()
    amount = context.user_data.get("withdraw_amount")
    method = context.user_data.get("withdraw_method")
    user_id = update.effective_user.id

    db_orders.request_withdrawal(user_id, amount, method, account_info)
    # zero out pending by marking those earnings withdrawn once admin pays —
    # for simplicity here we mark request as pending; admin settles manually.
    await update.message.reply_text(
        f"✅ Withdrawal request submitted for {amount} {CURRENCY} via {method}.\n"
        f"An admin will process this manually."
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💸 *Withdrawal request*\nUser: {user_id}\nAmount: {amount}\n"
                f"Method: {method}\nAccount: {account_info}",
                parse_mode="Markdown",
            )
        except Exception:
            pass
    context.user_data.clear()
    return ConversationHandler.END


# ---------------- Support ----------------

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🆘 *Support*", reply_markup=kb.support_kb(), parse_mode="Markdown")


async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "❓ *FAQ*\n\n"
        "*How do I buy a course?*\nGo to 📚 Courses → pick a course → Buy Now.\n\n"
        "*How long does payment verification take?*\nUsually within a few hours.\n\n"
        "*How does the referral program work?*\nShare your link — you earn a commission "
        "when someone you refer buys a course."
    )
    await query.edit_message_text(text, reply_markup=kb.back_button("menu_support"), parse_mode="Markdown")


async def start_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🎫 What's the subject of your issue?")
    return AWAITING_TICKET_SUBJECT


async def receive_ticket_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ticket_subject"] = update.message.text.strip()
    await update.message.reply_text("Please describe your issue in detail:")
    return AWAITING_TICKET_MESSAGE


async def receive_ticket_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import time
    subject = context.user_data.get("ticket_subject")
    message = update.message.text.strip()
    user_id = update.effective_user.id

    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO tickets (user_id, subject, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, subject, message, int(time.time()), int(time.time())))
        ticket_id = cur.lastrowid

    await update.message.reply_text(f"✅ Ticket #{ticket_id} opened. We'll get back to you soon!")
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🎫 *New support ticket #{ticket_id}*\nFrom: {user_id}\n"
                f"Subject: {subject}\nMessage: {message}",
                parse_mode="Markdown",
            )
        except Exception:
            pass
    context.user_data.clear()
    return ConversationHandler.END


async def show_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (query.from_user.id,))
        tickets = [dict(r) for r in cur.fetchall()]
    if not tickets:
        await query.edit_message_text("You have no tickets.", reply_markup=kb.back_button("menu_support"))
        return
    icons = {"open": "🟡", "answered": "✅", "closed": "⚪"}
    lines = ["📋 *My Tickets*\n"]
    for t in tickets:
        lines.append(f"{icons.get(t['status'], '❔')} #{t['ticket_id']} — {t['subject']} ({t['status']})")
        if t["admin_reply"]:
            lines.append(f"   💬 Reply: {t['admin_reply']}")
    await query.edit_message_text("\n".join(lines), reply_markup=kb.back_button("menu_support"), parse_mode="Markdown")


# ---------------- Settings ----------------

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = db_users.get_user(query.from_user.id)
    await query.edit_message_text(
        "⚙️ *Settings*", reply_markup=kb.settings_kb(user["notifications_on"]), parse_mode="Markdown"
    )


async def show_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🌐 Choose your language:", reply_markup=kb.language_kb())


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    db_users.update_user_field(query.from_user.id, "language", lang)
    await query.edit_message_text(f"✅ Language set to {'English' if lang == 'en' else 'বাংলা'}.")


async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = db_users.get_user(query.from_user.id)
    new_val = 0 if user["notifications_on"] else 1
    db_users.update_user_field(query.from_user.id, "notifications_on", new_val)
    user["notifications_on"] = new_val
    await query.edit_message_text(
        "⚙️ *Settings*", reply_markup=kb.settings_kb(new_val), parse_mode="Markdown"
    )


# ---------------- About ----------------

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "ℹ️ *About Us*\n\n"
        "We provide high-quality online courses to help you learn new skills.\n\n"
        "📞 Contact: @your_support_username\n"
        "🌐 Website: https://example.com"
    )
    await query.edit_message_text(text, reply_markup=kb.back_button(), parse_mode="Markdown")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

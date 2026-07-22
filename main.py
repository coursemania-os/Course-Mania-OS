"""
Entry point for the Course-Selling Telegram Bot.

Run with:  python main.py
Make sure you've created a .env file (copy .env.example) with your BOT_TOKEN
and ADMIN_IDS filled in.
"""
import logging

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters,
)

from config import (
    BOT_TOKEN,
    AWAITING_TXN_ID, AWAITING_COUPON_CODE, AWAITING_TICKET_SUBJECT,
    AWAITING_TICKET_MESSAGE, AWAITING_WITHDRAW_METHOD, AWAITING_WITHDRAW_ACCOUNT,
    ADMIN_AWAITING_CATEGORY_NAME, ADMIN_AWAITING_COURSE_TITLE, ADMIN_AWAITING_COURSE_DESC,
    ADMIN_AWAITING_COURSE_PRICE, ADMIN_AWAITING_COURSE_CONTENT, ADMIN_AWAITING_NEW_PRICE,
    ADMIN_AWAITING_COUPON_CODE, ADMIN_AWAITING_COUPON_PERCENT, ADMIN_AWAITING_USER_SEARCH,
    ADMIN_AWAITING_BROADCAST_MSG,
)
from database.db import init_db
from handlers import student as stu
from handlers import admin as adm

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # ---------------- /start ----------------
    app.add_handler(CommandHandler("start", stu.start))
    app.add_handler(CallbackQueryHandler(stu.show_home, pattern="^menu_home$"))

    # ---------------- Courses browsing ----------------
    app.add_handler(CallbackQueryHandler(stu.show_courses_menu, pattern="^menu_courses$"))
    app.add_handler(CallbackQueryHandler(stu.show_category_courses, pattern="^cat_\\d+$"))
    app.add_handler(CallbackQueryHandler(stu.show_course_detail, pattern="^course_\\d+$"))

    # ---------------- Checkout conversation (coupon -> payment method -> txn id) ----------------
    checkout_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(stu.start_checkout, pattern="^buy_\\d+$"),
        ],
        states={
            AWAITING_COUPON_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_coupon_code),
            ],
            AWAITING_TXN_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_txn_id),
            ],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(checkout_conv)
    app.add_handler(CallbackQueryHandler(stu.ask_coupon_code, pattern="^apply_coupon_\\d+$"))
    app.add_handler(CallbackQueryHandler(stu.confirm_pay, pattern="^confirm_pay_\\d+$"))

    payment_method_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(stu.choose_payment_method, pattern="^paymethod_\\d+_.+$"),
        ],
        states={
            AWAITING_TXN_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_txn_id),
            ],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(payment_method_conv)

    # ---------------- My Courses / Orders / Profile ----------------
    app.add_handler(CallbackQueryHandler(stu.show_my_courses, pattern="^menu_my_courses$"))
    app.add_handler(CallbackQueryHandler(stu.show_orders, pattern="^menu_orders$"))
    app.add_handler(CallbackQueryHandler(stu.show_profile, pattern="^menu_profile$"))

    # ---------------- Affiliate ----------------
    app.add_handler(CallbackQueryHandler(stu.show_affiliate, pattern="^menu_affiliate$"))
    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(stu.start_withdraw, pattern="^affiliate_withdraw$")],
        states={
            AWAITING_WITHDRAW_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_withdraw_method),
            ],
            AWAITING_WITHDRAW_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_withdraw_account),
            ],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(withdraw_conv)

    # ---------------- Support ----------------
    app.add_handler(CallbackQueryHandler(stu.show_support, pattern="^menu_support$"))
    app.add_handler(CallbackQueryHandler(stu.show_faq, pattern="^support_faq$"))
    app.add_handler(CallbackQueryHandler(stu.show_my_tickets, pattern="^support_my_tickets$"))
    ticket_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(stu.start_ticket, pattern="^support_open_ticket$")],
        states={
            AWAITING_TICKET_SUBJECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_ticket_subject),
            ],
            AWAITING_TICKET_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stu.receive_ticket_message),
            ],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(ticket_conv)

    # ---------------- Settings ----------------
    app.add_handler(CallbackQueryHandler(stu.show_settings, pattern="^menu_settings$"))
    app.add_handler(CallbackQueryHandler(stu.show_language, pattern="^settings_language$"))
    app.add_handler(CallbackQueryHandler(stu.set_language, pattern="^lang_(en|bn)$"))
    app.add_handler(CallbackQueryHandler(stu.toggle_notifications, pattern="^settings_toggle_notif$"))

    # ---------------- About ----------------
    app.add_handler(CallbackQueryHandler(stu.show_about, pattern="^menu_about$"))

    # ================== ADMIN ==================
    app.add_handler(CommandHandler("admin", adm.admin_start))
    app.add_handler(CallbackQueryHandler(adm.admin_home, pattern="^admin_home$"))
    app.add_handler(CallbackQueryHandler(adm.admin_dashboard, pattern="^admin_dashboard$"))

    # Users
    users_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm.admin_users_menu, pattern="^admin_users$")],
        states={
            ADMIN_AWAITING_USER_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_search_users),
            ],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(users_conv)
    app.add_handler(CallbackQueryHandler(adm.admin_toggle_ban, pattern="^admin_toggleban_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm.admin_make_admin, pattern="^admin_makeadmin_\\d+$"))

    # Courses
    app.add_handler(CallbackQueryHandler(adm.admin_courses_menu, pattern="^admin_courses$"))
    app.add_handler(CallbackQueryHandler(adm.admin_list_courses, pattern="^admin_list_courses$"))
    app.add_handler(CallbackQueryHandler(adm.admin_delete_course, pattern="^admin_delete_course_\\d+$"))

    add_course_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm.admin_add_course_start, pattern="^admin_add_course$")],
        states={
            ADMIN_AWAITING_COURSE_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_course_title)],
            ADMIN_AWAITING_COURSE_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_course_desc)],
            ADMIN_AWAITING_COURSE_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_course_price)],
            ADMIN_AWAITING_COURSE_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_course_content)],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(add_course_conv)

    edit_price_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm.admin_edit_price_start, pattern="^admin_edit_price_\\d+$")],
        states={
            ADMIN_AWAITING_NEW_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_edit_price_save)],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(edit_price_conv)

    # Payments
    app.add_handler(CallbackQueryHandler(adm.admin_payments_menu, pattern="^admin_payments$"))
    app.add_handler(CallbackQueryHandler(adm.admin_verify_order, pattern="^admin_verify_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm.admin_reject_order, pattern="^admin_reject_\\d+$"))

    # Coupons
    app.add_handler(CallbackQueryHandler(adm.admin_coupons_menu, pattern="^admin_coupons$"))
    app.add_handler(CallbackQueryHandler(adm.admin_list_coupons, pattern="^admin_list_coupons$"))
    add_coupon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm.admin_add_coupon_start, pattern="^admin_add_coupon$")],
        states={
            ADMIN_AWAITING_COUPON_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_coupon_code)],
            ADMIN_AWAITING_COUPON_PERCENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_add_coupon_percent)],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(add_coupon_conv)

    # Broadcast
    app.add_handler(CallbackQueryHandler(adm.admin_broadcast_menu, pattern="^admin_broadcast$"))
    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(adm.admin_broadcast_all_start, pattern="^admin_broadcast_all$"),
            CallbackQueryHandler(adm.admin_broadcast_enrolled_start, pattern="^admin_broadcast_enrolled$"),
        ],
        states={
            ADMIN_AWAITING_BROADCAST_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, adm.admin_broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", stu.cancel_conversation)],
        per_message=False,
    )
    app.add_handler(broadcast_conv)

    # Logs
    app.add_handler(CallbackQueryHandler(adm.admin_logs, pattern="^admin_logs$"))

    return app


def main():
    init_db()
    app = build_application()
    logger.info("Bot starting (polling mode)...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()

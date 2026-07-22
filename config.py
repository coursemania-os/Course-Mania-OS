import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CURRENCY = os.getenv("CURRENCY", "BDT")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
if not ADMIN_IDS:
    print("⚠️  WARNING: No ADMIN_IDS set — nobody will be able to access /admin.")

# Conversation states (used with ConversationHandler)
(
    AWAITING_TXN_ID,
    AWAITING_COUPON_CODE,
    AWAITING_TICKET_SUBJECT,
    AWAITING_TICKET_MESSAGE,
    AWAITING_PHONE,
    ADMIN_AWAITING_CATEGORY_NAME,
    ADMIN_AWAITING_COURSE_TITLE,
    ADMIN_AWAITING_COURSE_DESC,
    ADMIN_AWAITING_COURSE_PRICE,
    ADMIN_AWAITING_COURSE_CONTENT,
    ADMIN_AWAITING_NEW_PRICE,
    ADMIN_AWAITING_COUPON_CODE,
    ADMIN_AWAITING_COUPON_PERCENT,
    ADMIN_AWAITING_USER_SEARCH,
    ADMIN_AWAITING_BROADCAST_MSG,
    ADMIN_AWAITING_TICKET_REPLY,
    AWAITING_WITHDRAW_METHOD,
    AWAITING_WITHDRAW_ACCOUNT,
) = range(18)

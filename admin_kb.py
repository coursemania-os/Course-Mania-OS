from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_menu():
    rows = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
         InlineKeyboardButton("📦 Courses", callback_data="admin_courses")],
        [InlineKeyboardButton("💰 Payments", callback_data="admin_payments"),
         InlineKeyboardButton("🎟️ Coupons", callback_data="admin_coupons")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📋 Logs", callback_data="admin_logs")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_back(target="admin_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def admin_courses_kb():
    rows = [
        [InlineKeyboardButton("➕ Add Course", callback_data="admin_add_course")],
        [InlineKeyboardButton("📋 List / Edit / Delete", callback_data="admin_list_courses")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_home")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_course_row_kb(course_id):
    rows = [
        [InlineKeyboardButton("✏️ Edit Price", callback_data=f"admin_edit_price_{course_id}"),
         InlineKeyboardButton("🗑️ Delete", callback_data=f"admin_delete_course_{course_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_list_courses")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_payment_row_kb(order_id):
    rows = [
        [InlineKeyboardButton("✅ Verify", callback_data=f"admin_verify_{order_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{order_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_user_row_kb(user_id, is_banned):
    ban_label = "✅ Unban" if is_banned else "🚫 Ban"
    rows = [
        [InlineKeyboardButton(ban_label, callback_data=f"admin_toggleban_{user_id}"),
         InlineKeyboardButton("🔧 Make Admin", callback_data=f"admin_makeadmin_{user_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_users")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_coupons_kb():
    rows = [
        [InlineKeyboardButton("➕ Create Coupon", callback_data="admin_add_coupon")],
        [InlineKeyboardButton("📋 List / Deactivate", callback_data="admin_list_coupons")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_home")],
    ]
    return InlineKeyboardMarkup(rows)


def admin_broadcast_kb():
    rows = [
        [InlineKeyboardButton("📢 To All Users", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🎯 To Enrolled Only", callback_data="admin_broadcast_enrolled")],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_home")],
    ]
    return InlineKeyboardMarkup(rows)

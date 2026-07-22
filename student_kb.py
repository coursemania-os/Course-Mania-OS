from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    buttons = [
        [InlineKeyboardButton("📚 Courses", callback_data="menu_courses"),
         InlineKeyboardButton("🎓 My Courses", callback_data="menu_my_courses")],
        [InlineKeyboardButton("🛒 Orders", callback_data="menu_orders"),
         InlineKeyboardButton("👤 Profile", callback_data="menu_profile")],
        [InlineKeyboardButton("🌟 Affiliate", callback_data="menu_affiliate"),
         InlineKeyboardButton("🆘 Support", callback_data="menu_support")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_button(target="menu_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def categories_kb(categories):
    rows = [[InlineKeyboardButton(c["name"], callback_data=f"cat_{c['category_id']}")]
            for c in categories]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_home")])
    return InlineKeyboardMarkup(rows)


def courses_kb(courses, category_id):
    rows = [[InlineKeyboardButton(f"{c['title']} — {c['price']}", callback_data=f"course_{c['course_id']}")]
            for c in courses]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_courses")])
    return InlineKeyboardMarkup(rows)


def course_detail_kb(course_id, already_enrolled=False):
    rows = []
    if not already_enrolled:
        rows.append([InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{course_id}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_courses")])
    return InlineKeyboardMarkup(rows)


def checkout_kb(course_id):
    rows = [
        [InlineKeyboardButton("🎟️ Apply Coupon", callback_data=f"apply_coupon_{course_id}")],
        [InlineKeyboardButton("✅ Confirm & Pay", callback_data=f"confirm_pay_{course_id}")],
        [InlineKeyboardButton("⬅️ Cancel", callback_data=f"course_{course_id}")],
    ]
    return InlineKeyboardMarkup(rows)


def payment_methods_kb(course_id):
    methods = ["bKash", "Nagad", "Rocket", "Bank Transfer"]
    rows = [[InlineKeyboardButton(m, callback_data=f"paymethod_{course_id}_{m}")] for m in methods]
    rows.append([InlineKeyboardButton("⬅️ Cancel", callback_data=f"course_{course_id}")])
    return InlineKeyboardMarkup(rows)


def settings_kb(notifications_on):
    notif_label = "🔔 Notifications: ON" if notifications_on else "🔕 Notifications: OFF"
    rows = [
        [InlineKeyboardButton("🌐 Language", callback_data="settings_language")],
        [InlineKeyboardButton(notif_label, callback_data="settings_toggle_notif")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_home")],
    ]
    return InlineKeyboardMarkup(rows)


def language_kb():
    rows = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_bn")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_settings")],
    ]
    return InlineKeyboardMarkup(rows)


def support_kb():
    rows = [
        [InlineKeyboardButton("❓ FAQ", callback_data="support_faq")],
        [InlineKeyboardButton("🎫 Open Ticket", callback_data="support_open_ticket")],
        [InlineKeyboardButton("📋 My Tickets", callback_data="support_my_tickets")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_home")],
    ]
    return InlineKeyboardMarkup(rows)


def affiliate_kb():
    rows = [
        [InlineKeyboardButton("💸 Withdraw Earnings", callback_data="affiliate_withdraw")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_home")],
    ]
    return InlineKeyboardMarkup(rows)

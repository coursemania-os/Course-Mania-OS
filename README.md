# Course-Selling Telegram Bot

A complete Telegram bot for selling online courses, with student menus,
manual payment verification, coupons, and an affiliate/referral system —
plus a full admin panel.

## Features

**Student side**
- 🏠 Home menu
- 📚 Browse courses by category → course detail → buy
- 🛒 Checkout: apply coupon → choose payment method (bKash / Nagad / Rocket / Bank) → submit transaction ID
- 🎓 My Courses (see enrolled courses + access links)
- 🛒 Order history with status (pending / verified / rejected)
- 👤 Profile with personal referral link
- 🌟 Affiliate dashboard: referral count, earnings, withdraw request
- 🆘 Support: FAQ, open ticket, view ticket status
- ⚙️ Settings: language, notification toggle
- ℹ️ About

**Admin side** (`/admin`, restricted to `ADMIN_IDS`)
- 📊 Dashboard (users, revenue, orders, tickets at a glance)
- 👥 Users: search, ban/unban, promote to admin
- 📦 Courses: add / edit price / delete
- 💰 Payments: see pending orders with submitted transaction ID → verify or reject
- 🎟️ Coupons: create % discount codes, list/deactivate
- 📢 Broadcast: message all users or enrolled-only
- 📋 Logs: recent admin activity

## How payment verification works

Since you chose **manual verification**:
1. Student picks a course, applies a coupon (optional), picks a payment method
2. Student sends money manually (bKash/Nagad/etc.) using the number you configure
3. Student replies with their transaction ID inside the bot
4. Order goes to `pending` status; all admins get notified instantly
5. Admin opens 💰 Payments in `/admin`, checks the transaction ID against their
   actual bKash/Nagad account, then taps ✅ Verify or ❌ Reject
6. On verify: student is auto-enrolled, gets the course link, and the referrer
   (if any) is automatically credited a commission

**You still need to physically check the transaction ID against your real
payment account** — this bot doesn't call any payment gateway API. That's it
being "manual."

## Setup

1. **Get a bot token**: message [@BotFather](https://t.me/BotFather) on Telegram,
   run `/newbot`, follow the prompts, copy the token it gives you.

2. **Get your Telegram user ID**: message [@userinfobot](https://t.me/userinfobot),
   it replies with your numeric ID.

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   BOT_TOKEN=<paste your bot token>
   ADMIN_IDS=<your numeric user id>
   CURRENCY=BDT
   ```

5. **Run the bot**:
   ```bash
   python main.py
   ```

That's it — the SQLite database (`database/bot.db`) is created automatically
on first run. No external database server needed.

## Setting up real payment numbers

Edit `handlers/student.py`, function `choose_payment_method`, and replace the
placeholder numbers in the `instructions` dict with your real bKash/Nagad/Rocket/
bank details.

## Adding your first course

1. Message your bot with `/admin`
2. 📦 Courses → ➕ Add Course
3. Follow the prompts (title, description, price, content link)

The "content link" is whatever you want to send the student after they're
verified — e.g. a Google Drive folder link, a private Telegram group invite
link, or a course platform login link.

## Project structure

```
course-bot/
├── main.py                  # Entry point — wires up all handlers
├── config.py                 # Env vars + conversation state constants
├── requirements.txt
├── .env.example
├── database/
│   ├── db.py                 # SQLite connection + schema (init_db)
│   ├── users.py               # User queries (referral, ban, search...)
│   ├── courses.py             # Course/category/enrollment queries
│   └── orders.py              # Orders, coupons, referral earnings
├── keyboards/
│   ├── student_kb.py           # Inline keyboards for student menus
│   └── admin_kb.py             # Inline keyboards for admin panel
└── handlers/
    ├── student.py              # All student-facing logic
    └── admin.py                 # All admin-facing logic (access-controlled)
```

## Extending this

- **Multi-language**: `language` field is already stored per-user; wire up a
  translation dict and read `user['language']` in each handler to fully
  localize (currently only the language *setting* is functional).
- **Auto withdrawals**: currently withdrawal requests just notify admins —
  hook up a payment API here if you want auto-payout later.
- **File-based course content**: if courses should deliver actual video files
  instead of links, store `file_id`s from Telegram uploads instead of URLs.
- **Deployment**: this uses polling (`run_polling`), which is the simplest way
  to run 24/7 on a VPS (e.g. with `systemd`, `screen`, or `pm2`). For serverless
  hosting, swap to a webhook setup instead.

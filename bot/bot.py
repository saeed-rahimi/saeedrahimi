import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import json

# تنظیمات
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_URL = "http://127.0.0.1:8000/api"

# لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توابع کمکی API
def api_request(method, endpoint, data=None):
    """ارسال درخواست به API"""
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

def get_user_by_telegram_id(telegram_id):
    """دریافت اطلاعات کاربر از API"""
    return api_request("GET", f"/users/{telegram_id}")

def register_user(telegram_id, username=None, full_name=None):
    """ثبت‌نام کاربر"""
    return api_request("POST", "/users/register", {
        "telegram_id": telegram_id,
        "username": username,
        "full_name": full_name
    })

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    telegram_id = user.id
    
    # ثبت‌نام کاربر
    register_user(telegram_id, user.username, user.full_name)
    
    welcome_text = """
👋 به ربات Server24 خوش آمدید!

از این بخش می‌توانید:
• اشتراک بخرید
• کیف پول‌تان را شارژ کنید
• وضعیت سرویس‌تان را ببینید
• با پشتیبانی در ارتباط باشید

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    
    keyboard = [
        [InlineKeyboardButton("📌 خرید حجم", callback_data="buy")],
        [InlineKeyboardButton("🧾 وضعیت سرویس", callback_data="status")],
        [InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("💳 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("🎫 پشتیبانی", callback_data="support")]
    ]
    
    # اگر ادمین است، منوی ادمین را اضافه کن
    if telegram_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ مدیریت", callback_data="admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "buy":
        await show_buy_menu(query, context)
    elif data == "status":
        await show_status(query, context)
    elif data == "profile":
        await show_profile(query, context)
    elif data == "wallet":
        await show_wallet(query, context)
    elif data == "support":
        await show_support(query, context)
    elif data == "admin":
        if user_id == ADMIN_ID:
            await show_admin_menu(query, context)
    elif data.startswith("admin_"):
        if user_id == ADMIN_ID:
            await handle_admin_action(query, context, data)
    elif data.startswith("buy_"):
        await handle_buy_action(query, context, data)
    elif data == "back_main":
        await back_main_handler(query, context)

async def show_buy_menu(query, context):
    """نمایش منوی خرید"""
    text = """
📌 خرید حجم

لطفاً پلن مورد نظر را انتخاب کنید:

• پلن 1: 10 گیگابایت - 30 روز - 50,000 تومان
• پلن 2: 30 گیگابایت - 30 روز - 100,000 تومان
• پلن 3: 50 گیگابایت - 30 روز - 150,000 تومان
• پلن 4: 100 گیگابایت - 30 روز - 250,000 تومان
"""
    
    keyboard = [
        [InlineKeyboardButton("پلن 1 (10GB)", callback_data="buy_10")],
        [InlineKeyboardButton("پلن 2 (30GB)", callback_data="buy_30")],
        [InlineKeyboardButton("پلن 3 (50GB)", callback_data="buy_50")],
        [InlineKeyboardButton("پلن 4 (100GB)", callback_data="buy_100")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_buy_action(query, context, data):
    """مدیریت خرید"""
    user_info = get_user_by_telegram_id(query.from_user.id)
    if not user_info:
        await query.edit_message_text("❌ خطا در دریافت اطلاعات کاربر")
        return
    
    # استخراج حجم از callback_data
    gb_map = {"buy_10": 10, "buy_30": 30, "buy_50": 50, "buy_100": 100}
    gb = gb_map.get(data, 10)
    price = gb * 5000  # قیمت هر گیگابایت
    
    if user_info.get("balance", 0) < price:
        text = f"""
❌ موجودی کافی نیست!

موجودی فعلی: {user_info.get('balance', 0):,} تومان
مبلغ مورد نیاز: {price:,} تومان

لطفاً ابتدا کیف پول خود را شارژ کنید.
"""
        keyboard = [[InlineKeyboardButton("💳 شارژ کیف پول", callback_data="wallet")],
                   [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # ساخت کانفیگ
    result = api_request("POST", "/configs/create", {
        "user_id": user_info["id"],
        "total_gb": gb,
        "days": 30
    })
    
    if result and result.get("success"):
        # کسر از موجودی
        api_request("POST", "/wallet/add", {
            "user_id": user_info["id"],
            "amount": -price,
            "description": f"خرید پلن {gb} گیگابایت"
        })
        
        text = f"""
✅ کانفیگ شما با موفقیت ساخته شد!

📊 جزئیات:
• حجم: {gb} گیگابایت
• مدت: 30 روز
• مبلغ: {price:,} تومان

🔗 لینک کانفیگ:
{result.get('link', '')}

⚠️ لطفاً این لینک را در اپلیکیشن خود وارد کنید.
"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await query.edit_message_text("❌ خطا در ساخت کانفیگ. لطفاً با پشتیبانی تماس بگیرید.")

async def show_status(query, context):
    """نمایش وضعیت سرویس"""
    user_info = get_user_by_telegram_id(query.from_user.id)
    if not user_info:
        await query.edit_message_text("❌ خطا در دریافت اطلاعات")
        return
    
    configs = user_info.get("configs", [])
    
    if not configs:
        text = """
📊 وضعیت سرویس

شما هنوز هیچ سرویسی فعال ندارید.

برای خرید سرویس، از منوی اصلی گزینه "خرید حجم" را انتخاب کنید.
"""
    else:
        text = "📊 وضعیت سرویس‌های شما:\n\n"
        for i, config in enumerate(configs, 1):
            status = "✅ فعال" if config.get("is_active") else "❌ غیرفعال"
            used = config.get("used_gb", 0)
            total = config.get("total_gb", 0)
            remaining = total - used if total > 0 else "نامحدود"
            
            text += f"""
سرویس {i}:
• وضعیت: {status}
• مصرف شده: {used:.2f} GB
• کل حجم: {total} GB
• باقی‌مانده: {remaining} GB
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_profile(query, context):
    """نمایش پروفایل"""
    user_info = get_user_by_telegram_id(query.from_user.id)
    if not user_info:
        await query.edit_message_text("❌ خطا در دریافت اطلاعات")
        return
    
    text = f"""
👤 پروفایل شما

• نام کاربری: @{user_info.get('username', 'نامشخص')}
• نام کامل: {user_info.get('full_name', 'نامشخص')}
• موجودی: {user_info.get('balance', 0):,} تومان
• تعداد سرویس‌ها: {len(user_info.get('configs', []))}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_wallet(query, context):
    """نمایش کیف پول"""
    user_info = get_user_by_telegram_id(query.from_user.id)
    if not user_info:
        await query.edit_message_text("❌ خطا در دریافت اطلاعات")
        return
    
    balance = user_info.get("balance", 0)
    
    text = f"""
💳 کیف پول

• موجودی فعلی: {balance:,} تومان

برای شارژ کیف پول، لطفاً با پشتیبانی تماس بگیرید.
"""
    
    keyboard = [
        [InlineKeyboardButton("📋 تاریخچه تراکنش‌ها", callback_data="wallet_history")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_support(query, context):
    """نمایش منوی پشتیبانی"""
    text = """
🎫 پشتیبانی

برای ارسال تیکت پشتیبانی، لطفاً پیام خود را ارسال کنید.

یا می‌توانید از طریق منوی اصلی بازگردید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)
    
    # ذخیره وضعیت برای دریافت پیام بعدی
    context.user_data["waiting_for_ticket"] = True

async def show_admin_menu(query, context):
    """نمایش منوی ادمین"""
    text = """
⚙️ پنل مدیریت

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    
    keyboard = [
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("📋 لیست کانفیگ‌ها", callback_data="admin_configs")],
        [InlineKeyboardButton("➕ ساخت کانفیگ", callback_data="admin_create")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_admin_action(query, context, data):
    """مدیریت عملیات ادمین"""
    if data == "admin_users":
        users = api_request("GET", "/admin/users")
        if users:
            text = "👥 لیست کاربران:\n\n"
            for user in users[:10]:  # فقط 10 کاربر اول
                text += f"• @{user.get('username', 'نامشخص')} - موجودی: {user.get('balance', 0):,} تومان\n"
            if len(users) > 10:
                text += f"\n... و {len(users) - 10} کاربر دیگر"
        else:
            text = "❌ خطا در دریافت لیست کاربران"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif data == "admin_configs":
        configs = api_request("GET", "/admin/configs")
        if configs:
            text = f"📋 لیست کانفیگ‌ها:\n\nتعداد کل: {len(configs)}\n"
            active = sum(1 for c in configs if c.get("is_active"))
            text += f"فعال: {active}\nغیرفعال: {len(configs) - active}"
        else:
            text = "❌ خطا در دریافت لیست کانفیگ‌ها"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    if context.user_data.get("waiting_for_ticket"):
        # ایجاد تیکت
        user_info = get_user_by_telegram_id(update.effective_user.id)
        if user_info:
            result = api_request("POST", "/tickets/create", {
                "user_id": user_info["id"],
                "subject": "تیکت پشتیبانی",
                "message": update.message.text
            })
            
            if result and result.get("success"):
                await update.message.reply_text("✅ تیکت شما با موفقیت ثبت شد. به زودی پاسخ داده می‌شود.")
            else:
                await update.message.reply_text("❌ خطا در ثبت تیکت. لطفاً دوباره تلاش کنید.")
        
        context.user_data["waiting_for_ticket"] = False


def main():
    """تابع اصلی"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده است!")
        return
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن handlerها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # شروع ربات
    logger.info("ربات در حال راه‌اندازی...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()


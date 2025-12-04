# راهنمای اجرای ربات Server24

## 🚀 اجرای دستی ربات (برای تست)

### 1. فعال‌سازی Environment Variables

```bash
export BOT_TOKEN="your_bot_token"
export ADMIN_ID="your_admin_id"
export DOMAIN="your-domain.com"
export DATABASE_PATH="/opt/server24/database/server24.db"
export XRAY_CONFIG_PATH="/usr/local/etc/xray/config.json"
export FRONTEND_PATH="/opt/server24/frontend"
```

یا استفاده از فایل `.env`:

```bash
cd /opt/server24
source .env
```

### 2. اجرای API (FastAPI)

```bash
cd /opt/server24/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. اجرای ربات تلگرام

در ترمینال جدید:

```bash
cd /opt/server24/bot
python3 bot.py
```

## 🔧 اجرای با Systemd (پس از نصب کامل)

### بررسی وضعیت سرویس‌ها

```bash
systemctl status server24-api
systemctl status server24-bot
systemctl status xray
systemctl status nginx
```

### راه‌اندازی سرویس‌ها

```bash
systemctl start server24-api
systemctl start server24-bot
systemctl start xray
systemctl start nginx
```

### فعال‌سازی سرویس‌ها برای راه‌اندازی خودکار

```bash
systemctl enable server24-api
systemctl enable server24-bot
systemctl enable xray
systemctl enable nginx
```

### ری‌استارت سرویس‌ها

```bash
systemctl restart server24-api
systemctl restart server24-bot
systemctl restart xray
systemctl restart nginx
```

### مشاهده لاگ‌ها

```bash
# لاگ API
journalctl -u server24-api -f

# لاگ ربات
journalctl -u server24-bot -f

# لاگ Xray
journalctl -u xray -f

# لاگ Nginx
journalctl -u nginx -f
```

## 🐛 عیب‌یابی

### مشکل: ربات اجرا نمی‌شود

1. بررسی توکن ربات:
```bash
cat /opt/server24/.env | grep BOT_TOKEN
```

2. بررسی لاگ ربات:
```bash
journalctl -u server24-bot -n 50
```

3. تست دستی ربات:
```bash
cd /opt/server24/bot
export $(cat /opt/server24/.env | xargs)
python3 bot.py
```

### مشکل: API اجرا نمی‌شود

1. بررسی پورت 8000:
```bash
netstat -tlnp | grep 8000
```

2. بررسی لاگ API:
```bash
journalctl -u server24-api -n 50
```

3. تست دستی API:
```bash
cd /opt/server24/backend
export $(cat /opt/server24/.env | xargs)
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### مشکل: دیتابیس پیدا نمی‌شود

```bash
ls -la /opt/server24/database/
```

اگر دیتابیس وجود ندارد، دوباره ساخت:
```bash
cd /opt/server24
export ADMIN_ID="your_admin_id"
python3 << 'EOF'
import sqlite3
import os

db_path = "/opt/server24/database/server24.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    balance INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    uuid TEXT UNIQUE NOT NULL,
    port INTEGER NOT NULL,
    flow TEXT,
    total_gb INTEGER DEFAULT 0,
    used_gb REAL DEFAULT 0,
    expire_date TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    admin_reply TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')

admin_id = int(os.environ.get('ADMIN_ID', '0'))
if admin_id > 0:
    cursor.execute('''
    INSERT OR IGNORE INTO users (telegram_id, username, full_name, is_admin, balance)
    VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, 'admin', 'Admin', 1, 0))

conn.commit()
conn.close()
print("✅ دیتابیس با موفقیت ساخته شد")
EOF
```

## 📝 نکات مهم

1. **همیشه از systemd استفاده کنید** برای اجرای دائمی سرویس‌ها
2. **بررسی لاگ‌ها** اولین قدم در عیب‌یابی است
3. **مطمئن شوید** که فایل `.env` درست تنظیم شده است
4. **بررسی کنید** که پورت‌های 80 و 443 باز هستند

## 🔄 به‌روزرسانی

برای به‌روزرسانی ربات:

```bash
cd /opt/server24/bot
curl -sL "https://raw.githubusercontent.com/saeed-rahimi/saeedrahimi/main/bot/bot.py" -o bot.py
systemctl restart server24-bot
```

برای به‌روزرسانی API:

```bash
cd /opt/server24/backend
curl -sL "https://raw.githubusercontent.com/saeed-rahimi/saeedrahimi/main/backend/main.py" -o main.py
systemctl restart server24-api
```


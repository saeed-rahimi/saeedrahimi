#!/bin/bash

set -e

echo "🚀 شروع نصب Server24..."

# رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# تابع برای نمایش پیام
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# بررسی root بودن
if [ "$EUID" -ne 0 ]; then 
    print_error "لطفاً با دسترسی root اجرا کنید: sudo bash install.sh"
    exit 1
fi

# دریافت اطلاعات از کاربر
print_info "دریافت اطلاعات اولیه..."

read -p "توکن ربات تلگرام را وارد کنید: " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    print_error "توکن ربات نمی‌تواند خالی باشد!"
    exit 1
fi

read -p "ایدی عددی ادمین تلگرام را وارد کنید: " ADMIN_ID
if [ -z "$ADMIN_ID" ]; then
    print_error "ایدی ادمین نمی‌تواند خالی باشد!"
    exit 1
fi

read -p "دامنه یا ساب‌دامین سایت را وارد کنید (مثال: panel.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    print_error "دامنه نمی‌تواند خالی باشد!"
    exit 1
fi

# تعیین مسیر پروژه
PROJECT_DIR="/opt/server24"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

print_info "مسیر پروژه: $PROJECT_DIR"

# قدم 1: آپدیت سیستم
print_info "آپدیت سیستم..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

# قدم 2: نصب پیش‌نیازها
print_info "نصب پیش‌نیازها..."
apt-get install -y python3 python3-pip python3-venv curl wget git ufw certbot python3-certbot-nginx

# نصب Nginx
print_info "نصب Nginx..."
apt-get install -y nginx

# نصب پکیج‌های Python
print_info "نصب پکیج‌های Python..."
pip3 install fastapi uvicorn[standard] python-telegram-bot sqlalchemy aiofiles python-multipart jinja2

# قدم 3: نصب Xray-core
print_info "نصب Xray-core..."
XRAY_VERSION=$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//')
ARCH=$(uname -m)

case $ARCH in
    x86_64)
        ARCH_TYPE="64"
        ;;
    aarch64)
        ARCH_TYPE="arm64-v8a"
        ;;
    armv7l)
        ARCH_TYPE="arm32-v7a"
        ;;
    *)
        print_error "معماری سیستم پشتیبانی نمی‌شود: $ARCH"
        exit 1
        ;;
esac

XRAY_URL="https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-${ARCH_TYPE}.zip"

print_info "دانلود Xray-core نسخه $XRAY_VERSION..."
wget -q $XRAY_URL -O /tmp/xray.zip
unzip -q /tmp/xray.zip -d /tmp/xray
mv /tmp/xray/xray /usr/local/bin/xray
chmod +x /usr/local/bin/xray
rm -rf /tmp/xray /tmp/xray.zip

# ساخت فایل service برای Xray
print_info "ساخت سرویس Xray..."
cat > /etc/systemd/system/xray.service << EOF
[Unit]
Description=Xray Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# ساخت پوشه کانفیگ Xray
mkdir -p /usr/local/etc/xray

# ساخت کانفیگ اولیه Xray
cat > /usr/local/etc/xray/config.json << 'EOF'
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none",
        "fallbacks": [
          {
            "dest": 80
          }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            {
              "certificateFile": "/etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem",
              "keyFile": "/etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem"
            }
          ]
        },
        "wsSettings": {
          "path": "/vless"
        }
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom"
    }
  ]
}
EOF

# جایگزینی DOMAIN_PLACEHOLDER
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /usr/local/etc/xray/config.json

# قدم 4: راه‌اندازی دیتابیس
print_info "راه‌اندازی دیتابیس..."
mkdir -p $PROJECT_DIR/database
export ADMIN_ID=$ADMIN_ID
python3 << 'PYTHON_SCRIPT'
import sqlite3
import os

db_path = "/opt/server24/database/server24.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# جدول کاربران
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

# جدول کانفیگ‌ها
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

# جدول کیف پول
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

# جدول تیکت‌ها
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

# جدول لاگ‌ها
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

# اضافه کردن ادمین اولیه
cursor.execute('''
INSERT OR IGNORE INTO users (telegram_id, username, full_name, is_admin, balance)
VALUES (?, ?, ?, ?, ?)
''', (int(os.environ.get('ADMIN_ID', '0')), 'admin', 'Admin', 1, 0))

conn.commit()
conn.close()
print("✅ دیتابیس با موفقیت ساخته شد")
PYTHON_SCRIPT

# دانلود فایل‌های پروژه از GitHub
print_info "دانلود فایل‌های پروژه از GitHub..."
GITHUB_REPO="https://raw.githubusercontent.com/saeed-rahimi/saeedrahimi/main"

# ساخت پوشه‌های لازم
mkdir -p $PROJECT_DIR/backend
mkdir -p $PROJECT_DIR/bot
mkdir -p $PROJECT_DIR/frontend
mkdir -p $PROJECT_DIR/scripts
mkdir -p $PROJECT_DIR/configs
mkdir -p $PROJECT_DIR/database

# دانلود فایل‌های backend
print_info "دانلود فایل‌های backend..."
curl -sL "$GITHUB_REPO/backend/main.py" -o $PROJECT_DIR/backend/main.py
curl -sL "$GITHUB_REPO/backend/requirements.txt" -o $PROJECT_DIR/backend/requirements.txt

# دانلود فایل‌های bot
print_info "دانلود فایل‌های bot..."
curl -sL "$GITHUB_REPO/bot/bot.py" -o $PROJECT_DIR/bot/bot.py
curl -sL "$GITHUB_REPO/bot/requirements.txt" -o $PROJECT_DIR/bot/requirements.txt

# دانلود فایل‌های frontend
print_info "دانلود فایل‌های frontend..."
curl -sL "$GITHUB_REPO/frontend/login.html" -o $PROJECT_DIR/frontend/login.html
curl -sL "$GITHUB_REPO/frontend/dashboard.html" -o $PROJECT_DIR/frontend/dashboard.html
curl -sL "$GITHUB_REPO/frontend/buy.html" -o $PROJECT_DIR/frontend/buy.html
curl -sL "$GITHUB_REPO/frontend/wallet.html" -o $PROJECT_DIR/frontend/wallet.html
curl -sL "$GITHUB_REPO/frontend/profile.html" -o $PROJECT_DIR/frontend/profile.html
curl -sL "$GITHUB_REPO/frontend/tickets.html" -o $PROJECT_DIR/frontend/tickets.html
curl -sL "$GITHUB_REPO/frontend/admin.html" -o $PROJECT_DIR/frontend/admin.html
curl -sL "$GITHUB_REPO/frontend/admin-users.html" -o $PROJECT_DIR/frontend/admin-users.html
curl -sL "$GITHUB_REPO/frontend/admin-configs.html" -o $PROJECT_DIR/frontend/admin-configs.html
curl -sL "$GITHUB_REPO/frontend/index.html" -o $PROJECT_DIR/frontend/index.html
curl -sL "$GITHUB_REPO/frontend/style.css" -o $PROJECT_DIR/frontend/style.css

# دانلود فایل‌های scripts
print_info "دانلود فایل‌های scripts..."
curl -sL "$GITHUB_REPO/scripts/xray_manager.py" -o $PROJECT_DIR/scripts/xray_manager.py

# تنظیم دسترسی‌ها
chmod +x $PROJECT_DIR/scripts/*.py 2>/dev/null || true

# بررسی موفقیت دانلود
if [ ! -f "$PROJECT_DIR/backend/main.py" ]; then
    print_error "خطا در دانلود فایل‌های پروژه از GitHub!"
    print_warning "لطفاً دستی فایل‌ها را از GitHub دانلود کنید:"
    print_warning "git clone https://github.com/saeed-rahimi/saeedrahimi.git"
    exit 1
fi

print_info "✅ فایل‌های پروژه با موفقیت دانلود شدند."

# ساخت فایل .env
print_info "ساخت فایل .env..."
cat > $PROJECT_DIR/.env << EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
DOMAIN=$DOMAIN
PROJECT_DIR=$PROJECT_DIR
DATABASE_PATH=$PROJECT_DIR/database/server24.db
XRAY_CONFIG_PATH=/usr/local/etc/xray/config.json
FRONTEND_PATH=$PROJECT_DIR/frontend
EOF

# تنظیم environment variables برای سرویس‌ها
export BOT_TOKEN=$BOT_TOKEN
export ADMIN_ID=$ADMIN_ID
export DOMAIN=$DOMAIN
export DATABASE_PATH=$PROJECT_DIR/database/server24.db
export XRAY_CONFIG_PATH=/usr/local/etc/xray/config.json
export FRONTEND_PATH=$PROJECT_DIR/frontend

# قدم 5: ساخت سرویس FastAPI
print_info "ساخت سرویس FastAPI..."
cat > /etc/systemd/system/server24-api.service << EOF
[Unit]
Description=Server24 FastAPI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/backend
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# قدم 6: ساخت سرویس ربات تلگرام
print_info "ساخت سرویس ربات تلگرام..."
cat > /etc/systemd/system/server24-bot.service << EOF
[Unit]
Description=Server24 Telegram Bot
After=network.target server24-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/bot
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=/usr/bin/python3 bot.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# قدم 7: تنظیم Nginx
print_info "تنظیم Nginx..."
cat > /etc/nginx/sites-available/server24 << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        root $PROJECT_DIR/frontend;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    location /vless {
        proxy_pass http://127.0.0.1:443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/server24 /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# قدم 8: دریافت SSL
print_info "دریافت گواهینامه SSL..."
certbot certonly --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || {
    print_warning "دریافت SSL با مشکل مواجه شد. لطفاً بعداً دستی انجام دهید."
}

# قدم 9: تنظیم فایروال
print_info "تنظیم فایروال..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# قدم 10: فعال‌سازی سرویس‌ها
print_info "فعال‌سازی سرویس‌ها..."
systemctl daemon-reload
systemctl enable xray
systemctl enable server24-api
systemctl enable server24-bot
systemctl enable nginx

# راه‌اندازی سرویس‌ها
print_info "راه‌اندازی سرویس‌ها..."
systemctl restart nginx
systemctl restart xray
systemctl restart server24-api
systemctl restart server24-bot

print_info "✅ نصب با موفقیت انجام شد!"
print_info "🌐 پنل شما در آدرس زیر در دسترس است:"
print_info "   https://$DOMAIN"
print_info ""
print_info "📋 وضعیت سرویس‌ها:"
systemctl status xray --no-pager -l | head -3
systemctl status server24-api --no-pager -l | head -3
systemctl status server24-bot --no-pager -l | head -3

print_info ""
print_info "🎉 پروژه Server24 با موفقیت نصب شد!"


# راهنمای مشارکت در پروژه

## ساختار پروژه

```
server24/
├── backend/          # FastAPI Backend
│   ├── main.py      # فایل اصلی API
│   └── requirements.txt
├── bot/              # ربات تلگرام
│   ├── bot.py       # فایل اصلی ربات
│   └── requirements.txt
├── frontend/         # صفحات HTML/CSS
│   ├── *.html       # صفحات مختلف
│   └── style.css    # استایل‌ها
├── scripts/          # اسکریپت‌های کمکی
│   └── xray_manager.py
├── configs/          # فایل‌های کانفیگ
├── install.sh        # اسکریپت نصب
└── README.md
```

## نحوه مشارکت

1. Fork کردن پروژه
2. ساخت branch جدید: `git checkout -b feature/amazing-feature`
3. Commit کردن تغییرات: `git commit -m 'Add amazing feature'`
4. Push کردن به branch: `git push origin feature/amazing-feature`
5. باز کردن Pull Request

## استانداردهای کد

- استفاده از Python 3.10+
- رعایت PEP 8 برای Python
- کامنت‌گذاری مناسب
- استفاده از نام‌های فارسی برای متغیرهای مربوط به کاربر

## تست

قبل از ارسال PR، لطفاً:
- کد را تست کنید
- مطمئن شوید که خطای syntax وجود ندارد
- بررسی کنید که تمام قابلیت‌ها کار می‌کنند


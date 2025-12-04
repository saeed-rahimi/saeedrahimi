# راهنمای رفع مشکل SSL و Nginx

## مشکل فعلی

Nginx نمی‌تواند start شود چون به فایل‌های SSL که هنوز دریافت نشده‌اند اشاره می‌کند.

## راه حل سریع

### مرحله 1: تنظیم Nginx با HTTP (موقت)

```bash
cat > /etc/nginx/sites-available/server24 << 'EOF'
server {
    listen 80;
    server_name panel.server24net.online;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /opt/server24/frontend;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    location /vless {
        proxy_pass http://127.0.0.1:443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# تست کانفیگ
nginx -t

# راه‌اندازی Nginx
systemctl restart nginx
```

### مرحله 2: دریافت SSL

```bash
# دریافت SSL با webroot
certbot certonly --webroot -w /var/www/html -d panel.server24net.online --non-interactive --agree-tos --register-unsafely-without-email --email admin@panel.server24net.online
```

### مرحله 3: به‌روزرسانی Nginx با SSL

```bash
cat > /etc/nginx/sites-available/server24 << 'EOF'
server {
    listen 80;
    server_name panel.server24net.online;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name panel.server24net.online;

    ssl_certificate /etc/letsencrypt/live/panel.server24net.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/panel.server24net.online/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /opt/server24/frontend;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    location /vless {
        proxy_pass http://127.0.0.1:443;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# تست و راه‌اندازی
nginx -t && systemctl reload nginx
```

## بررسی وضعیت

```bash
# بررسی وضعیت Nginx
systemctl status nginx

# بررسی لاگ Nginx
journalctl -u nginx -n 50

# بررسی SSL
ls -la /etc/letsencrypt/live/panel.server24net.online/
```

## راه‌اندازی سرویس‌ها

```bash
# راه‌اندازی API
systemctl start server24-api
systemctl status server24-api

# راه‌اندازی ربات
systemctl start server24-bot
systemctl status server24-bot

# راه‌اندازی Xray
systemctl start xray
systemctl status xray
```

## تست

```bash
# تست API
curl http://localhost:8000/api/health

# تست Nginx
curl http://panel.server24net.online
curl https://panel.server24net.online
```


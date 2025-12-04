from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
import sqlite3
import json
import uuid
import os
import subprocess
from typing import Optional
import secrets

app = FastAPI(title="Server24 API")

# سرو کردن فایل‌های استاتیک
frontend_path = os.getenv("FRONTEND_PATH", "/opt/server24/frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# تنظیمات دیتابیس
DATABASE_PATH = os.getenv("DATABASE_PATH", "/opt/server24/database/server24.db")
engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# مدل‌های دیتابیس
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    balance = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    configs = relationship("Config", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")

class Config(Base):
    __tablename__ = "configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    uuid = Column(String, unique=True, nullable=False)
    port = Column(Integer, nullable=False)
    flow = Column(String)
    total_gb = Column(Integer, default=0)
    used_gb = Column(Float, default=0.0)
    expire_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="configs")

class Wallet(Base):
    __tablename__ = "wallet"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, default="open")
    admin_reply = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="tickets")

class Log(Base):
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# ساخت جداول
Base.metadata.create_all(bind=engine)

# Dependency برای دیتابیس
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# تنظیمات
DOMAIN = os.getenv("DOMAIN", "localhost")
XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/usr/local/etc/xray/config.json")

# توابع کمکی
def load_xray_config():
    """بارگذاری کانفیگ Xray"""
    try:
        with open(XRAY_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        return None

def save_xray_config(config):
    """ذخیره کانفیگ Xray"""
    try:
        with open(XRAY_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        # ری‌استارت Xray
        subprocess.run(["systemctl", "reload", "xray"], check=False)
        return True
    except Exception as e:
        return False

def generate_vless_link(uuid: str, port: int, domain: str, flow: str = ""):
    """تولید لینک VLESS"""
    if flow:
        return f"vless://{uuid}@{domain}:443?type=ws&security=tls&path=/vless&flow={flow}#Server24"
    return f"vless://{uuid}@{domain}:443?type=ws&security=tls&path=/vless#Server24"

def get_free_port():
    """دریافت پورت آزاد"""
    xray_config = load_xray_config()
    if not xray_config:
        return 10000
    
    used_ports = set()
    for inbound in xray_config.get("inbounds", []):
        if "port" in inbound:
            used_ports.add(inbound["port"])
    
    # بررسی پورت‌های موجود در دیتابیس
    db = SessionLocal()
    try:
        existing_ports = {c.port for c in db.query(Config).all()}
        used_ports.update(existing_ports)
    finally:
        db.close()
    
    port = 10000
    while port in used_ports:
        port += 1
    return port

# API Routes

@app.get("/")
async def root():
    return RedirectResponse(url="/login.html")

# Serve HTML files
@app.get("/{filename}.html")
async def serve_html(filename: str):
    """سرو کردن فایل‌های HTML"""
    html_path = os.path.join(frontend_path, f"{filename}.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="صفحه یافت نشد")

@app.get("/style.css")
async def serve_css():
    """سرو کردن فایل CSS"""
    css_path = os.path.join(frontend_path, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="فایل CSS یافت نشد")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# API کاربران
@app.post("/api/users/register")
async def register_user(telegram_id: int, username: str = None, full_name: str = None, db: Session = Depends(get_db)):
    """ثبت‌نام کاربر جدید"""
    existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing_user:
        return {"success": True, "user_id": existing_user.id, "message": "کاربر از قبل وجود دارد"}
    
    new_user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"success": True, "user_id": new_user.id, "message": "کاربر با موفقیت ثبت شد"}

@app.get("/api/users/{telegram_id}")
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    """دریافت اطلاعات کاربر"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    configs = db.query(Config).filter(Config.user_id == user.id).all()
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "balance": user.balance,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "configs": [
            {
                "id": c.id,
                "uuid": c.uuid,
                "port": c.port,
                "total_gb": c.total_gb,
                "used_gb": c.used_gb,
                "expire_date": c.expire_date.isoformat() if c.expire_date else None,
                "is_active": c.is_active
            }
            for c in configs
        ]
    }

# API کانفیگ‌ها
@app.post("/api/configs/create")
async def create_config(user_id: int, total_gb: int = 0, days: int = 30, db: Session = Depends(get_db)):
    """ساخت کانفیگ جدید"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    # تولید UUID و پورت
    config_uuid = str(uuid.uuid4())
    port = get_free_port()
    
    # محاسبه تاریخ انقضا
    expire_date = datetime.utcnow() + timedelta(days=days)
    
    # ساخت کانفیگ در دیتابیس
    new_config = Config(
        user_id=user_id,
        uuid=config_uuid,
        port=port,
        total_gb=total_gb,
        expire_date=expire_date
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    # اضافه کردن به کانفیگ Xray
    xray_config = load_xray_config()
    if xray_config:
        # پیدا کردن inbound مربوط به VLESS
        for inbound in xray_config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                clients = inbound.get("settings", {}).get("clients", [])
                clients.append({
                    "id": config_uuid,
                    "flow": ""
                })
                inbound["settings"]["clients"] = clients
                break
        
        save_xray_config(xray_config)
    
    # تولید لینک
    link = generate_vless_link(config_uuid, port, DOMAIN)
    
    return {
        "success": True,
        "config_id": new_config.id,
        "uuid": config_uuid,
        "port": port,
        "link": link,
        "expire_date": expire_date.isoformat()
    }

@app.get("/api/configs/{config_id}")
async def get_config(config_id: int, db: Session = Depends(get_db)):
    """دریافت اطلاعات کانفیگ"""
    config = db.query(Config).filter(Config.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="کانفیگ یافت نشد")
    
    link = generate_vless_link(config.uuid, config.port, DOMAIN)
    
    return {
        "id": config.id,
        "uuid": config.uuid,
        "port": config.port,
        "total_gb": config.total_gb,
        "used_gb": config.used_gb,
        "expire_date": config.expire_date.isoformat() if config.expire_date else None,
        "is_active": config.is_active,
        "link": link
    }

@app.post("/api/configs/{config_id}/renew")
async def renew_config(config_id: int, days: int, db: Session = Depends(get_db)):
    """تمدید کانفیگ"""
    config = db.query(Config).filter(Config.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="کانفیگ یافت نشد")
    
    if config.expire_date:
        config.expire_date = config.expire_date + timedelta(days=days)
    else:
        config.expire_date = datetime.utcnow() + timedelta(days=days)
    
    db.commit()
    
    return {"success": True, "expire_date": config.expire_date.isoformat()}

@app.post("/api/configs/{config_id}/update-traffic")
async def update_traffic(config_id: int, used_gb: float, db: Session = Depends(get_db)):
    """به‌روزرسانی ترافیک مصرفی"""
    config = db.query(Config).filter(Config.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="کانفیگ یافت نشد")
    
    config.used_gb = used_gb
    db.commit()
    
    return {"success": True}

@app.delete("/api/configs/{config_id}")
async def delete_config(config_id: int, db: Session = Depends(get_db)):
    """حذف کانفیگ"""
    config = db.query(Config).filter(Config.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="کانفیگ یافت نشد")
    
    # حذف از کانفیگ Xray
    xray_config = load_xray_config()
    if xray_config:
        for inbound in xray_config.get("inbounds", []):
            if inbound.get("protocol") == "vless":
                clients = inbound.get("settings", {}).get("clients", [])
                inbound["settings"]["clients"] = [c for c in clients if c.get("id") != config.uuid]
                break
        save_xray_config(xray_config)
    
    db.delete(config)
    db.commit()
    
    return {"success": True}

# API کیف پول
@app.post("/api/wallet/add")
async def add_balance(user_id: int, amount: int, description: str = None, db: Session = Depends(get_db)):
    """افزودن موجودی به کیف پول"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    user.balance += amount
    
    wallet_entry = Wallet(
        user_id=user_id,
        amount=amount,
        description=description or "افزایش موجودی"
    )
    db.add(wallet_entry)
    db.commit()
    
    return {"success": True, "new_balance": user.balance}

@app.get("/api/wallet/{user_id}/history")
async def wallet_history(user_id: int, db: Session = Depends(get_db)):
    """تاریخچه تراکنش‌های کیف پول"""
    history = db.query(Wallet).filter(Wallet.user_id == user_id).order_by(Wallet.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": w.id,
            "amount": w.amount,
            "description": w.description,
            "created_at": w.created_at.isoformat()
        }
        for w in history
    ]

# API تیکت‌ها
@app.post("/api/tickets/create")
async def create_ticket(user_id: int, subject: str, message: str, db: Session = Depends(get_db)):
    """ایجاد تیکت جدید"""
    ticket = Ticket(
        user_id=user_id,
        subject=subject,
        message=message
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    return {"success": True, "ticket_id": ticket.id}

@app.get("/api/tickets/{user_id}")
async def get_user_tickets(user_id: int, db: Session = Depends(get_db)):
    """دریافت تیکت‌های کاربر"""
    tickets = db.query(Ticket).filter(Ticket.user_id == user_id).order_by(Ticket.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "subject": t.subject,
            "message": t.message,
            "status": t.status,
            "admin_reply": t.admin_reply,
            "created_at": t.created_at.isoformat()
        }
        for t in tickets
    ]

# API ادمین
@app.get("/api/admin/users")
async def admin_get_users(db: Session = Depends(get_db)):
    """لیست تمام کاربران (فقط ادمین)"""
    users = db.query(User).all()
    
    return [
        {
            "id": u.id,
            "telegram_id": u.telegram_id,
            "username": u.username,
            "full_name": u.full_name,
            "balance": u.balance,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]

@app.get("/api/admin/configs")
async def admin_get_configs(db: Session = Depends(get_db)):
    """لیست تمام کانفیگ‌ها (فقط ادمین)"""
    configs = db.query(Config).all()
    
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "uuid": c.uuid,
            "port": c.port,
            "total_gb": c.total_gb,
            "used_gb": c.used_gb,
            "expire_date": c.expire_date.isoformat() if c.expire_date else None,
            "is_active": c.is_active
        }
        for c in configs
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


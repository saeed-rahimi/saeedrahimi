#!/usr/bin/env python3
"""
اسکریپت مدیریت Xray-core
برای ساخت، حذف و به‌روزرسانی کانفیگ‌ها
"""

import json
import os
import sys
import subprocess
from typing import Dict, List, Optional

XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/usr/local/etc/xray/config.json")

def load_config() -> Optional[Dict]:
    """بارگذاری کانفیگ Xray"""
    try:
        with open(XRAY_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"خطا در بارگذاری کانفیگ: {e}")
        return None

def save_config(config: Dict) -> bool:
    """ذخیره کانفیگ Xray"""
    try:
        with open(XRAY_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"خطا در ذخیره کانفیگ: {e}")
        return False

def reload_xray() -> bool:
    """ری‌لود سرویس Xray"""
    try:
        subprocess.run(["systemctl", "reload", "xray"], check=True)
        return True
    except Exception as e:
        print(f"خطا در ری‌لود Xray: {e}")
        return False

def add_client(uuid: str, flow: str = "") -> bool:
    """افزودن کلاینت جدید به کانفیگ"""
    config = load_config()
    if not config:
        return False
    
    # پیدا کردن inbound مربوط به VLESS
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless":
            clients = inbound.get("settings", {}).get("clients", [])
            
            # بررسی وجود UUID
            if any(c.get("id") == uuid for c in clients):
                print(f"UUID {uuid} از قبل وجود دارد")
                return False
            
            clients.append({
                "id": uuid,
                "flow": flow
            })
            inbound["settings"]["clients"] = clients
            break
    
    if save_config(config):
        return reload_xray()
    return False

def remove_client(uuid: str) -> bool:
    """حذف کلاینت از کانفیگ"""
    config = load_config()
    if not config:
        return False
    
    # پیدا کردن inbound مربوط به VLESS
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless":
            clients = inbound.get("settings", {}).get("clients", [])
            inbound["settings"]["clients"] = [c for c in clients if c.get("id") != uuid]
            break
    
    if save_config(config):
        return reload_xray()
    return False

def list_clients() -> List[Dict]:
    """لیست تمام کلاینت‌ها"""
    config = load_config()
    if not config:
        return []
    
    clients = []
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") == "vless":
            clients = inbound.get("settings", {}).get("clients", [])
            break
    
    return clients

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("استفاده:")
        print("  python3 xray_manager.py add <uuid> [flow]")
        print("  python3 xray_manager.py remove <uuid>")
        print("  python3 xray_manager.py list")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 3:
            print("لطفاً UUID را وارد کنید")
            sys.exit(1)
        uuid = sys.argv[2]
        flow = sys.argv[3] if len(sys.argv) > 3 else ""
        if add_client(uuid, flow):
            print(f"✅ کلاینت {uuid} با موفقیت اضافه شد")
        else:
            print(f"❌ خطا در افزودن کلاینت")
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("لطفاً UUID را وارد کنید")
            sys.exit(1)
        uuid = sys.argv[2]
        if remove_client(uuid):
            print(f"✅ کلاینت {uuid} با موفقیت حذف شد")
        else:
            print(f"❌ خطا در حذف کلاینت")
    
    elif command == "list":
        clients = list_clients()
        print(f"تعداد کلاینت‌ها: {len(clients)}")
        for client in clients:
            print(f"  - {client.get('id')}")
    
    else:
        print("دستور نامعتبر")
        sys.exit(1)


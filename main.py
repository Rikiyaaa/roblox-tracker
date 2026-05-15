import os
import time
import requests

ROBLOX_USER_ID = int(os.environ["ROBLOX_USER_ID"])
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))


def check_roblox_presence(user_id):
    """เช็คสถานะผ่าน Presence API (ต้องใช้ cookie บางที)"""
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }
    payload = {"userIds": [user_id]}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[DEBUG] Presence API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[DEBUG] Response: {data}")
            
            if data.get("userPresences"):
                presence_type = data["userPresences"][0]["userPresenceType"]
                print(f"[DEBUG] userPresenceType = {presence_type}")
                return presence_type
        else:
            print(f"[-] API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[-] Exception in check_roblox_presence: {e}")
    
    return None


def check_last_online(user_id):
    """Fallback: เช็คว่าออนไลน์หรือไม่ผ่าน Users API"""
    url = f"https://users.roblox.com/v1/users/{user_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"[DEBUG] Users API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[DEBUG] User data: {data}")
            
            # เช็คว่ามี lastOnline หรือเปล่า (ถ้าเป็น recent = กำลังออนไลน์)
            if "created" in data:  # API ตอบกลับมาปกติ
                return True  # อย่างน้อย user exists
    except Exception as e:
        print(f"[-] Exception in check_last_online: {e}")
    
    return False


def send_discord_notification(webhook_url, status_code):
    status_map = {
        0: "⚫ ออฟไลน์ (Offline)",
        1: "🟢 ออนไลน์บนเว็บ (Online)",
        2: "🎮 กำลังเล่นเกม (In Game)",
        3: "🛠️ กำลังใช้ Studio (In Studio)",
        99: "✅ User Exists (fallback check)",
    }
    status_text = status_map.get(status_code, f"❓ Unknown ({status_code})")

    payload = {
        "username": "Roblox Tracker",
        "avatar_url": "https://images.rbxcdn.com/251325146c6e737bd3297a760c4fb62c.png",
        "embeds": [
            {
                "title": "🔔 Roblox Status Update",
                "description": (
                    f"ผู้ใช้ ID: **{ROBLOX_USER_ID}**\n"
                    f"สถานะ: **{status_text}**\n\n"
                    f"[ดูโปรไฟล์](https://www.roblox.com/users/{ROBLOX_USER_ID}/profile)"
                ),
                "color": 3066993 if status_code > 0 else 10197915,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        print(f"[+] Discord notification sent! (Status: {resp.status_code})")
    except Exception as e:
        print(f"[-] Discord webhook error: {e}")


def main():
    print(f"[+] Tracking user ID: {ROBLOX_USER_ID} | Interval: {CHECK_INTERVAL}s")
    print(f"[+] Discord Webhook: {DISCORD_WEBHOOK_URL[:50]}...")
    
    last_status = None
    first_run = True

    while True:
        print("\n" + "="*50)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking...")
        
        # พยายามเช็คด้วย Presence API ก่อน
        current_presence = check_roblox_presence(ROBLOX_USER_ID)
        
        # ถ้า Presence API ไม่ได้ผล → ใช้ fallback
        if current_presence is None:
            print("[!] Presence API failed, trying fallback...")
            user_exists = check_last_online(ROBLOX_USER_ID)
            
            if user_exists and first_run:
                print("[+] User found via fallback API")
                send_discord_notification(DISCORD_WEBHOOK_URL, 99)
                first_run = False
        else:
            # มีข้อมูลจาก Presence API
            if current_presence != last_status:
                print(f"[+] Status changed: {last_status} → {current_presence}")
                send_discord_notification(DISCORD_WEBHOOK_URL, current_presence)
                last_status = current_presence
            else:
                print(f"[=] No change (still {current_presence})")
        
        print(f"[.] Sleeping {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

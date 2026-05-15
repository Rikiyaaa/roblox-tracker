import os
import time
import requests

ROBLOX_USER_ID = int(os.environ["ROBLOX_USER_ID"])
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))


def check_roblox_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [user_id]}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("userPresences"):
                return data["userPresences"][0]["userPresenceType"]
        else:
            print(f"[-] Roblox API error (Status: {response.status_code})")
    except Exception as e:
        print(f"[-] Network error: {e}")
    return None


def send_discord_notification(webhook_url, status_code):
    status_map = {
        1: "🟢 กำลังออนไลน์อยู่บนเว็บไซต์ (Online)",
        2: "🎮 กำลังเล่นเกมอยู่ (In Game)",
        3: "🛠️ กำลังพัฒนาเกมใน Studio (In Studio)",
    }
    status_text = status_map.get(status_code, "🟢 ออนไลน์")

    payload = {
        "username": "Roblox Tracker",
        "avatar_url": "https://images.rbxcdn.com/251325146c6e737bd3297a760c4fb62c.png",
        "embeds": [
            {
                "title": "🚨 แจ้งเตือน: เป้าหมายเข้าสู่ระบบแล้ว!",
                "description": (
                    f"ผู้ใช้ ID: **{ROBLOX_USER_ID}** ตอนนี้สถานะ: **{status_text}**\n\n"
                    f"[ดูโปรไฟล์คลิกที่นี่](https://www.roblox.com/users/{ROBLOX_USER_ID}/profile)"
                ),
                "color": 3066993,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
        print("[+] ส่ง Discord notification เรียบร้อย")
    except Exception as e:
        print(f"[-] Discord webhook error: {e}")


def main():
    print(f"[+] Tracking user ID: {ROBLOX_USER_ID} | Interval: {CHECK_INTERVAL}s")
    is_online = False

    while True:
        current_presence = check_roblox_presence(ROBLOX_USER_ID)

        if current_presence is not None:
            if current_presence in [1, 2, 3]:
                if not is_online:
                    print(f"[+] User online! Status: {current_presence}")
                    send_discord_notification(DISCORD_WEBHOOK_URL, current_presence)
                    is_online = True
            else:
                if is_online:
                    print("[-] User went offline")
                is_online = False

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

import os
import time
import requests

ROBLOX_USER_ID = int(os.environ["ROBLOX_USER_ID"])
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))


def check_roblox_presence(user_id):
    """เช็คสถานะผ่าน Presence API"""
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
            
            if "created" in data:
                return True
    except Exception as e:
        print(f"[-] Exception in check_last_online: {e}")
    
    return False


def get_game_info(user_id):
    """ดึงข้อมูลเกมที่กำลังเล่นอยู่"""
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    }
    payload = {"userIds": [user_id]}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("userPresences"):
                presence = data["userPresences"][0]
                
                # ดึง placeId (game ID) และ rootPlaceId
                place_id = presence.get("placeId")
                root_place_id = presence.get("rootPlaceId")
                universe_id = presence.get("universeId")
                
                print(f"[DEBUG] Game IDs - placeId: {place_id}, rootPlaceId: {root_place_id}, universeId: {universe_id}")
                
                # ถ้ามี universeId ให้ดึงชื่อเกม
                if universe_id:
                    game_name = get_game_name(universe_id)
                    if game_name:
                        return {
                            "name": game_name,
                            "universeId": universe_id,
                            "placeId": place_id or root_place_id
                        }
                
                # ถ้าไม่มี universeId แต่มี placeId
                if place_id or root_place_id:
                    return {
                        "name": "Unknown Game",
                        "placeId": place_id or root_place_id
                    }
    except Exception as e:
        print(f"[-] Exception in get_game_info: {e}")
    
    return None


def get_game_name(universe_id):
    """ดึงชื่อเกมจาก universeId"""
    url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"[DEBUG] Game Name API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[DEBUG] Game data: {data}")
            
            if data.get("data") and len(data["data"]) > 0:
                game_name = data["data"][0].get("name", "Unknown Game")
                print(f"[DEBUG] Game name: {game_name}")
                return game_name
    except Exception as e:
        print(f"[-] Exception in get_game_name: {e}")
    
    return None


def send_discord_notification(webhook_url, status_code, game_info=None):
    status_map = {
        0: "⚫ ออฟไลน์ (Offline)",
        1: "🟢 ออนไลน์บนเว็บ (Online)",
        2: "🎮 กำลังเล่นเกม (In Game)",
        3: "🛠️ กำลังใช้ Studio (In Studio)",
        99: "✅ User Exists (fallback check)",
    }
    status_text = status_map.get(status_code, f"❓ Unknown ({status_code})")

    # สร้าง description
    description = f"ผู้ใช้ ID: **{ROBLOX_USER_ID}**\n"
    description += f"สถานะ: **{status_text}**\n"
    
    # 🔥 ถ้ากำลังเล่นเกม (status = 2) แสดงชื่อเกม
    if status_code == 2 and game_info:
        game_name = game_info.get("name", "Unknown Game")
        place_id = game_info.get("placeId")
        universe_id = game_info.get("universeId")
        
        description += f"\n🎮 **กำลังเล่น:** {game_name}\n"
        
        if place_id:
            description += f"[เข้าร่วมเกม](https://www.roblox.com/games/{place_id})\n"
    
    description += f"\n[ดูโปรไฟล์](https://www.roblox.com/users/{ROBLOX_USER_ID}/profile)"

    # 🔥 Ping เฉพาะตอนออนไลน์ (status > 0)
    content = "<@918384557131173988>" if status_code > 0 else None

    payload = {
        "username": "Roblox Tracker",
        "avatar_url": "https://images.rbxcdn.com/251325146c6e737bd3297a760c4fb62c.png",
        "embeds": [
            {
                "title": "🔔 Roblox Status Update",
                "description": description,
                "color": 3066993 if status_code > 0 else 10197915,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
    }
    
    # เพิ่ม content ถ้ามี
    if content:
        payload["content"] = content
    
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
                
                # 🔥 ถ้ากำลังเล่นเกม (status = 2) ให้ดึงข้อมูลเกม
                game_info = None
                if current_presence == 2:
                    print("[+] Player is in game, fetching game info...")
                    game_info = get_game_info(ROBLOX_USER_ID)
                    if game_info:
                        print(f"[+] Game found: {game_info.get('name')}")
                
                send_discord_notification(DISCORD_WEBHOOK_URL, current_presence, game_info)
                last_status = current_presence
            else:
                print(f"[=] No change (still {current_presence})")
        
        print(f"[.] Sleeping {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

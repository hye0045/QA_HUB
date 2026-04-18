import os
import time
import requests
import schedule
from dotenv import load_dotenv

load_dotenv()

QA_HUB_API_URL = os.getenv("QA_HUB_API_URL", "http://localhost:8000/api")
SYNC_USER_EMAIL = os.getenv("SYNC_USER_EMAIL", "admin@thundersoft.com")
SYNC_USER_PASS = os.getenv("SYNC_USER_PASS", "admin123")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

_active_jwt_token = None

def login_to_qahub():
    global _active_jwt_token
    url = f"{QA_HUB_API_URL}/auth/login"
    payload = {"username": SYNC_USER_EMAIL, "password": SYNC_USER_PASS}
    try:
        res = requests.post(url, data=payload)
        res.raise_for_status()
        _active_jwt_token = res.json().get("access_token")
        return True
    except Exception as e:
        print(f"[!] Feishu login to QA_HUB failed: {e}")
        return False

def get_quality_analytics():
    url = f"{QA_HUB_API_URL}/defects/analytics"
    headers = {"Authorization": f"Bearer {_active_jwt_token}"}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 401:
            print("[!] Token expired, re-logging in...")
            login_to_qahub()
            headers = {"Authorization": f"Bearer {_active_jwt_token}"}
            res = requests.get(url, headers=headers)
        return res.json()
    except Exception as e:
        print(f"[!] Failed to get analytics: {e}")
        return None

def send_feishu_notification(data):
    if not FEISHU_WEBHOOK_URL:
        print("[!] No FEISHU_WEBHOOK_URL set. Skipping notification.")
        return

    total = data.get("total", 0)
    by_status = data.get("by_status", [])
    
    # Format message body
    content_text = f"Hôm nay có tổng cộng **{total} Defects** được ghi nhận trên hệ thống QA_HUB.\n\n"
    for st in by_status:
        content_text += f"- Trạng thái [{st['status']}]: {st['count']} lỗi\n"

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🚨 QA HUB Daily Quality Report"
                },
                "template": "red" if total > 10 else "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": content_text,
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "Được gửi tự động từ QA_HUB Sync Service."
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        res = requests.post(FEISHU_WEBHOOK_URL, json=payload)
        if res.status_code == 200:
             print("[+] Gửi thông báo Lệnh Feishu thành công!")
        else:
             print(f"[!] Feishu return error: {res.text}")
    except Exception as e:
         print(f"[!] Could not send to Webhook: {e}")

def job():
    print("[*] Running Scheduled QA Analytics Task...")
    if not _active_jwt_token and not login_to_qahub():
        return
        
    data = get_quality_analytics()
    if data:
        send_feishu_notification(data)

if __name__ == "__main__":
    print("Feishu Quality Notification Service started.")
    print("MOCK: Running job immediately for test...")
    job() # Run once immediately on start
    
    schedule.every().day.at("17:00").do(job) # Lên lịch thật sự gửi báo cáo hàng ngày 5h chiều
    while True:
        schedule.run_pending()
        time.sleep(60)

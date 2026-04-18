import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ================= Configuration =================
# Redmine Config
REDMINE_URL = os.getenv("REDMINE_URL", "http://redmine.thundersoft.com")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "mock_redmine_key_123")
PROJECT_ID = os.getenv("PROJECT_ID", "qa_hub_project")

# QA HUB API Config
QA_HUB_API_URL = os.getenv("QA_HUB_API_URL", "http://localhost:8000/api")
SYNC_USER_EMAIL = os.getenv("SYNC_USER_EMAIL", "admin@thundersoft.com")
SYNC_USER_PASS = os.getenv("SYNC_USER_PASS", "admin123")

# Sync Schedule (in seconds)
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 10))

LAST_SYNC_FILE = "last_sync.txt"
# =================================================

_active_jwt_token = None

def get_last_sync_time():
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, "r") as f:
            return f.read().strip()
    return (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

def update_last_sync_time():
    with open(LAST_SYNC_FILE, "w") as f:
        f.write(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

def login_to_qahub():
    """Tự động đăng nhập lấy JWT token theo OAuth2"""
    global _active_jwt_token
    url = f"{QA_HUB_API_URL}/auth/login"
    payload = {
        "username": SYNC_USER_EMAIL,
        "password": SYNC_USER_PASS
    }
    try:
        res = requests.post(url, data=payload)
        res.raise_for_status()
        _active_jwt_token = res.json().get("access_token")
        print("[+] Logged in to QA_HUB successfully. Acquired Access Token.")
        return True
    except Exception as e:
        print(f"[!] Login failed: {e}")
        return False

def get_auth_headers():
    return {
        "Authorization": f"Bearer {_active_jwt_token}",
        "Content-Type": "application/json"
    }

def fetch_redmine_defects(last_sync):
    """Cào Bugs trực tiếp từ Kyocera Redmine"""
    print(f"[*] Đang cào Defects thực tế từ Redmine: {REDMINE_URL}...")
    url = f"{REDMINE_URL}/issues.json"
    params = {
        "project_id": PROJECT_ID,
        "tracker_id": 38,
        "status_id": "open",
        "sort": "id:desc",
        "limit": 100
    }
    headers = {"X-Redmine-API-Key": REDMINE_API_KEY}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"[!] Lỗi kết nối Redmine API. HTTP {response.status_code}: {response.text}")
            return []
            
        issues = response.json().get("issues", [])
        
        defects = []
        for issue in issues:
            defects.append({
                "redmine_id": issue["id"],
                "title": issue.get("subject", "N/A"),
                "status": issue.get("status", {}).get("name", "new").lower(),
                "severity": issue.get("priority", {}).get("name", "normal").lower(),
                "model_id": "Kyocera Device" # Mặc định hoặc bóc từ custom_fields nếu có
            })
        return defects
    except Exception as e:
        print(f"[!] Error calling Redmine API: {e}")
        return []

def fetch_redmine_specs(last_sync):
    """Giả lập đổ Specifications (Wiki)"""
    print(f"[*] Fetching specs from Redmine updated since {last_sync}...")
    return [] # Bỏ qua mock spec tránh rườm rà console

def push_defects_to_qahub(defects):
    if not defects:
        return
    url = f"{QA_HUB_API_URL}/defects/sync"
    try:
        response = requests.post(url, json=defects, headers=get_auth_headers())
        if response.status_code == 200:
            print(f"[+] Synced {len(defects)} defects successfully to QA HUB!")
        elif response.status_code == 401:
            print("[!] Token expired. Retrying login...")
            if login_to_qahub():
                 requests.post(url, json=defects, headers=get_auth_headers())
        else:
            print(f"[!] Failed to sync defects. HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[!] HTTP Error during pushing defects: {e}")

def run_sync():
    """Main lifecycle"""
    if not _active_jwt_token:
        if not login_to_qahub():
            return
            
    last_sync = get_last_sync_time()
    try:
        # 1. Sync Defects
        defects = fetch_redmine_defects(last_sync)
        if defects:
            push_defects_to_qahub(defects)
        else:
            print("[-] No new defects found.")
            
        update_last_sync_time()
        
    except Exception as e:
        print(f"[!] Sync error: {str(e)}")

if __name__ == "__main__":
    print(f"Starting Secure Redmine -> QA HUB Sync Service (Interval: {SYNC_INTERVAL}s)")
    while True:
        run_sync()
        time.sleep(SYNC_INTERVAL)


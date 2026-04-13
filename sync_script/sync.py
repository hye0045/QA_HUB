import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ================= Configuration =================
# Redmine Config
REDMINE_URL = os.getenv("REDMINE_URL", "http://redmine.thundersoft.com")
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "your_redmine_api_key")
PROJECT_ID = os.getenv("PROJECT_ID", "qa_hub_project")

# QA HUB API Config
QA_HUB_API_URL = os.getenv("QA_HUB_API_URL", "http://localhost:8000/api")
QA_HUB_API_TOKEN = os.getenv("QA_HUB_API_TOKEN", "service_role_or_custom_jwt_token")

# Sync Schedule (in seconds)
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300)) # Default: 5 minutes

# File to store the last sync timestamp
LAST_SYNC_FILE = "last_sync.txt"
# =================================================

def get_last_sync_time():
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, "r") as f:
            return f.read().strip()
    # If no previous sync, sync data from the last 7 days
    return (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

def update_last_sync_time():
    with open(LAST_SYNC_FILE, "w") as f:
        # Save current UTC time
        f.write(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

def fetch_redmine_defects(last_sync):
    print(f"[*] Fetching defects from Redmine updated since {last_sync}...")
    url = f"{REDMINE_URL}/issues.json"
    params = {
        "project_id": PROJECT_ID,
        "updated_on": f">={last_sync}",
        "status_id": "*", # All statuses
        "limit": 100
    }
    headers = {"X-Redmine-API-Key": REDMINE_API_KEY}
    
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        print(f"[!] Warning: Failed to fetch defects. HTTP {response.status_code}")
        return []
    
    issues = response.json().get("issues", [])
    
    defects = []
    for issue in issues:
        defects.append({
            "redmine_id": issue["id"],
            "title": issue["subject"],
            "status": issue["status"]["name"].lower(),
            "severity": issue.get("priority", {}).get("name", "normal").lower(),
            "model_id": "Unknown" # Extract this from custom_fields if available in Redmine
        })
    return defects

def fetch_redmine_specs(last_sync):
    """
    Kéo các trang Wiki từ Redmine làm Specification.
    Redmine Wiki API: GET /projects/[project_id]/wiki/index.json trả về danh sách
    Sau đó GET chi tiết từng trang bị thay đổi.
    """
    print(f"[*] Fetching specs from Redmine updated since {last_sync}...")
    
    # Lấy danh sách toàn bộ các trang Wiki trong Project
    index_url = f"{REDMINE_URL}/projects/{PROJECT_ID}/wiki/index.json"
    headers = {"X-Redmine-API-Key": REDMINE_API_KEY}
    
    try:
        res = requests.get(index_url, headers=headers)
        if res.status_code != 200:
            print(f"[!] Lỗi khi lấy danh sách Wiki: HTTP {res.status_code}")
            return []
            
        wiki_pages = res.json().get("wiki_pages", [])
        
        # Lọc ra những trang có ngày cập nhật (updated_on) lớn hơn last_sync
        updated_pages = []
        last_sync_dt = datetime.strptime(last_sync, "%Y-%m-%dT%H:%M:%SZ")
        
        for p in wiki_pages:
            updated_on_str = p.get("updated_on", "")
            if updated_on_str:
                # Format của Redmine: "2024-03-25T08:00:00Z"
                updated_dt = datetime.strptime(updated_on_str, "%Y-%m-%dT%H:%M:%SZ")
                if updated_dt >= last_sync_dt:
                    updated_pages.append(p)
                    
        specs = []
        # Tải chi tiết nội dung (content) của từng trang đã được lọc
        for page in updated_pages:
            title = page["title"]
            detail_url = f"{REDMINE_URL}/projects/{PROJECT_ID}/wiki/{title}.json"
            detail_res = requests.get(detail_url, headers=headers)
            
            if detail_res.status_code == 200:
                wiki_data = detail_res.json().get("wiki_page", {})
                content = wiki_data.get("text", "")
                version = wiki_data.get("version", 1)
                
                # Cấu trúc JSON gửi về QA HUB Backend
                specs.append({
                    "title": title,
                    "language": "EN", # Tạm thời set gốc là EN, QA HUB sẽ tự xử lý hoặc nhận dạng
                    "content": content,
                    "version_number": version
                })
                
        return specs
        
    except Exception as e:
        print(f"[!] Lỗi kết nối khi đồng bộ Spec: {str(e)}")
        return []

def push_defects_to_qahub(defects):
    if not defects:
        return
    print(f"[*] Pushing {len(defects)} defects to QA HUB...")
    url = f"{QA_HUB_API_URL}/defects/sync"
    headers = {
        "Authorization": f"Bearer {QA_HUB_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=defects, headers=headers)
    if response.status_code == 200:
        print("[+] Defects synced successfully!")
    else:
        print(f"[!] Failed to sync defects to QA HUB. HTTP {response.status_code}: {response.text}")

def push_spec_to_qahub(spec):
    print(f"[*] Pushing spec '{spec['title']}' to QA HUB...")
    url = f"{QA_HUB_API_URL}/specs/sync"
    headers = {
        "Authorization": f"Bearer {QA_HUB_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=spec, headers=headers)
    if response.status_code == 200:
        print("[+] Spec synced successfully!")
    else:
        print(f"[!] Failed to sync spec. HTTP {response.status_code}: {response.text}")

def run_sync():
    last_sync = get_last_sync_time()
    
    try:
        # 1. Sync Defects
        defects = fetch_redmine_defects(last_sync)
        if defects:
            push_defects_to_qahub(defects)
        else:
            print("[-] No new defects found.")
            
        # 2. Sync Specs
        specs = fetch_redmine_specs(last_sync)
        for spec in specs:
             push_spec_to_qahub(spec)
             
        # Update timestamp after successful sync
        update_last_sync_time()
        
    except Exception as e:
        print(f"[!] Sync error: {str(e)}")

if __name__ == "__main__":
    print(f"Starting Redmine -> QA HUB Sync Service (Interval: {SYNC_INTERVAL}s)")
    while True:
        run_sync()
        print(f"Sleeping for {SYNC_INTERVAL} seconds...\n")
        time.sleep(SYNC_INTERVAL)

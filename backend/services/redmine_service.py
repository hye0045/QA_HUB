import httpx
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedmineClient:
    def __init__(self):
        self.base_url = settings.REDMINE_URL
        self.api_key = settings.REDMINE_API_KEY
    
    async def fetch_issues(self, project_id: str, tracker_id: int = 38):
        """
        Asynchronously fetches open issues from Redmine for a specific project.
        """
        endpoint = f"{self.base_url}/issues.json"
        
        params = {
            "project_id": project_id,
            "tracker_id": tracker_id,
            "status_id": "open",
            "sort": "id:desc",
            "limit": 100
        }
        
        headers = {
            "X-Redmine-API-Key": self.api_key
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                
                data = response.json()
                issues = data.get("issues", [])
                
                # Chuẩn hóa cấu trúc list of dicts tương tự mô hình db_models.
                defects = []
                for issue in issues:
                    defects.append({
                        "redmine_id": issue["id"],
                        "title": issue.get("subject", "N/A"),
                        "description": issue.get("description", ""),
                        "status": issue.get("status", {}).get("name", "new").lower(),
                        "severity": issue.get("priority", {}).get("name", "normal").lower(),
                        "model_id": "Kyocera Device" # Mặc định hoặc bóc từ log tùy ý
                    })
                return defects
            except httpx.HTTPStatusError as e:
                logger.error(f"Redmine API HTTP Error: {e.response.status_code}")
                return []
            except Exception as e:
                logger.error(f"Redmine Error: {str(e)}")
                return []

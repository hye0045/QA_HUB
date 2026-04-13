from fastapi import Request, HTTPException, status, Depends
from core.security import get_current_user
from db.supabase_client import supabase
import datetime

# Limits per role per day for fetching testcases (example)
RATE_LIMITS = {
    "intern": 10,
    "tester": 30,
    "qa_lead": 1000, # Effectively unlimited
    "admin": 1000
}

def check_rate_limit(endpoint: str = "fetch_testcase"):
    def rate_limit_checker(request: Request, current_user: dict = Depends(get_current_user)):
        user_id = current_user['id']
        role = current_user['role']
        limit = RATE_LIMITS.get(role, 10)
        
        # We could bypass if it is an urgent project, but that requires more context.
        # For simplicity, if role is qa_lead or admin, they bypass
        if role in ["qa_lead", "admin"]:
            return current_user
            
        # Get today's logs for this user and endpoint
        today = datetime.datetime.now().date().isoformat()
        
        logs = supabase.table('access_log') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .eq('endpoint', endpoint) \
            .gte('accessed_at', today) \
            .execute()
        
        count = logs.count if logs.count else 0
        
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for endpoint '{endpoint}'. Max {limit} requests per day."
            )
        
        # Log this access
        supabase.table('access_log').insert({
            "user_id": user_id,
            "endpoint": endpoint
        }).execute()
        
        return current_user
    return rate_limit_checker

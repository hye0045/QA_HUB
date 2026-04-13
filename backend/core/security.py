from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.supabase_client import supabase
from typing import Dict, Any, List

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        # Verify JWT with Supabase Auth
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Get custom claims or fetch from public.users to get the role
        # Here we query public.users table to get RBAC role
        user_id = user.user.id
        user_record = supabase.table('users').select('*').eq('id', user_id).single().execute()
        
        if not user_record.data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in system")
            
        return user_record.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        if current_user.get('role') not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

# Pre-defined dependencies
require_admin = require_roles(["admin"])
require_qa_lead = require_roles(["admin", "qa_lead"])
require_tester = require_roles(["admin", "qa_lead", "tester"])

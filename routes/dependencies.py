from typing import Optional
from fastapi import Request, HTTPException
import os

def get_current_user(request: Request) -> Optional[dict]:
    return request.session.get("user")

def require_auth(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        # 使用 303 Redirect 到 /login（保留你原本的行為）
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    return "".join(
        c if c.isalnum() or c in (' ', '.', '_', '-') else '_'
        for c in name
    ).replace(' ', '_')
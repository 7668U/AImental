# router/auth.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid  # 确保导入 uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# --- 安全配置 ---
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be configured with at least 32 characters.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

# --- 【新增】Token黑名单 ---
# 在真实项目中，这里应该用Redis或数据库。为简化，我们先用一个全局集合来模拟。
# 注意：这种内存中的黑名单在服务重启后会丢失，不适用于生产环境！
TOKEN_DENYLIST = set()

# --- Token 创建函数 ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """根据用户信息创建一个JWT Token，并包含一个唯一的jti"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4())  # 为每个token添加一个唯一的ID
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 真实的认证依赖项 ---
def get_authenticated_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Decode and validate a JWT without applying privacy-consent gating."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # **【新增】**：检查token是否在黑名单中
        jti = payload.get("jti")
        if jti is None or jti in TOKEN_DENYLIST:
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    return user_id


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """Validate the token and require the current privacy policy consent."""
    user_id = get_authenticated_user_id(token)

    # Late import avoids a model/router import cycle during application startup.
    from model.user import user_table
    from privacy_policy import PRIVACY_POLICY_VERSION

    if not user_table.has_current_privacy_consent(user_id):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "privacy_consent_required",
                "message": "Please review and accept the current privacy policy.",
                "privacy_policy_version": PRIVACY_POLICY_VERSION,
            },
        )
    return user_id

# router/auth.py

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid  # 确保导入 uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# --- 安全配置 ---
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_secret_and_long_random_string_for_jwt")
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
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    解码JWT Token，验证并返回用户ID。
    新增了黑名单检查。
    """
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
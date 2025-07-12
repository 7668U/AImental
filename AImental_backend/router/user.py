# routers/user.py

# 1. 导入所有需要的模块
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Header
from pydantic import BaseModel
from typing import Optional
import os
import requests
from jose import jwt, JWTError

# 2. 从项目其他文件中导入
from db import user_db
from model.user import User, user_table, UserModel
# **重要**：确保从 auth.py 导入所有需要的工具，包括黑名单
from .auth import create_access_token, get_current_user_id, TOKEN_DENYLIST 

# ---------------------------------------------------
# Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/users",
    tags=["Users - 用户管理"],
)

# ---------------------------------------------------
# Pydantic Models
# ---------------------------------------------------
class UserLoginRequest(BaseModel):
    """用户登录请求体"""
    code: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class TokenResponse(BaseModel):
    """Token响应体"""
    access_token: str
    token_type: str = "bearer"

class AvatarUpdateResponse(BaseModel):
    """头像更新响应体"""
    message: str
    new_avatar_url: str

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------

# --- 从环境变量或配置文件中读取敏感信息 (已根据你的日志填入) ---
APP_ID = os.getenv("WECHAT_APP_ID", "wxd90fc334d65b9a0a")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "ea616af4afb747c84fcaf18119bd11ef")

@router.post("/login", response_model=TokenResponse, summary="微信小程序登录")
def wechat_login(login_data: UserLoginRequest):
    """
    处理微信登录请求，code换取openid，创建或登录用户，并返回JWT
    """
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={APP_ID}&secret={APP_SECRET}&js_code={login_data.code}&grant_type=authorization_code"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"请求微信服务器失败: {e}")

    openid = data.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail=data.get("errmsg", "获取 openid 失败"))

    user = user_table.get_user_by_openid(openid)
    if not user:
        user = user_table.create_user(
            openid=openid,
            nickname=login_data.nickname or "微信用户",
            avatar_url=login_data.avatar_url or ""
        )

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token}


@router.get("/me", response_model=UserModel, summary="获取当前用户信息")
def get_current_user_info(current_user_id: str = Depends(get_current_user_id)):
    """
    使用真实的Token认证，获取当前登录用户的信息
    """
    user = user_table.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/me/avatar", response_model=AvatarUpdateResponse, summary="更新当前用户头像")
def update_current_user_avatar(
    current_user_id: str = Depends(get_current_user_id),
    image: UploadFile = File(...)
):
    """
    更新当前用户的头像。前端必须使用 POST 方法上传图片。
    """
    new_path = user_table.update_avatar(user_id=current_user_id, image_file=image)
    if not new_path:
        raise HTTPException(
            status_code=404, 
            detail="User not found or file could not be saved."
        )
    return AvatarUpdateResponse(
        message="Avatar updated successfully",
        new_avatar_url=new_path
    )


@router.post("/logout", summary="用户退出登录（Token加入黑名单）")
def logout(authorization: str = Header(...)):
    """
    将当前用户的token加入黑名单，实现真正的服务端登出。
    """
    try:
        # 从 "Bearer <token>" 中提取 token
        token = authorization.split(" ")[1]
        # 解码以获取jti
        payload = jwt.decode(token, os.getenv("SECRET_KEY", "a_very_secret_and_long_random_string_for_jwt"), algorithms=["HS256"], options={"verify_signature": False})
        jti = payload.get("jti")
        if jti:
            TOKEN_DENYLIST.add(jti)
    except (JWTError, IndexError):
        # 即使token有问题，也让前端认为登出成功，不报错
        pass
    return {"message": "Successfully logged out"}

# **【重要】** 此处已删除了所有其他重复的、用来占位的函数和模型，比如多余的 get_current_user_id 和 UserCreateForm。
# routers/user.py

# 1. 导入所有需要的模块
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Header
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
import os
import requests
from jose import jwt, JWTError

# 2. 从项目其他文件中导入
from db import user_db
from model.user import User, user_table, UserModel
from .auth import create_access_token, get_current_user_id, TOKEN_DENYLIST 

# ---------------------------------------------------
# Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/users",
    tags=["Users - 用户管理"],
)

# ---------------------------------------------------
# Pydantic Models (已更新)
# ---------------------------------------------------
class UserLoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AvatarUpdateResponse(BaseModel):
    message: str
    new_avatar_url: str

class UserInfoUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    gender: Optional[int] = Field(None, ge=0, le=2, description="0: 未知, 1: 男, 2: 女")
    birthday: Optional[date] = None

class UserInfoResponse(BaseModel):
    nickname: Optional[str]
    gender: Optional[int]
    birthday: Optional[date]

# --- 【新增模型】 ---
class UserSettingsRequest(BaseModel):
    """更新用户设置的请求体"""
    allow_ai_read_data: bool
# --- ----------- ---


# ---------------------------------------------------
# API Endpoints (已更新)
# ---------------------------------------------------

APP_ID = os.getenv("WECHAT_APP_ID", "wx87018ae3626d4acb")
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "b79008d89825b2065ad3c7bc305133ed")


def create_test_login_token(user_id_for_test: str = "local-dev-user"):
    user, created = User.get_or_create(
        id=user_id_for_test,
        defaults={
            'openid': f"test_openid_{user_id_for_test}",
            'nickname': f"test-user-{user_id_for_test[:6]}",
            'avatar_url': ""
        }
    )
    if created:
        print(f"Created local test user: {user_id_for_test}")

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token}


@router.post("/login", response_model=TokenResponse, summary="微信小程序登录")
def wechat_login(login_data: UserLoginRequest):
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={APP_ID}&secret={APP_SECRET}&js_code={login_data.code}&grant_type=authorization_code"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"请求微信服务器失败: {e}")

    openid = data.get("openid")
    if not openid:
        if os.getenv("ALLOW_LOCAL_DEV_LOGIN", "1") == "1":
            print(f"WeChat login failed in local development, falling back to test login: {data}")
            return create_test_login_token()
        raise HTTPException(status_code=400, detail=data.get("errmsg", "获取 openid 失败"))

    user = user_table.get_user_by_openid(openid)
    if not user:
        user = user_table.create_user(
            openid=openid,
            nickname=login_data.nickname or "微信用户",
            avatar_url=login_data.avatar_url or ""
        )
    user.last_login_at = date.today()
    user.save()

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token}


@router.get("/me", response_model=UserModel, summary="获取当前用户信息(完整)")
def get_current_user_info(current_user_id: str = Depends(get_current_user_id)):
    """
    使用真实的Token认证，获取当前登录用户的**所有**信息
    (已包含个性化对话设置)
    """
    user = user_table.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/info", response_model=UserInfoResponse, summary="获取用户基本信息(昵称/性别/生日)")
def get_user_basic_info(current_user_id: str = Depends(get_current_user_id)):
    user = user_table.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserInfoResponse(
        nickname=user.nickname,
        gender=user.gender,
        birthday=user.birthday
    )

@router.put("/me/info", summary="补充或更新用户基本信息")
def update_user_info(
    info_data: UserInfoUpdateRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    success = user_table.update_user_info(
        user_id=current_user_id,
        nickname=info_data.nickname,
        gender=info_data.gender,
        birthday=info_data.birthday
    )
    if not success:
        raise HTTPException(status_code=404, detail="User not found or update failed")
    
    return {"message": "User information updated successfully"}


# --- 【新增接口】 ---
@router.put("/me/settings", summary="更新用户个性化对话设置")
def update_user_settings(
    settings: UserSettingsRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新用户是否允许AI读取其个人数据以进行个性化对话的设置。
    """
    success = user_table.update_ai_read_permission(
        user_id=current_user_id,
        allow=settings.allow_ai_read_data
    )
    if not success:
        # 这个错误理论上很难触发，因为 current_user_id 来自有效的 token
        raise HTTPException(status_code=404, detail="User not found or update failed")
    
    return {"message": "Settings updated successfully"}


@router.post("/me/avatar", response_model=AvatarUpdateResponse, summary="更新当前用户头像")
def update_current_user_avatar(
    current_user_id: str = Depends(get_current_user_id),
    image: UploadFile = File(...)
):
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
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, os.getenv("SECRET_KEY", "a_very_secret_and_long_random_string_for_jwt"), algorithms=["HS256"], options={"verify_signature": False})
        jti = payload.get("jti")
        if jti:
            TOKEN_DENYLIST.add(jti)
    except (JWTError, IndexError):
        pass
    return {"message": "Successfully logged out"}

# ---------------------------------------------------
# Database Connection Management
# ---------------------------------------------------
@router.on_event("startup")
def startup():
    if user_db.is_closed():
        user_db.connect()

@router.on_event("shutdown")
def shutdown():
    if not user_db.is_closed():
        user_db.close()


class TestUserLoginRequest(BaseModel):
    """仅用于测试登录的请求体"""
    user_id: str = Field(..., description="用于测试的任意用户ID")
    
@router.post("/login/test", response_model=TokenResponse, summary="【仅供测试】使用任意ID登录")
def test_login(login_data: TestUserLoginRequest):
    """
    一个专为开发和测试设置的后门登录接口。
    它会根据提供的 user_id 查找用户，如果用户不存在则自动创建，
    然后直接签发一个有效的JWT Token。
    【警告】这个接口绝对不能部署到生产环境！
    """
    user_id_for_test = login_data.user_id
    
    # 在 Peewee 中，我们通常用 get_or_none 来安全地获取对象
    # 假设 user_table 中有 get_user_by_id 方法
    # 注意：这里的 user_id 可能是你数据库中的自增主键或UUID，
    # 我们这里简化为直接使用前端传来的字符串作为用户的唯一标识来查找或创建。
    # 更好的做法是查找或创建一个user，然后用user的真实db_id来生成token。
    
    # 查找用户，如果不存在则创建一个新用户用于测试
    user, created = User.get_or_create(
        id=user_id_for_test, 
        defaults={
            'openid': f"test_openid_{user_id_for_test}",
            'nickname': f"测试用户-{user_id_for_test[:6]}",
            'avatar_url': ""
        }
    )
    if created:
        print(f"为测试创建了新用户: {user_id_for_test}")
    
    # 使用与微信登录相同的函数来创建Token，确保Token格式一致
    # Token的'sub'字段（主体）应该是用户的唯一数据库ID
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token}


@router.put("/me/unlock-community", summary="【新】用户分享后，解锁社区全部角色")
def unlock_community_for_user(current_user_id: str = Depends(get_current_user_id)):
    """
    这个接口在用户首次分享成功后被前端调用一次。
    它的作用就是把用户的 'has_unlocked_community' 标志位永久设为 True。
    """
    rows_updated = (User
                    .update({User.has_unlocked_community: True})
                    .where(User.id == current_user_id)
                    .execute())

    if rows_updated == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"message": "社区已成功解锁!"}

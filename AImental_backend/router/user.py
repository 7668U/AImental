# routers/user.py

# 1. 导入所有需要的模块
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Header
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
import os
import requests
from jose import jwt, JWTError

# 2. 从项目其他文件中导入
from db import user_db
from feature_flags import ENABLE_COMMUNITY_BACKEND
from model.user import User, user_table, UserModel
from privacy_policy import (
    PRIVACY_POLICY_VERSION,
    get_privacy_policy,
    get_privacy_policy_digest,
    validate_policy_version,
)
from .auth import (
    ALGORITHM,
    SECRET_KEY,
    TOKEN_DENYLIST,
    create_access_token,
    get_authenticated_user_id,
    get_current_user_id,
)

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
    privacy_consent_agreed: bool = False
    privacy_policy_version: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    privacy_policy_version: str = PRIVACY_POLICY_VERSION

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


class PrivacyConsentRequest(BaseModel):
    privacy_consent_agreed: bool
    privacy_policy_version: str
    source: str = Field(default="mini_program_privacy_modal", max_length=64)


# ---------------------------------------------------
# API Endpoints (已更新)
# ---------------------------------------------------

APP_ID = os.getenv("WECHAT_APP_ID", "").strip()
APP_SECRET = os.getenv("WECHAT_APP_SECRET", "").strip()


def require_current_privacy_consent(agreed: bool, policy_version: Optional[str]):
    if not agreed or not validate_policy_version(policy_version or ""):
        raise HTTPException(
            status_code=428,
            detail={
                "code": "privacy_consent_required",
                "message": "请先阅读并同意当前版本的用户隐私保护协议。",
                "privacy_policy_version": PRIVACY_POLICY_VERSION,
                "privacy_policy_digest": get_privacy_policy_digest(),
            },
        )


def issue_login_token(user: User, source: str) -> dict:
    if not user_table.accept_privacy_consent(
        user.id,
        PRIVACY_POLICY_VERSION,
        source,
    ):
        raise HTTPException(status_code=500, detail="Could not record privacy consent.")
    user.last_login_at = datetime.now()
    user.save(only=[User.last_login_at])
    access_token = create_access_token(data={"sub": user.id})
    return {
        "access_token": access_token,
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
    }


def create_test_login_token(
    user_id_for_test: str = "local-dev-user",
    *,
    privacy_consent_agreed: bool,
    privacy_policy_version: Optional[str],
):
    require_current_privacy_consent(
        privacy_consent_agreed,
        privacy_policy_version,
    )
    user, created = user_table.get_or_create_test_user(user_id_for_test)
    if created:
        print(f"Created local test user: {user_id_for_test}")
    user_table.update_wechat_session_key(
        user.id,
        f"local-session-key-{user.id}",
    )
    return issue_login_token(user, "local_test_login")


@router.get("/privacy-policy", summary="获取当前用户隐私保护协议")
def get_current_privacy_policy():
    policy = get_privacy_policy()
    policy["digest"] = get_privacy_policy_digest()
    return policy


@router.post("/login", response_model=TokenResponse, summary="微信小程序登录")
def wechat_login(login_data: UserLoginRequest):
    require_current_privacy_consent(
        login_data.privacy_consent_agreed,
        login_data.privacy_policy_version,
    )
    if not APP_ID or not APP_SECRET:
        if os.getenv("ALLOW_LOCAL_DEV_LOGIN", "1") == "1":
            print("WeChat login config is missing, falling back to local test login.")
            return create_test_login_token(
                privacy_consent_agreed=login_data.privacy_consent_agreed,
                privacy_policy_version=login_data.privacy_policy_version,
            )
        raise HTTPException(status_code=500, detail="WeChat login configuration is missing")

    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={APP_ID}&secret={APP_SECRET}&js_code={login_data.code}&grant_type=authorization_code"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"请求微信服务器失败: {e}")

    openid = data.get("openid")
    session_key = data.get("session_key")
    if not openid:
        if os.getenv("ALLOW_LOCAL_DEV_LOGIN", "1") == "1":
            print(f"WeChat login failed in local development, falling back to test login: {data}")
            return create_test_login_token(
                privacy_consent_agreed=login_data.privacy_consent_agreed,
                privacy_policy_version=login_data.privacy_policy_version,
            )
        raise HTTPException(status_code=400, detail=data.get("errmsg", "获取 openid 失败"))

    user = user_table.get_user_by_openid(openid)
    if not user:
        user = user_table.create_user(
            openid=openid,
            nickname=login_data.nickname or "微信用户",
            avatar_url=login_data.avatar_url or ""
        )
    user_table.update_wechat_session_key(user.id, session_key)
    return issue_login_token(user, "mini_program_login")


@router.get("/me", response_model=UserModel, summary="获取当前用户信息(完整)")
def get_current_user_info(current_user_id: str = Depends(get_current_user_id)):
    """
    使用真实的Token认证，获取当前登录用户的**所有**信息
    (已包含个性化对话设置)
    """
    user = user_table.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_table.serialize_user(user)


@router.get("/me/privacy-consent", summary="获取当前用户的隐私同意状态")
def get_my_privacy_consent(
    current_user_id: str = Depends(get_authenticated_user_id),
):
    user = user_table.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "is_current": user_table.has_current_privacy_consent(current_user_id),
        "accepted_version": user.privacy_consent_version,
        "current_version": PRIVACY_POLICY_VERSION,
        "consented_at": user.privacy_consented_at,
        "withdrawn_at": user.privacy_consent_withdrawn_at,
    }


@router.put("/me/privacy-consent", summary="同意当前版本的隐私协议")
def accept_my_privacy_consent(
    payload: PrivacyConsentRequest,
    current_user_id: str = Depends(get_authenticated_user_id),
):
    require_current_privacy_consent(
        payload.privacy_consent_agreed,
        payload.privacy_policy_version,
    )
    if not user_table.accept_privacy_consent(
        current_user_id,
        payload.privacy_policy_version,
        payload.source,
    ):
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "message": "Privacy consent recorded.",
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
    }


@router.delete("/me/privacy-consent", summary="撤回隐私同意")
def withdraw_my_privacy_consent(
    current_user_id: str = Depends(get_authenticated_user_id),
):
    if not user_table.withdraw_privacy_consent(
        current_user_id,
        "mini_program_privacy_settings",
    ):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Privacy consent withdrawn."}


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
    privacy_consent_agreed: bool = False
    privacy_policy_version: Optional[str] = None
    
@router.post("/login/test", response_model=TokenResponse, summary="【仅供测试】使用任意ID登录")
def test_login(login_data: TestUserLoginRequest):
    """
    一个专为开发和测试设置的后门登录接口。
    它会根据提供的 user_id 查找用户，如果用户不存在则自动创建，
    然后直接签发一个有效的JWT Token。
    【警告】这个接口绝对不能部署到生产环境！
    """
    user_id_for_test = login_data.user_id
    return create_test_login_token(
        user_id_for_test,
        privacy_consent_agreed=login_data.privacy_consent_agreed,
        privacy_policy_version=login_data.privacy_policy_version,
    )


@router.put("/me/unlock-community", summary="【新】用户分享后，解锁社区全部角色")
def unlock_community_for_user(current_user_id: str = Depends(get_current_user_id)):
    """
    这个接口在用户首次分享成功后被前端调用一次。
    它的作用就是把用户的 'has_unlocked_community' 标志位永久设为 True。
    """
    if not ENABLE_COMMUNITY_BACKEND:
        raise HTTPException(status_code=503, detail="心灵社区模块已暂时下线")

    rows_updated = (User
                    .update({User.has_unlocked_community: True})
                    .where(User.id == current_user_id)
                    .execute())

    if rows_updated == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"message": "社区已成功解锁!"}

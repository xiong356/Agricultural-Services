"""
auth_service.py
用户认证服务 — 注册 / 登录 / JWT 令牌管理

功能:
  1. 用户注册（手机号 + 密码 + 姓名）
  2. 用户登录（手机号 + 密码 → JWT 令牌）
  3. JWT 令牌签发与验证
  4. 密码 bcrypt 加密
  5. 当前用户获取（从 JWT 解析）

使用方式:
  from auth_service import register_user, login_user, get_current_user, verify_token
"""

import os
import time
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_db, Session, User
from logger import get_logger

logger = get_logger(__name__)

# ============================================================
# JWT 配置
# ============================================================

_env_path = os.path.join(os.path.dirname(__file__), ".env")
_jwt_secret = os.getenv("JWT_SECRET", "")
if not _jwt_secret:
    def _load_jwt_secret():
        if os.path.exists(_env_path):
            with open(_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("JWT_SECRET="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        return ""
    _jwt_secret = _load_jwt_secret()

# 默认密钥（开发环境用，生产环境必须在 .env 中设置 JWT_SECRET）
if not _jwt_secret:
    _jwt_secret = "CHANGE-ME-dev-secret"
    logger.warning("未配置 JWT_SECRET，使用默认开发密钥。生产环境请在 .env 中设置 JWT_SECRET")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24           # Access Token 有效期
JWT_REFRESH_EXPIRE_DAYS = 30    # Refresh Token 有效期


# ============================================================
# 密码加密
# ============================================================

def hash_password(password: str) -> str:
    """bcrypt 加密密码"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ============================================================
# JWT 令牌
# ============================================================

def create_access_token(user_id: int, phone: str) -> str:
    """签发 Access Token"""
    payload = {
        "sub": str(user_id),
        "phone": phone,
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, _jwt_secret, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """签发 Refresh Token"""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_REFRESH_EXPIRE_DAYS * 86400,
    }
    return jwt.encode(payload, _jwt_secret, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """
    验证 JWT 令牌

    Returns:
        payload dict 如果验证成功, None 如果失败
    """
    try:
        payload = jwt.decode(token, _jwt_secret, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT 令牌已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT 令牌无效: {e}")
        return None


# ============================================================
# 注册 / 登录
# ============================================================

def register_user(db: Session, phone: str, password: str, name: str, village: str = "") -> dict:
    """
    用户注册

    Args:
        db: 数据库会话
        phone: 手机号
        password: 明文密码
        name: 姓名
        village: 村庄（可选）

    Returns:
        用户信息 + 令牌

    Raises:
        ValueError: 手机号已注册
    """
    # 检查手机号是否已注册
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise ValueError("该手机号已注册")

    # 创建用户
    user = User(
        phone=phone,
        password_hash=hash_password(password),
        name=name,
        village=village,
        role="farmer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"用户注册成功: phone={phone}, name={name}, user_id={user.id}")

    return _build_auth_response(user)


def login_user(db: Session, phone: str, password: str) -> dict:
    """
    用户登录

    Args:
        db: 数据库会话
        phone: 手机号
        password: 明文密码

    Returns:
        用户信息 + 令牌

    Raises:
        ValueError: 手机号或密码错误
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise ValueError("手机号或密码错误")

    if not verify_password(password, user.password_hash):
        logger.warning(f"登录密码错误: phone={phone}")
        raise ValueError("手机号或密码错误")

    logger.info(f"用户登录成功: phone={phone}, user_id={user.id}")

    return _build_auth_response(user)


def _build_auth_response(user: User) -> dict:
    """构建认证响应（用户信息 + 令牌）"""
    return {
        "access_token": create_access_token(user.id, user.phone),
        "refresh_token": create_refresh_token(user.id),
        "expires_in": JWT_EXPIRE_HOURS * 3600,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "name": user.name,
            "village": user.village or "",
            "avatar": user.avatar or "",
            "role": user.role,
        }
    }


# ============================================================
# FastAPI 认证依赖
# ============================================================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI 依赖: 从请求头提取 JWT 并返回当前用户

    使用方式:
        @app.get("/profile")
        async def profile(current_user: User = Depends(get_current_user)):
            return {"name": current_user.name}
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="令牌类型错误")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    可选认证: 不强制要求登录，但如果提供了令牌则返回用户

    用于兼容现有接口（有 token 则返回用户数据，无 token 则返回 mock 数据）
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    payload = verify_token(token)

    if not payload or payload.get("type") != "access":
        return None

    user_id = int(payload["sub"])
    return db.query(User).filter(User.id == user_id).first()

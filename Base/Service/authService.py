import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt

from Base.Config.setting import settings
from Base.Models.userModel import UserModel
from Base.Models.userTokenModel import UserTokenModel


class AuthService:
    """
    用户认证服务：注册、登录、Token 签发与校验。
    密码使用 argon2 哈希，Token 使用 JWT。
    """

    @staticmethod
    def hash_password(password: str) -> str:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        return ph.hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        from argon2 import PasswordHasher, exceptions
        ph = PasswordHasher()
        try:
            return ph.verify(password_hash, password)
        except exceptions.VerifyMismatchError:
            return False

    @staticmethod
    def _create_jwt(payload: dict, expires_delta: timedelta) -> str:
        now = datetime.utcnow()
        to_encode = payload.copy()
        to_encode.update({"exp": now + expires_delta, "iat": now})
        return jwt.encode(
            to_encode,
            settings.auth.jwt_secret or "fallback-secret-change-in-env",
            algorithm=settings.auth.jwt_algorithm,
        )

    @classmethod
    def create_access_token(cls, user_id: int, source_module: str) -> str:
        return cls._create_jwt(
            payload={"sub": str(user_id), "source_module": source_module, "type": "access"},
            expires_delta=timedelta(minutes=settings.auth.access_token_expire_minutes),
        )

    @classmethod
    def create_refresh_token(cls, user_id: int, source_module: str) -> str:
        return cls._create_jwt(
            payload={"sub": str(user_id), "source_module": source_module, "type": "refresh"},
            expires_delta=timedelta(days=settings.auth.refresh_token_expire_days),
        )

    @classmethod
    def verify_token(cls, token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token,
                settings.auth.jwt_secret or "fallback-secret-change-in-env",
                algorithms=[settings.auth.jwt_algorithm],
            )
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    @classmethod
    def register(
        cls,
        username: str,
        password: str,
        source_module: str = "default",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> Tuple[bool, Optional[UserModel], str]:
        existing = UserModel.find_by_username(username)
        if existing:
            return False, None, "用户名已存在"

        if email:
            existing_email = UserModel.find_by_email(email)
            if existing_email:
                return False, None, "邮箱已被注册"

        user = UserModel(
            username=username,
            email=email,
            phone=phone,
            password_hash=cls.hash_password(password),
            source_module=source_module,
            extra_data=extra_data,
        )
        user_id = user.save()
        if user_id > 0:
            return True, UserModel.get_by_id(user_id), ""
        return False, None, "注册失败"

    @classmethod
    def login(
        cls, username: str, password: str
    ) -> Tuple[bool, Optional[UserModel], Optional[str], Optional[str], str]:
        user = UserModel.find_by_username(username)
        if not user:
            return False, None, None, None, "用户不存在"

        if user.status != "active":
            return False, user, None, None, "账户已被禁用或未激活"

        if not cls.verify_password(password, user.password_hash):
            return False, user, None, None, "密码错误"

        user.update(last_login_at=datetime.utcnow())
        UserModel.get_by_id(user.id)

        access_token = cls.create_access_token(user.id, user.source_module)
        refresh_token = cls.create_refresh_token(user.id, user.source_module)
        return True, user, access_token, refresh_token, ""

    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Tuple[bool, Optional[str], str]:
        payload = cls.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return False, None, "Token 无效或已过期"

        user_id = int(payload["sub"])
        user = UserModel.get_by_id(user_id)
        if not user or user.status != "active":
            return False, None, "用户不存在或已被禁用"

        new_access_token = cls.create_access_token(user.id, user.source_module)
        return True, new_access_token, ""

    @classmethod
    def get_current_user(cls, access_token: str) -> Optional[UserModel]:
        payload = cls.verify_token(access_token)
        if not payload or payload.get("type") != "access":
            return None
        return UserModel.get_by_id(int(payload["sub"]))

    @classmethod
    def update_user_status(cls, user_id: int, status: str) -> bool:
        user = UserModel.get_by_id(user_id)
        if not user:
            return False
        return user.update(status=status)

    @classmethod
    def soft_delete(cls, user_id: int) -> bool:
        user = UserModel.get_by_id(user_id)
        if not user:
            return False
        return user.update(deleted_at=datetime.utcnow())

    @classmethod
    def change_password(cls, user_id: int, old_password: str, new_password: str) -> str:
        user = UserModel.get_by_id(user_id)
        if not user:
            return "用户不存在"
        if not cls.verify_password(old_password, user.password_hash):
            return "原密码错误"
        user.update(password_hash=cls.hash_password(new_password))
        return ""

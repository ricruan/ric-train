import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

import jwt

from Base.Config.setting import settings
from Base.Models.userModel import UserModel
from Base.Models.roleModel import RoleModel, Permission, BUILTIN_ROLES
from Base.Models.userRoleModel import UserRoleModel

logger = logging.getLogger(__name__)


class AuthService:
    """
    用户认证服务：注册、登录、Token 签发与校验、角色权限管理。

    Superpowers 权限体系:
    - RoleModel: 独立角色表，定义角色名 + 权限列表 (JSON)
    - UserRoleModel: 关联表，用户 ↔ 角色 多对多
    - 用户最终权限 = 所有角色权限的并集
    - 预置角色: super_admin / admin / moderator / user / guest
    - 支持动态创建自定义角色
    """

    # =========================
    # 密码处理
    # =========================

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

    # =========================
    # JWT Token 处理
    # =========================

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

    # =========================
    # 注册 / 登录 / Token 刷新
    # =========================

    @classmethod
    def register(
        cls,
        username: str,
        password: str,
        source_module: str = "default",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        extra_data: Optional[dict] = None,
        role_name: str = "user",
    ) -> Tuple[bool, Optional[UserModel], str]:
        """
        用户注册

        Args:
            role_name: 初始角色名 (默认 "user")
        """
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
            # 自动分配默认角色
            role = RoleModel.find_by_name(role_name, source_module)
            if role:
                UserRoleModel.grant_role(user_id, role.id, source_module)
            return True, user, ""
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

    # =========================
    # 用户状态管理
    # =========================

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
        if len(new_password) < 6:
            return "新密码长度不能少于6位"
        user.update(password_hash=cls.hash_password(new_password))
        return ""

    @classmethod
    def reset_password(cls, user_id: int, new_password: str = "123456") -> str:
        user = UserModel.get_by_id(user_id)
        if not user:
            return "用户不存在"
        if len(new_password) < 6:
            return "密码长度不能少于6位"
        user.update(password_hash=cls.hash_password(new_password))
        return ""

    @classmethod
    def update_profile(
        cls,
        user_id: int,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> Tuple[bool, str]:
        user = UserModel.get_by_id(user_id)
        if not user:
            return False, "用户不存在"

        if email and email != user.email:
            existing = UserModel.find_by_email(email)
            if existing and existing.id != user_id:
                return False, "邮箱已被其他用户使用"

        update_fields = {}
        if email is not None:
            update_fields["email"] = email
        if phone is not None:
            update_fields["phone"] = phone
        if extra_data is not None:
            merged = {**(user.extra_data or {}), **extra_data}
            update_fields["extra_data"] = merged

        if update_fields:
            user.update(**update_fields)
        return True, ""

    # =========================
    # 用户列表
    # =========================

    @classmethod
    def list_users(
        cls,
        source_module: str = None,
        status: str = None,
        keyword: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        conditions = ["deleted_at IS NULL"]
        params = []

        if source_module:
            conditions.append("source_module = %s")
            params.append(source_module)
        if status:
            conditions.append("status = %s")
            params.append(status)
        if keyword:
            conditions.append("(username LIKE %s OR email LIKE %s OR phone LIKE %s)")
            like_val = f"%{keyword}%"
            params.extend([like_val, like_val, like_val])

        where = " AND ".join(conditions)

        db = UserModel.get_db_connection()
        if db is None:
            return [], 0

        count_sql = f"SELECT COUNT(*) as cnt FROM {UserModel.table_alias} WHERE {where}"
        count_result = db.execute(count_sql, tuple(params))
        total = count_result[0]["cnt"] if count_result else 0

        data_sql = f"""SELECT * FROM {UserModel.table_alias}
                       WHERE {where}
                       ORDER BY id DESC
                       LIMIT %s OFFSET %s"""
        data_params = params + [limit, offset]
        results = db.execute(data_sql, tuple(data_params))
        users = []
        for row in results:
            u = UserModel(**row)
            role_info = cls.get_user_role_info(u.id, u.source_module)
            users.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "phone": u.phone,
                "source_module": u.source_module,
                "status": u.status,
                "roles": role_info.get("roles"),
                "permissions": role_info.get("permissions"),
                "last_login_at": str(u.last_login_at) if u.last_login_at else None,
                "created_at": str(u.created_at) if u.created_at else None,
            })
        return users, total

    # =========================
    # 角色 & 权限管理 (Superpowers)
    # =========================

    @classmethod
    def get_user_role_info(cls, user_id: int, source_module: str = None) -> dict:
        """获取用户的角色和权限信息（所有角色权限取并集）"""
        assignments = UserRoleModel.find_by_user(user_id, source_module)
        if not assignments:
            return {
                "roles": [],
                "role_names": [],
                "permissions": [],
                "is_admin": False,
                "is_super_admin": False,
            }

        roles = []
        role_names = []
        all_permissions = set()

        for assignment in assignments:
            # 检查是否过期
            if assignment.expires_at and assignment.expires_at < datetime.utcnow():
                continue
            role = RoleModel.get_by_id(assignment.role_id)
            if role:
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "display_name": role.display_name,
                })
                role_names.append(role.name)
                all_permissions.update(role.permissions or [])

        return {
            "roles": roles,
            "role_names": role_names,
            "permissions": list(all_permissions),
            "is_admin": "super_admin" in role_names or "admin" in role_names,
            "is_super_admin": "super_admin" in role_names,
        }

    @classmethod
    def get_user_permissions(cls, user_id: int, source_module: str = None) -> List[str]:
        """获取用户所有权限的并集"""
        info = cls.get_user_role_info(user_id, source_module)
        return info["permissions"]

    @classmethod
    def has_permission(cls, user_id: int, permission: str, source_module: str = None) -> bool:
        """检查用户是否拥有指定权限"""
        permissions = cls.get_user_permissions(user_id, source_module)
        return permission in permissions

    @classmethod
    def require_permission(cls, user_id: int, permission: str, source_module: str = None) -> Tuple[bool, str]:
        ok = cls.has_permission(user_id, permission, source_module)
        if ok:
            return True, ""
        return False, f"缺少权限: {permission}"

    # ---------- 角色分配 ----------

    @classmethod
    def grant_role(
        cls,
        operator_id: int,
        target_user_id: int,
        role_name: str,
        source_module: str = None,
        expires_at: datetime = None,
    ) -> Tuple[bool, str]:
        """授予用户角色"""
        if not cls.has_permission(operator_id, Permission.ROLE_MANAGE, source_module):
            return False, "没有角色管理权限"

        target = UserModel.get_by_id(target_user_id)
        if not target:
            return False, "目标用户不存在"

        module = source_module or target.source_module
        role = RoleModel.find_by_name(role_name, module)
        if not role:
            return False, f"角色 '{role_name}' 不存在"

        ok = UserRoleModel.grant_role(target_user_id, role.id, module, operator_id, expires_at)
        return (True, "") if ok else (False, "角色授予失败")

    @classmethod
    def revoke_role(
        cls,
        operator_id: int,
        target_user_id: int,
        role_name: str,
        source_module: str = None,
    ) -> Tuple[bool, str]:
        """撤销用户角色"""
        if not cls.has_permission(operator_id, Permission.ROLE_MANAGE, source_module):
            return False, "没有角色管理权限"

        target = UserModel.get_by_id(target_user_id)
        if not target:
            return False, "目标用户不存在"

        module = source_module or target.source_module
        role = RoleModel.find_by_name(role_name, module)
        if not role:
            return False, f"角色 '{role_name}' 不存在"

        ok = UserRoleModel.revoke_role(target_user_id, role.id, module)
        return (True, "") if ok else (False, "角色撤销失败")

    @classmethod
    def set_user_roles(
        cls,
        operator_id: int,
        target_user_id: int,
        role_names: List[str],
        source_module: str = None,
    ) -> Tuple[bool, str]:
        """替换用户的全部角色"""
        if not cls.has_permission(operator_id, Permission.ROLE_MANAGE, source_module):
            return False, "没有角色管理权限"

        target = UserModel.get_by_id(target_user_id)
        if not target:
            return False, "目标用户不存在"

        module = source_module or target.source_module
        role_ids = []
        for name in role_names:
            role = RoleModel.find_by_name(name, module)
            if not role:
                return False, f"角色 '{name}' 不存在"
            role_ids.append(role.id)

        ok = UserRoleModel.replace_roles(target_user_id, role_ids, module, operator_id)
        return (True, "") if ok else (False, "角色设置失败")

    # ---------- 角色 CRUD ----------

    @classmethod
    def list_roles(cls, source_module: str = "default") -> List[dict]:
        """获取所有角色"""
        roles = RoleModel.find_by_module(source_module)
        return [
            {
                "id": r.id,
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description,
                "permissions": r.permissions,
                "is_builtin": r.is_builtin,
            }
            for r in roles
        ]

    @classmethod
    def create_role(
        cls,
        operator_id: int,
        name: str,
        display_name: str,
        permissions: List[str],
        source_module: str = "default",
        description: str = None,
    ) -> Tuple[bool, str]:
        """创建自定义角色"""
        if not cls.has_permission(operator_id, Permission.ROLE_MANAGE, source_module):
            return False, "没有角色管理权限"

        existing = RoleModel.find_by_name(name, source_module)
        if existing:
            return False, f"角色 '{name}' 已存在"

        RoleModel.create_role(name, display_name, permissions, source_module, description)
        return True, ""

    @classmethod
    def update_role_permissions(
        cls,
        operator_id: int,
        role_name: str,
        permissions: List[str],
        source_module: str = "default",
    ) -> Tuple[bool, str]:
        """更新角色权限"""
        if not cls.has_permission(operator_id, Permission.ROLE_MANAGE, source_module):
            return False, "没有角色管理权限"

        role = RoleModel.find_by_name(role_name, source_module)
        if not role:
            return False, f"角色 '{role_name}' 不存在"

        role.update_permissions(permissions)
        return True, ""

    @classmethod
    def get_available_permissions(cls) -> List[dict]:
        """获取所有可用权限列表"""
        return [
            {"key": Permission.USER_MANAGE, "label": "用户管理", "group": "用户"},
            {"key": Permission.USER_READ, "label": "查看用户", "group": "用户"},
            {"key": Permission.ROLE_MANAGE, "label": "角色管理", "group": "角色"},
            {"key": Permission.CONTENT_MANAGE, "label": "内容管理", "group": "内容"},
            {"key": Permission.CONTENT_READ, "label": "内容查看", "group": "内容"},
            {"key": Permission.SYSTEM_CONFIG, "label": "系统配置", "group": "系统"},
            {"key": Permission.MODULE_MANAGE, "label": "模块管理", "group": "模块"},
            {"key": Permission.DATA_EXPORT, "label": "数据导出", "group": "数据"},
        ]

    # ---------- 初始化 ----------

    @classmethod
    def ensure_builtin_roles(cls, source_module: str = "default"):
        """确保预置角色存在"""
        RoleModel.ensure_builtin_roles(source_module)

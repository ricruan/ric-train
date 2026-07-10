"""
角色定义模型 (Role)

独立的角色表，支持动态创建自定义角色并定义权限。
权限以 JSON 数组存储，灵活可扩展。

Superpowers 权限体系:
  权限键格式: "资源:操作"
  预定义权限:
  - user:manage     用户管理（增删改查用户）
  - user:read       查看用户信息
  - role:manage     角色管理（创建/编辑/删除角色，分配角色）
  - content:manage  内容管理
  - content:read    内容查看
  - system:config   系统配置
  - module:manage   模块管理
  - data:export     数据导出
"""

from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional, List
from datetime import datetime
import json


# =========================
# 预定义权限常量 (Superpowers)
# =========================
class Permission:
    # 用户管理
    USER_MANAGE = "user:manage"
    USER_READ = "user:read"
    # 角色管理
    ROLE_MANAGE = "role:manage"
    # 内容管理
    CONTENT_MANAGE = "content:manage"
    CONTENT_READ = "content:read"
    # 系统配置
    SYSTEM_CONFIG = "system:config"
    # 模块管理
    MODULE_MANAGE = "module:manage"
    # 数据导出
    DATA_EXPORT = "data:export"

    ALL = [
        USER_MANAGE, USER_READ, ROLE_MANAGE,
        CONTENT_MANAGE, CONTENT_READ,
        SYSTEM_CONFIG, MODULE_MANAGE, DATA_EXPORT,
    ]


# 预置角色名（启动时自动创建）
BUILTIN_ROLES = {
    "super_admin": {
        "display_name": "超级管理员",
        "description": "拥有所有权限",
        "permissions": Permission.ALL,
    },
    "admin": {
        "display_name": "管理员",
        "description": "拥有用户、内容、模块管理权限",
        "permissions": [
            Permission.USER_MANAGE, Permission.USER_READ,
            Permission.CONTENT_MANAGE, Permission.CONTENT_READ,
            Permission.MODULE_MANAGE, Permission.DATA_EXPORT,
        ],
    },
    "moderator": {
        "display_name": "版主",
        "description": "拥有内容管理和查看权限",
        "permissions": [
            Permission.USER_READ,
            Permission.CONTENT_MANAGE, Permission.CONTENT_READ,
        ],
    },
    "user": {
        "display_name": "普通用户",
        "description": "拥有基本信息查看和内容阅读权限",
        "permissions": [Permission.USER_READ, Permission.CONTENT_READ],
    },
    "guest": {
        "display_name": "访客",
        "description": "仅拥有内容阅读权限",
        "permissions": [Permission.CONTENT_READ],
    },
}


def _parse_json_field(value):
    """将 JSON 字符串或 list 统一解析为 list"""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []


class RoleModel(BaseModuleDBModel):
    table_alias = "base_role"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` VARCHAR(50) NOT NULL COMMENT '角色标识（唯一）',
  `display_name` VARCHAR(100) NOT NULL COMMENT '角色显示名称',
  `description` VARCHAR(500) COMMENT '角色描述',
  `permissions` JSON NOT NULL COMMENT '权限列表 (JSON数组)',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块',
  `is_builtin` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否内置角色（不可删除）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_module` (`name`, `source_module`),
  KEY `idx_source_module` (`source_module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色定义表';
    """

    id: Optional[int] = None
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: list = []
    source_module: str = "default"
    is_builtin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __init__(self, **data):
        # 从 DB 读取时 permissions 可能是 JSON 字符串，统一转为 list
        if "permissions" in data:
            data["permissions"] = _parse_json_field(data["permissions"])
        super().__init__(**data)

    def _serialize_for_db(self) -> dict:
        """序列化字段用于写入 DB（permissions list → JSON string）"""
        data = self.model_dump(exclude_none=True, exclude={"id"})
        if "permissions" in data:
            data["permissions"] = json.dumps(data["permissions"], ensure_ascii=False)
        return data

    def _insert(self) -> int:
        """重写 _insert，处理 JSON 字段序列化"""
        db = self.get_db_connection()
        if db is None:
            return -1
        table_name = self.get_table_name_with_db()
        data = self._serialize_for_db()
        if not data:
            return -1
        try:
            keys = list(data.keys())
            placeholders = ",".join(["%s"] * len(keys))
            quoted_keys = [f"`{k}`" for k in keys]
            sql = f"INSERT INTO {table_name} ({','.join(quoted_keys)}) VALUES ({placeholders})"
            self.id = db.execute(sql, tuple(data[k] for k in keys))
            return self.id
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"{self.__class__.__name__}._insert() failed: {e}")
            return -1

    def _update(self) -> bool:
        """重写 _update，处理 JSON 字段序列化"""
        db = self.get_db_connection()
        if db is None:
            return False
        table_name = self.get_table_name_with_db()
        data = self._serialize_for_db()
        if not data:
            return True
        try:
            sets = ",".join([f"`{k}`=%s" for k in data])
            sql = f"UPDATE {table_name} SET {sets} WHERE id = %s"
            affected = db.execute(sql, tuple(data.values()) + (self.id,))
            return affected > 0
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"{self.__class__.__name__}._update() failed: {e}")
            return False

    # ---------- 查询方法 ----------

    @classmethod
    def find_by_name(cls, name: str, source_module: str = None):
        """按角色名查找"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return None
        sql = f"SELECT * FROM {cls.table_alias} WHERE name = %s"
        params = [name]
        if source_module:
            sql += " AND source_module = %s"
            params.append(source_module)
        sql += " LIMIT 1"
        results = db.execute(sql, tuple(params))
        return cls(**results[0]) if results else None

    @classmethod
    def find_by_module(cls, source_module: str = "default") -> List["RoleModel"]:
        """获取模块下所有角色"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE source_module = %s ORDER BY id ASC"
        results = db.execute(sql, (source_module,))
        return [cls(**row) for row in results]

    # ---------- 权限检查 ----------

    def has_permission(self, permission: str) -> bool:
        """检查此角色是否包含指定权限"""
        return permission in (self.permissions or [])

    def has_any_permission(self, permissions: List[str]) -> bool:
        """检查此角色是否包含任一指定权限"""
        return bool(set(permissions) & set(self.permissions or []))

    # ---------- 角色管理 ----------

    @classmethod
    def create_role(
        cls,
        name: str,
        display_name: str,
        permissions: List[str],
        source_module: str = "default",
        description: str = None,
    ) -> "RoleModel":
        """创建自定义角色"""
        cls._ensure_table_exists()
        role = cls(
            name=name,
            display_name=display_name,
            permissions=permissions,
            source_module=source_module,
            description=description,
            is_builtin=False,
        )
        role.save()
        return role

    @classmethod
    def ensure_builtin_roles(cls, source_module: str = "default"):
        """确保预置角色存在（启动时调用，已存在则跳过）"""
        for role_name, role_data in BUILTIN_ROLES.items():
            existing = cls.find_by_name(role_name, source_module)
            if not existing:
                role = cls(
                    name=role_name,
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                    source_module=source_module,
                    is_builtin=True,
                )
                role.save()

    def update_permissions(self, permissions: List[str]) -> bool:
        """更新角色权限（内置角色也可更新）"""
        return self.update(permissions=permissions)

"""
用户角色关联表 (User-Role 多对多)

纯关联表，一个用户可以拥有多个角色。
用户的最终权限 = 所有角色权限的并集。
"""

from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional, List
from datetime import datetime


class UserRoleModel(BaseModuleDBModel):
    table_alias = "base_user_role"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` INT NOT NULL COMMENT '用户ID',
  `role_id` INT NOT NULL COMMENT '角色ID',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块',
  `granted_by` INT COMMENT '授权人用户ID',
  `expires_at` DATETIME COMMENT '过期时间(NULL=永久)',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role_module` (`user_id`, `role_id`, `source_module`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_source_module` (`source_module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';
    """

    id: Optional[int] = None
    user_id: int
    role_id: int
    source_module: str = "default"
    granted_by: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # ---------- 查询 ----------

    @classmethod
    def find_by_user(cls, user_id: int, source_module: str = None) -> List["UserRoleModel"]:
        """查询用户的所有角色关联"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE user_id = %s"
        params = [user_id]
        if source_module:
            sql += " AND source_module = %s"
            params.append(source_module)
        results = db.execute(sql, tuple(params))
        return [cls(**row) for row in results]

    @classmethod
    def find_by_user_and_role(cls, user_id: int, role_id: int, source_module: str = None) -> Optional["UserRoleModel"]:
        """查询用户是否拥有某角色"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return None
        sql = f"SELECT * FROM {cls.table_alias} WHERE user_id = %s AND role_id = %s"
        params = [user_id, role_id]
        if source_module:
            sql += " AND source_module = %s"
            params.append(source_module)
        sql += " LIMIT 1"
        results = db.execute(sql, tuple(params))
        return cls(**results[0]) if results else None

    @classmethod
    def find_users_by_role(cls, role_id: int, source_module: str = None, limit: int = 100) -> List["UserRoleModel"]:
        """查询拥有某角色的所有用户"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE role_id = %s"
        params = [role_id]
        if source_module:
            sql += " AND source_module = %s"
            params.append(source_module)
        sql += f" LIMIT %s"
        params.append(limit)
        results = db.execute(sql, tuple(params))
        return [cls(**row) for row in results]

    # ---------- 角色分配 ----------

    @classmethod
    def grant_role(
        cls,
        user_id: int,
        role_id: int,
        source_module: str = "default",
        granted_by: int = None,
        expires_at: datetime = None,
    ) -> bool:
        """授予用户角色（如已存在则忽略）"""
        existing = cls.find_by_user_and_role(user_id, role_id, source_module)
        if existing:
            return True  # 已存在，幂等
        record = cls(
            user_id=user_id,
            role_id=role_id,
            source_module=source_module,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        return record.save() > 0

    @classmethod
    def revoke_role(cls, user_id: int, role_id: int, source_module: str = None) -> bool:
        """撤销用户角色"""
        record = cls.find_by_user_and_role(user_id, role_id, source_module)
        if not record:
            return False
        return record.delete()

    @classmethod
    def revoke_all_roles(cls, user_id: int, source_module: str = None) -> int:
        """撤销用户所有角色，返回撤销数量"""
        records = cls.find_by_user(user_id, source_module)
        count = 0
        for r in records:
            if r.delete():
                count += 1
        return count

    @classmethod
    def replace_roles(
        cls,
        user_id: int,
        role_ids: List[int],
        source_module: str = "default",
        granted_by: int = None,
    ) -> bool:
        """替换用户的所有角色（先清空再授予）"""
        cls.revoke_all_roles(user_id, source_module)
        for role_id in role_ids:
            cls.grant_role(user_id, role_id, source_module, granted_by)
        return True

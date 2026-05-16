from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional
from datetime import datetime


class UserModel(BaseModuleDBModel):
    table_alias = "base_user"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `email` VARCHAR(100) COMMENT '邮箱',
  `phone` VARCHAR(20) COMMENT '手机号',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块标识',
  `status` ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '账户状态',
  `last_login_at` DATETIME COMMENT '最后登录时间',
  `extra_data` JSON COMMENT '扩展数据(JSON)',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` DATETIME COMMENT '软删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_phone` (`phone`),
  KEY `idx_source_module` (`source_module`),
  KEY `idx_status` (`status`),
  KEY `idx_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
    """

    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password_hash: str
    source_module: str = "default"
    status: str = "active"
    last_login_at: Optional[datetime] = None
    extra_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @classmethod
    def find_by_username(cls, username: str):
        sql = f"SELECT * FROM {cls.table_alias} WHERE username = %s AND deleted_at IS NULL"
        results = cls.get_db_connection().execute(sql, (username,))
        return cls(**results[0]) if results else None

    @classmethod
    def find_by_email(cls, email: str):
        sql = f"SELECT * FROM {cls.table_alias} WHERE email = %s AND deleted_at IS NULL"
        results = cls.get_db_connection().execute(sql, (email,))
        return cls(**results[0]) if results else None

    @classmethod
    def find_by_module(cls, source_module: str, limit: int = None, offset: int = 0):
        sql = f"SELECT * FROM {cls.table_alias} WHERE source_module = %s AND deleted_at IS NULL"
        params: list = [source_module]
        sql += " ORDER BY id ASC"
        if limit is not None:
            sql += f" LIMIT %s"
            params.append(limit)
        if offset:
            sql += f" OFFSET %s"
            params.append(offset)
        results = cls.get_db_connection().execute(sql, tuple(params))
        return [cls(**row) for row in results]

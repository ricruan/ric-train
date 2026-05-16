from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional
from datetime import datetime


class UserTokenModel(BaseModuleDBModel):
    table_alias = "base_user_token"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` INT NOT NULL COMMENT '关联用户ID',
  `token` VARCHAR(500) NOT NULL COMMENT 'Token值',
  `token_type` ENUM('access', 'refresh') DEFAULT 'access' COMMENT 'Token类型',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块标识',
  `expires_at` DATETIME NOT NULL COMMENT '过期时间',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `revoked_at` DATETIME COMMENT '撤销时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_token` (`token`(255)),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_source_module` (`source_module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户Token表';
    """

    id: Optional[int] = None
    user_id: int
    token: str
    token_type: str = "access"
    source_module: str = "default"
    expires_at: datetime
    created_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    def find_active_token(self, user_id: int, token_type: str = "access"):
        sql = f"""SELECT * FROM {self.table_alias}
                  WHERE user_id = %s AND token_type = %s
                  AND revoked_at IS NULL AND expires_at > NOW()
                  ORDER BY id DESC LIMIT 1"""
        results = UserTokenModel.get_db_connection().execute(sql, (user_id, token_type))
        return UserTokenModel(**results[0]) if results else None

    def revoke_all_for_user(self, user_id: int):
        sql = f"""UPDATE {self.table_alias}
                  SET revoked_at = NOW()
                  WHERE user_id = %s AND revoked_at IS NULL"""
        return UserTokenModel.get_db_connection().execute(sql, (user_id,), commit=True)

    def find_valid_token(self, token: str):
        sql = f"""SELECT * FROM {self.table_alias}
                  WHERE token = %s AND revoked_at IS NULL AND expires_at > NOW()"""
        results = UserTokenModel.get_db_connection().execute(sql, (token,))
        return UserTokenModel(**results[0]) if results else None

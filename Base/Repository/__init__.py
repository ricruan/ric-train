from Base.Repository.register import register_default_connection, register_base_module_connection

# 注册默认连接 和 Base模块连接
register_default_connection()
register_base_module_connection()


def _init_builtin_roles():
    """确保预置角色存在（首次启动时自动创建）"""
    try:
        from Base.Models.roleModel import RoleModel
        RoleModel.ensure_builtin_roles()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"init builtin roles failed: {e}")


_init_builtin_roles()
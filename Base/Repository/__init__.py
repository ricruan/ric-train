from Base.Repository.register import register_default_connection, register_base_module_connection, init_base_module_tables

# 注册默认连接 和 Base模块连接
register_default_connection()
register_base_module_connection()
init_base_module_tables()
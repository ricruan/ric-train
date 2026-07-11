"""
初始化 Wolin 模块的管理员账号

使用方法:
    python Wolin/scripts/init_admin.py

或者直接运行:
    cd Wolin
    python scripts/init_admin.py
"""
import sys
import os

# 添加项目根目录到 path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 初始化日志
from Base.Config.logConfig import setup_logging
setup_logging()

# 注册数据库连接
from Wolin.db.connectionInit import register_wolin_connection
register_wolin_connection()

from Base.Service.authService import AuthService
from Base.Models.roleModel import RoleModel


def init_admin():
    """初始化管理员账号"""
    # 确保预置角色存在
    print("正在检查预置角色...")
    RoleModel.ensure_builtin_roles("wolin")
    print("✓ 预置角色已就绪")

    # 检查管理员是否已存在
    admin_username = "admin"
    existing_user = None
    from Base.Models.userModel import UserModel
    existing_user = UserModel.find_by_username(admin_username)

    if existing_user:
        print(f"⚠ 管理员账号 '{admin_username}' 已存在 (ID: {existing_user.id})")
        print("如需重置密码，请使用 AuthService.reset_password()")
        return

    # 创建管理员
    print(f"\n正在创建管理员账号...")
    print(f"  用户名: {admin_username}")
    print(f"  密码: admin123")
    print(f"  角色: super_admin")

    ok, user, msg = AuthService.register(
        username=admin_username,
        password="admin123",
        source_module="wolin",
        email="admin@example.com",
        role_name="super_admin",
    )

    if ok:
        print(f"\n✓ 管理员账号创建成功!")
        print(f"  ID: {user.id}")
        print(f"  用户名: {user.username}")
        print(f"\n登录信息:")
        print(f"  POST /api/auth/login")
        print(f"  {{\"username\": \"admin\", \"password\": \"admin123\"}}")
    else:
        print(f"\n✗ 创建失败: {msg}")


if __name__ == "__main__":
    init_admin()

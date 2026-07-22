#!/usr/bin/env python3
"""
Wolin 模块初始化脚本

确保：
1. Wolin 模块的内置角色存在
2. Wolin 模块的默认菜单存在
3. Wolin 模块的超级管理员账号存在
"""

import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Base.Models.roleModel import RoleModel
from Base.Models.menuModel import MenuModel
from Base.Service.authService import AuthService


def init_wolin():
    source_module = "wolin"

    print(f"[1/3] 确保 {source_module} 模块的内置角色存在...")
    RoleModel.ensure_builtin_roles(source_module)
    print("  ✓ 角色初始化完成")

    print(f"[2/3] 确保 {source_module} 模块的默认菜单存在...")
    MenuModel.ensure_default_menus(source_module)
    print("  ✓ 菜单初始化完成")

    print(f"[3/3] 检查 {source_module} 模块的超级管理员账号...")
    from Base.Models.userModel import UserModel
    admin = UserModel.find_by_username("admin")
    if not admin or admin.source_module != source_module:
        ok, user, msg = AuthService.register(
            username="admin",
            password="admin123",
            source_module=source_module,
            role_name="super_admin",
        )
        if ok:
            print("  ✓ 超级管理员账号创建成功 (admin / admin123)")
        else:
            print(f"  ✗ 创建失败: {msg}")
    else:
        print("  ✓ 超级管理员账号已存在")

    print("\n✅ Wolin 模块初始化完成！")
    print("  登录账号: admin")
    print("  登录密码: admin123")


if __name__ == "__main__":
    init_wolin()

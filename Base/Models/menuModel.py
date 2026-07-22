"""
菜单管理模型 (Menu)

动态菜单配置表，支持树形结构（父子关系），
用于前端侧边栏菜单的动态渲染与权限控制。
"""

from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional, List
from datetime import datetime


class MenuModel(BaseModuleDBModel):
    table_alias = "base_menu"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `parent_id` INT DEFAULT NULL COMMENT '父菜单ID（逻辑关系，无外键）',
  `name` VARCHAR(50) NOT NULL COMMENT '菜单名称',
  `path` VARCHAR(200) NOT NULL COMMENT '路由路径',
  `component` VARCHAR(200) NOT NULL COMMENT '前端组件路径',
  `icon` VARCHAR(50) COMMENT '图标标识',
  `permission` VARCHAR(100) COMMENT '权限键（NULL表示所有人可见）',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序权重',
  `is_visible` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否在侧边栏显示',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块标识',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_parent` (`parent_id`),
  INDEX `idx_module` (`source_module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜单配置表';
    """

    id: Optional[int] = None
    parent_id: Optional[int] = None
    name: str
    path: str
    component: str
    icon: Optional[str] = None
    permission: Optional[str] = None
    sort_order: int = 0
    is_visible: bool = True
    source_module: str = "default"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ---------- 查询方法 ----------

    @classmethod
    def find_by_module(cls, source_module: str) -> List["MenuModel"]:
        """获取模块下所有菜单，按 sort_order 排序"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE source_module = %s ORDER BY sort_order ASC, id ASC"
        results = db.execute(sql, (source_module,))
        return [cls(**row) for row in results]

    @classmethod
    def find_by_id(cls, menu_id: int) -> Optional["MenuModel"]:
        """根据 ID 查找菜单"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return None
        sql = f"SELECT * FROM {cls.table_alias} WHERE id = %s LIMIT 1"
        results = db.execute(sql, (menu_id,))
        return cls(**results[0]) if results else None

    @classmethod
    def find_children(cls, parent_id: int) -> List["MenuModel"]:
        """查找指定父菜单的子菜单，按 sort_order 排序"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE parent_id = %s ORDER BY sort_order ASC, id ASC"
        results = db.execute(sql, (parent_id,))
        return [cls(**row) for row in results]

    # ---------- 删除方法 ----------

    @classmethod
    def delete_with_children(cls, menu_id: int) -> int:
        """
        删除菜单及其所有子菜单（递归），返回删除的数量。
        由于无外键约束，需手动递归删除。
        """
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return 0

        deleted_count = 0

        # 先递归删除所有子菜单
        children = cls.find_children(menu_id)
        for child in children:
            deleted_count += cls.delete_with_children(child.id)

        # 再删除自身
        sql = f"DELETE FROM {cls.table_alias} WHERE id = %s"
        affected = db.execute(sql, (menu_id,))
        if affected > 0:
            deleted_count += affected

        return deleted_count

    # ---------- 树形构建 ----------

    @classmethod
    def build_tree(cls, menus: List["MenuModel"]) -> List[dict]:
        """
        将扁平的菜单列表组装为树形结构。

        返回的每个 dict 包含：
        id, parent_id, name, path, component, icon, permission, sort_order, is_visible, children
        """
        def _menu_to_dict(menu: "MenuModel") -> dict:
            return {
                "id": menu.id,
                "parent_id": menu.parent_id,
                "name": menu.name,
                "path": menu.path,
                "component": menu.component,
                "icon": menu.icon,
                "permission": menu.permission,
                "sort_order": menu.sort_order,
                "is_visible": menu.is_visible,
                "children": [],
            }

        # 构建 id -> dict 映射
        menu_map: dict[int, dict] = {}
        for menu in menus:
            menu_map[menu.id] = _menu_to_dict(menu)

        # 组装树形结构
        roots: List[dict] = []
        for menu in menus:
            node = menu_map[menu.id]
            if menu.parent_id is None:
                roots.append(node)
            else:
                parent_node = menu_map.get(menu.parent_id)
                if parent_node is not None:
                    parent_node["children"].append(node)
                else:
                    # 父节点不在列表中，当作根节点处理
                    roots.append(node)

        return roots

    # ---------- 默认菜单初始化 ----------

    @classmethod
    def ensure_default_menus(cls, source_module: str = "default"):
        """
        确保默认菜单存在（启动时调用，已存在则跳过）。
        仅当该模块下无任何菜单时才创建默认菜单。
        """
        existing = cls.find_by_module(source_module)
        if existing:
            return

        default_menus = [
            {"name": "记录管理", "path": "/records", "component": "pages/records/RecordManager", "icon": "TableOutlined", "permission": "content:manage", "sort_order": 1},
            {"name": "用户管理", "path": "/users", "component": "pages/users/UserManager", "icon": "UserOutlined", "permission": "user:manage", "sort_order": 2},
            {"name": "角色管理", "path": "/roles", "component": "pages/roles/RoleManager", "icon": "TeamOutlined", "permission": "role:manage", "sort_order": 3},
            {"name": "菜单管理", "path": "/menus", "component": "pages/menus/MenuManager", "icon": "MenuOutlined", "permission": "system:config", "sort_order": 4},
        ]

        for menu_data in default_menus:
            menu = cls(
                parent_id=None,
                name=menu_data["name"],
                path=menu_data["path"],
                component=menu_data["component"],
                icon=menu_data.get("icon"),
                permission=menu_data.get("permission"),
                sort_order=menu_data["sort_order"],
                is_visible=True,
                source_module=source_module,
            )
            menu.save()

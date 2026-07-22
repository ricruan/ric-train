# Wolin 认证与菜单管理系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的认证、授权和动态菜单管理系统，包括后端菜单模型、API 接口，前端动态路由和管理页面。

**Architecture:** 后端新增 MenuModel 存储菜单树，通过权限过滤返回用户可见菜单；前端切换为真实认证模式，动态加载菜单并渲染路由和侧边栏。

**Tech Stack:** Python FastAPI, MySQL, React 19, TypeScript, Vite, React Router 7

## Global Constraints

- **后端**: 所有新模型继承 `BaseModuleDBModel`，表名前缀 `base_`
- **后端**: 不使用外键约束，`parent_id` 仅逻辑关联
- **后端**: API 路径前缀 `/api/auth`，使用 `HttpResponse.ok()` 统一响应格式
- **后端**: 权限检查使用 `_require_permission()` 装饰器
- **前端**: 所有管理页面使用 `React.lazy()` 懒加载
- **前端**: 组件映射使用白名单 `componentMap`，防止路径注入
- **前端**: 图标从 `@ant-design/icons` 动态加载
- **数据库**: Wolin 模块 `source_module="wolin"`
- **默认账号**: 初始化时创建 `admin/admin123` 超级管理员

---

## Task 1: Create MenuModel

**Files:**
- Create: `Base/Models/menuModel.py`

**Interfaces:**
- Consumes: `BaseModuleDBModel` from `Base/Repository/models/moduleDbModel.py`
- Produces: `MenuModel` class with CRUD methods and tree assembly logic

- [ ] **Step 1: Create MenuModel class**

Create `Base/Models/menuModel.py`:

```python
"""
菜单模型 (Menu)

支持树形菜单结构，通过 permission 字段关联角色权限。
permission 为空表示所有登录用户可见。
"""

from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from typing import Optional, List
from datetime import datetime


class MenuModel(BaseModuleDBModel):
    table_alias = "base_menu"
    create_table_sql = f"""
    CREATE TABLE `{table_alias}` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `parent_id` INT DEFAULT NULL COMMENT '父菜单ID（无外键）',
  `name` VARCHAR(50) NOT NULL COMMENT '菜单名称',
  `path` VARCHAR(200) NOT NULL COMMENT '路由路径',
  `component` VARCHAR(200) NOT NULL COMMENT '前端组件key',
  `icon` VARCHAR(50) COMMENT '图标标识',
  `permission` VARCHAR(100) COMMENT '权限标识（空=所有用户可见）',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序权重',
  `is_visible` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否在侧边栏显示',
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '来源模块',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_parent` (`parent_id`),
  KEY `idx_module` (`source_module`),
  KEY `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='菜单表';
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

    @classmethod
    def find_by_module(cls, source_module: str) -> List["MenuModel"]:
        """获取模块下所有菜单（按 sort_order 排序）"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE source_module = %s ORDER BY sort_order ASC, id ASC"
        results = db.execute(sql, (source_module,))
        return [cls(**row) for row in results]

    @classmethod
    def find_by_id(cls, menu_id: int) -> Optional["MenuModel"]:
        """按 ID 查找菜单"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return None
        sql = f"SELECT * FROM {cls.table_alias} WHERE id = %s"
        results = db.execute(sql, (menu_id,))
        return cls(**results[0]) if results else None

    @classmethod
    def find_children(cls, parent_id: int) -> List["MenuModel"]:
        """查找子菜单"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return []
        sql = f"SELECT * FROM {cls.table_alias} WHERE parent_id = %s ORDER BY sort_order ASC"
        results = db.execute(sql, (parent_id,))
        return [cls(**row) for row in results]

    @classmethod
    def delete_with_children(cls, menu_id: int) -> int:
        """删除菜单及其所有子菜单（递归）"""
        cls._ensure_table_exists()
        db = cls.get_db_connection()
        if db is None:
            return 0

        deleted_count = 0

        # 先删除子菜单
        children = cls.find_children(menu_id)
        for child in children:
            deleted_count += cls.delete_with_children(child.id)

        # 删除自身
        sql = f"DELETE FROM {cls.table_alias} WHERE id = %s"
        affected = db.execute(sql, (menu_id,))
        deleted_count += affected

        return deleted_count

    @classmethod
    def build_tree(cls, menus: List["MenuModel"]) -> List[dict]:
        """将菜单列表组装成树形结构"""
        menu_map = {menu.id: menu for menu in menus}
        tree = []

        for menu in menus:
            menu_dict = {
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

            if menu.parent_id is None or menu.parent_id not in menu_map:
                tree.append(menu_dict)
            else:
                # 找到父节点并添加
                for parent_dict in tree:
                    if cls._find_and_add_child(parent_dict, menu.parent_id, menu_dict):
                        break

        return tree

    @classmethod
    def _find_and_add_child(cls, node: dict, target_parent_id: int, child: dict) -> bool:
        """递归查找父节点并添加子节点"""
        if node["id"] == target_parent_id:
            node["children"].append(child)
            return True
        for child_node in node["children"]:
            if cls._find_and_add_child(child_node, target_parent_id, child):
                return True
        return False

    @classmethod
    def ensure_default_menus(cls, source_module: str = "default"):
        """确保默认菜单存在（启动时调用）"""
        existing = cls.find_by_module(source_module)
        if existing:
            return  # 已存在菜单，跳过

        default_menus = [
            {"name": "记录管理", "path": "/records", "component": "pages/records/RecordManager", "icon": "TableOutlined", "permission": "content:manage", "sort_order": 1},
            {"name": "用户管理", "path": "/users", "component": "pages/users/UserManager", "icon": "UserOutlined", "permission": "user:manage", "sort_order": 2},
            {"name": "角色管理", "path": "/roles", "component": "pages/roles/RoleManager", "icon": "TeamOutlined", "permission": "role:manage", "sort_order": 3},
            {"name": "菜单管理", "path": "/menus", "component": "pages/menus/MenuManager", "icon": "MenuOutlined", "permission": "system:config", "sort_order": 4},
        ]

        for menu_data in default_menus:
            menu = cls(
                parent_id=None,
                source_module=source_module,
                **menu_data,
            )
            menu.save()
```

- [ ] **Step 2: Verify model syntax**

Run: `python -c "from Base.Models.menuModel import MenuModel; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Base/Models/menuModel.py
git commit -m "feat: add MenuModel for dynamic menu management"
```

---

## Task 2: Menu CRUD API

**Files:**
- Modify: `Base/Api/authApi.py` (add menu endpoints)

**Interfaces:**
- Consumes: `MenuModel` from `Base/Models/menuModel.py`
- Produces: REST API endpoints for menu CRUD

- [ ] **Step 1: Add Request models**

Add to `Base/Api/authApi.py` after existing Request models:

```python
class CreateMenuRequest(BaseModel):
    parent_id: Optional[int] = None
    name: str = Field(..., max_length=50)
    path: str = Field(..., max_length=200)
    component: str = Field(..., max_length=200)
    icon: Optional[str] = Field(None, max_length=50)
    permission: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0
    is_visible: bool = True
    source_module: str = "default"


class UpdateMenuRequest(BaseModel):
    parent_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=50)
    path: Optional[str] = Field(None, max_length=200)
    component: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = Field(None, max_length=50)
    permission: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None


class SortMenuRequest(BaseModel):
    items: List[dict] = Field(..., description="[{id, sort_order}]")
```

- [ ] **Step 2: Add import**

Add at top of `Base/Api/authApi.py`:

```python
from Base.Models.menuModel import MenuModel
```

- [ ] **Step 3: Add menu CRUD endpoints**

Add to `Base/Api/authApi.py` after existing endpoints:

```python
# =========================
# 菜单管理 (需 system:config 权限)
# =========================

@router.get("/menus")
def get_menus(
    source_module: str = "default",
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    _require_permission(credentials, Permission.SYSTEM_CONFIG)
    menus = MenuModel.find_by_module(source_module)
    tree = MenuModel.build_tree(menus)
    return HttpResponse.ok(data={"menus": tree})


@router.post("/menus")
def create_menu(
    req: CreateMenuRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    _require_permission(credentials, Permission.SYSTEM_CONFIG)
    menu = MenuModel(**req.model_dump())
    menu.save()
    return HttpResponse.ok(data={"id": menu.id}, msg="创建成功")


@router.put("/menus/{menu_id}")
def update_menu(
    menu_id: int,
    req: UpdateMenuRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    _require_permission(credentials, Permission.SYSTEM_CONFIG)
    menu = MenuModel.find_by_id(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(menu, key, value)
    menu.save()

    return HttpResponse.ok(msg="更新成功")


@router.delete("/menus/{menu_id}")
def delete_menu(
    menu_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    _require_permission(credentials, Permission.SYSTEM_CONFIG)
    deleted = MenuModel.delete_with_children(menu_id)
    return HttpResponse.ok(data={"deleted": deleted}, msg=f"已删除 {deleted} 条菜单")


@router.put("/menus/sort")
def sort_menus(
    req: SortMenuRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    _require_permission(credentials, Permission.SYSTEM_CONFIG)
    for item in req.items:
        menu = MenuModel.find_by_id(item["id"])
        if menu:
            menu.update(sort_order=item["sort_order"])
    return HttpResponse.ok(msg="排序更新成功")
```

- [ ] **Step 4: Verify syntax**

Run: `python -c "from Base.Api.authApi import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add Base/Api/authApi.py
git commit -m "feat: add menu CRUD API endpoints"
```

---

## Task 3: User Menus API

**Files:**
- Modify: `Base/Api/authApi.py` (add `/me/menus` endpoint)

**Interfaces:**
- Consumes: `MenuModel`, `AuthService.get_user_role_info()`
- Produces: `GET /api/auth/me/menus` endpoint

- [ ] **Step 1: Add /me/menus endpoint**

Add to `Base/Api/authApi.py` after the `/me` endpoints:

```python
@router.get("/me/menus")
def get_my_menus(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户可见的菜单树"""
    user = _get_current_user(credentials)
    role_info = AuthService.get_user_role_info(user.id, user.source_module)

    # 获取用户所有菜单
    all_menus = MenuModel.find_by_module(user.source_module)

    # 过滤：permission 为空 OR permission 在用户权限中
    user_permissions = set(role_info["permissions"])
    visible_menus = [
        menu for menu in all_menus
        if not menu.permission or menu.permission in user_permissions
    ]

    # 组装成树形结构
    tree = MenuModel.build_tree(visible_menus)
    return HttpResponse.ok(data={"menus": tree})
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "from Base.Api.authApi import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add Base/Api/authApi.py
git commit -m "feat: add /me/menus endpoint for user menu tree"
```

---

## Task 4: Wolin Initialization Script

**Files:**
- Create: `Wolin/scripts/init_wolin.py`

**Interfaces:**
- Consumes: `RoleModel.ensure_builtin_roles()`, `MenuModel.ensure_default_menus()`, `AuthService.register()`
- Produces: Initialization script for Wolin module

- [ ] **Step 1: Create init script**

Create `Wolin/scripts/init_wolin.py`:

```python
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
```

- [ ] **Step 2: Make executable**

Run: `chmod +x Wolin/scripts/init_wolin.py` (Linux/Mac) or ensure it can be run with `python Wolin/scripts/init_wolin.py`

- [ ] **Step 3: Test the script**

Run: `python Wolin/scripts/init_wolin.py`
Expected: Script runs successfully, creates roles, menus, and admin account

- [ ] **Step 4: Commit**

```bash
git add Wolin/scripts/init_wolin.py
git commit -m "feat: add Wolin initialization script with default admin"
```

---

## Task 5: Frontend Auth Switch

**Files:**
- Modify: `Wolin/frontend/react/apps/admin/.env`
- Modify: `Wolin/frontend/react/packages/shared/src/auth/AuthProvider.tsx`
- Modify: `Wolin/frontend/react/packages/shared/src/auth/types.ts`
- Create: `Wolin/frontend/react/packages/shared/src/api/menus.ts`

**Interfaces:**
- Consumes: Backend `/api/auth/*` endpoints
- Produces: Enhanced AuthProvider with `menus` and `hasPermission()`

- [ ] **Step 1: Switch to API mode**

Modify `Wolin/frontend/react/apps/admin/.env`:

```env
VITE_AUTH_MODE=api
VITE_API_BASE_URL=http://localhost:8001
```

- [ ] **Step 2: Create menus API module**

Create `Wolin/frontend/react/packages/shared/src/api/menus.ts`:

```typescript
import { apiClient } from './client';

export interface MenuItem {
  id: number;
  parent_id: number | null;
  name: string;
  path: string;
  component: string;
  icon?: string;
  permission?: string;
  sort_order: number;
  is_visible: boolean;
  children: MenuItem[];
}

export async function fetchUserMenus(): Promise<MenuItem[]> {
  const res = await apiClient.get('/api/auth/me/menus');
  return res.data.data.menus;
}
```

- [ ] **Step 3: Update auth types**

Modify `Wolin/frontend/react/packages/shared/src/auth/types.ts`, add to `AuthContextType`:

```typescript
import type { MenuItem } from '../api/menus';

export interface AuthContextType {
  user: User | null;
  ready: boolean;
  menus: MenuItem[];
  login: (form: LoginForm) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}
```

- [ ] **Step 4: Enhance AuthProvider**

Modify `Wolin/frontend/react/packages/shared/src/auth/AuthProvider.tsx`:

Add imports:

```typescript
import { fetchUserMenus, type MenuItem } from '../api/menus';
```

Add state:

```typescript
const [menus, setMenus] = useState<MenuItem[]>([]);
```

Update login method to fetch menus:

```typescript
const login = async (form: LoginForm) => {
  const result = await strategy.login(form);
  setTokens(result.tokens.access_token, result.tokens.refresh_token);
  setUser(result.user);

  // 获取用户菜单
  try {
    const userMenus = await fetchUserMenus();
    setMenus(userMenus);
  } catch (err) {
    console.error('Failed to fetch menus:', err);
    setMenus([]);
  }
};
```

Update mount effect to fetch menus:

```typescript
useEffect(() => {
  const token = getToken();
  if (token) {
    strategy
      .getUser(token)
      .then((u) => {
        if (u) {
          setUser(u);
          // 获取菜单
          fetchUserMenus()
            .then(setMenus)
            .catch(() => setMenus([]));
        } else {
          clearToken();
        }
      })
      .catch(() => clearToken())
      .finally(() => setReady(true));
  } else {
    setReady(true);
  }
}, []);
```

Add hasPermission method:

```typescript
const hasPermission = useCallback(
  (permission: string) => {
    if (!user) return false;
    if (user.is_admin) return true; // 管理员拥有所有权限
    return user.permissions.includes(permission);
  },
  [user],
);
```

Update context value:

```typescript
return (
  <AuthContext.Provider value={{ user, ready, menus, login, logout, hasPermission }}>
    {children}
  </AuthContext.Provider>
);
```

- [ ] **Step 5: Update shared index exports**

Modify `Wolin/frontend/react/packages/shared/src/index.ts`, add:

```typescript
export { fetchUserMenus, type MenuItem } from './api/menus';
```

- [ ] **Step 6: Build shared package**

Run: `cd Wolin/frontend/react && pnpm --filter @interview/shared build`
Expected: Build succeeds

- [ ] **Step 7: Commit**

```bash
git add Wolin/frontend/react/
git commit -m "feat: switch admin to API auth mode with dynamic menus"
```

---

## Task 6: Frontend Dynamic Routing

**Files:**
- Create: `Wolin/frontend/react/apps/admin/src/router/componentMap.ts`
- Create: `Wolin/frontend/react/packages/shared/src/router/DynamicRouter.tsx`
- Modify: `Wolin/frontend/react/apps/admin/src/App.tsx`

**Interfaces:**
- Consumes: `MenuItem[]` from AuthProvider
- Produces: Dynamic route rendering based on menu tree

- [ ] **Step 1: Create component map**

Create `Wolin/frontend/react/apps/admin/src/router/componentMap.ts`:

```typescript
import { lazy } from 'react';

export const componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>> = {
  'pages/records/RecordManager': lazy(() => import('../pages/records/RecordManager')),
  'pages/users/UserManager': lazy(() => import('../pages/users/UserManager')),
  'pages/roles/RoleManager': lazy(() => import('../pages/roles/RoleManager')),
  'pages/menus/MenuManager': lazy(() => import('../pages/menus/MenuManager')),
};
```

- [ ] **Step 2: Create DynamicRouter**

Create `Wolin/frontend/react/packages/shared/src/router/DynamicRouter.tsx`:

```typescript
import { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import type { MenuItem } from '../api/menus';

interface DynamicRouterProps {
  menus: MenuItem[];
  componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>>;
}

function renderRoutes(menus: MenuItem[], componentMap: Record<string, React.LazyExoticComponent<React.ComponentType>>): React.ReactNode[] {
  const routes: React.ReactNode[] = [];

  for (const menu of menus) {
    const Component = componentMap[menu.component];

    if (Component) {
      routes.push(
        <Route
          key={menu.id}
          path={menu.path}
          element={
            <Suspense fallback={<div>加载中...</div>}>
              <Component />
            </Suspense>
          }
        />,
      );
    }

    // 递归处理子菜单
    if (menu.children && menu.children.length > 0) {
      routes.push(...renderRoutes(menu.children, componentMap));
    }
  }

  return routes;
}

export function DynamicRouter({ menus, componentMap }: DynamicRouterProps) {
  if (menus.length === 0) {
    return <div>暂无菜单权限</div>;
  }

  // 默认跳转到第一个菜单
  const firstMenu = menus[0];

  return (
    <Routes>
      <Route index element={<Navigate to={firstMenu.path} replace />} />
      {renderRoutes(menus, componentMap)}
      <Route path="*" element={<Navigate to={firstMenu.path} replace />} />
    </Routes>
  );
}
```

- [ ] **Step 3: Update shared index exports**

Modify `Wolin/frontend/react/packages/shared/src/index.ts`, add:

```typescript
export { DynamicRouter } from './router/DynamicRouter';
```

- [ ] **Step 4: Update admin App.tsx**

Modify `Wolin/frontend/react/apps/admin/src/App.tsx`:

Replace hardcoded routes with DynamicRouter:

```typescript
import { useAuth, DynamicRouter } from '@interview/shared';
import { componentMap } from './router/componentMap';

function AdminApp() {
  const { menus } = useAuth();

  return <DynamicRouter menus={menus} componentMap={componentMap} />;
}
```

Keep the outer structure (HashRouter, AuthProvider, RequireAuth) intact.

- [ ] **Step 5: Build and verify**

Run: `cd Wolin/frontend/react && pnpm build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add Wolin/frontend/react/
git commit -m "feat: implement dynamic routing with componentMap"
```

---

## Task 7: Frontend Sidebar Rendering

**Files:**
- Modify: `Wolin/frontend/react/apps/admin/src/App.tsx` (AdminLayout component)
- Create: `Wolin/frontend/react/apps/admin/src/utils/iconMap.ts`

**Interfaces:**
- Consumes: `MenuItem[]` from AuthProvider, `@ant-design/icons`
- Produces: Dynamic sidebar menu rendering

- [ ] **Step 1: Create icon map**

Create `Wolin/frontend/react/apps/admin/src/utils/iconMap.ts`:

```typescript
import * as Icons from '@ant-design/icons';
import type { ComponentType } from 'react';

export const iconMap: Record<string, ComponentType> = {
  'UserOutlined': Icons.UserOutlined,
  'TeamOutlined': Icons.TeamOutlined,
  'TableOutlined': Icons.TableOutlined,
  'MenuOutlined': Icons.MenuOutlined,
  'SettingOutlined': Icons.SettingOutlined,
  'DashboardOutlined': Icons.DashboardOutlined,
  'FileTextOutlined': Icons.FileTextOutlined,
  'CheckSquareOutlined': Icons.CheckSquareOutlined,
  'VideoCameraOutlined': Icons.VideoCameraOutlined,
};

export function getIcon(iconName?: string): ComponentType | null {
  if (!iconName) return null;
  return iconMap[iconName] || null;
}
```

- [ ] **Step 2: Update AdminLayout**

Modify `Wolin/frontend/react/apps/admin/src/App.tsx`, update the AdminLayout component to render dynamic menu:

```typescript
import { useAuth, MenuItem } from '@interview/shared';
import { getIcon } from './utils/iconMap';

function renderMenuItems(menus: MenuItem[]): React.ReactNode[] {
  return menus.map((menu) => {
    const IconComponent = getIcon(menu.icon);

    if (menu.children && menu.children.length > 0) {
      return (
        <SubMenu
          key={menu.id}
          title={
            <>
              {IconComponent && <IconComponent />}
              <span>{menu.name}</span>
            </>
          }
        >
          {renderMenuItems(menu.children)}
        </SubMenu>
      );
    }

    return (
      <Menu.Item key={menu.path}>
        <Link to={menu.path}>
          {IconComponent && <IconComponent />}
          <span>{menu.name}</span>
        </Link>
      </Menu.Item>
    );
  });
}

// In AdminLayout:
const { menus } = useAuth();

<Menu mode="inline" selectedKeys={[location.pathname]}>
  {renderMenuItems(menus)}
</Menu>
```

- [ ] **Step 3: Build and verify**

Run: `cd Wolin/frontend/react && pnpm build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add Wolin/frontend/react/
git commit -m "feat: implement dynamic sidebar menu rendering"
```

---

## Task 8: UserManager Page

**Files:**
- Create: `Wolin/frontend/react/apps/admin/src/pages/users/UserManager.tsx`
- Create: `Wolin/frontend/react/apps/admin/src/api/users.ts`

**Interfaces:**
- Consumes: Backend `/api/auth/users` endpoints
- Produces: User management UI with list, search, status toggle, password reset, role assignment

- [ ] **Step 1: Create users API module**

Create `Wolin/frontend/react/apps/admin/src/api/users.ts`:

```typescript
import { apiClient } from '@interview/shared';

export interface User {
  id: number;
  username: string;
  email?: string;
  phone?: string;
  source_module: string;
  status: string;
  roles: string[];
  created_at: string;
}

export async function getUsers(params?: { keyword?: string; limit?: number; offset?: number }) {
  const res = await apiClient.get('/api/auth/users', { params });
  return res.data.data;
}

export async function updateUserStatus(userId: number, status: string) {
  const res = await apiClient.put('/api/auth/users/status', { user_id: userId, status });
  return res.data;
}

export async function resetUserPassword(userId: number, newPassword: string) {
  const res = await apiClient.post('/api/auth/users/reset-password', { user_id: userId, new_password: newPassword });
  return res.data;
}

export async function setUserRoles(userId: number, roleNames: string[], sourceModule: string) {
  const res = await apiClient.post('/api/auth/roles/set', { target_user_id: userId, role_names: roleNames, source_module: sourceModule });
  return res.data;
}
```

- [ ] **Step 2: Create UserManager page**

Create `Wolin/frontend/react/apps/admin/src/pages/users/UserManager.tsx`:

```typescript
import { useState, useEffect } from 'react';
import { Table, Button, Modal, Input, Select, message, Popconfirm } from 'antd';
import { getUsers, updateUserStatus, resetUserPassword, setUserRoles, type User } from '../../api/users';

export default function UserManager() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [keyword, setKeyword] = useState('');

  useEffect(() => {
    loadUsers();
  }, [keyword]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await getUsers({ keyword, limit: 100 });
      setUsers(data.users || []);
    } catch (err) {
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    try {
      await updateUserStatus(user.id, newStatus);
      message.success('状态更新成功');
      loadUsers();
    } catch (err) {
      message.error('状态更新失败');
    }
  };

  const handleResetPassword = async (user: User) => {
    try {
      await resetUserPassword(user.id, '123456');
      message.success('密码已重置为 123456');
    } catch (err) {
      message.error('密码重置失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    { title: '角色', dataIndex: 'roles', key: 'roles', render: (roles: string[]) => roles?.join(', ') },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, user: User) => (
        <>
          <Button size="small" onClick={() => handleToggleStatus(user)}>
            {user.status === 'active' ? '禁用' : '启用'}
          </Button>
          <Popconfirm title="确定重置密码？" onConfirm={() => handleResetPassword(user)}>
            <Button size="small">重置密码</Button>
          </Popconfirm>
        </>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>用户管理</h2>
      <Input.Search
        placeholder="搜索用户名/邮箱"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        style={{ marginBottom: 16, width: 300 }}
      />
      <Table columns={columns} dataSource={users} loading={loading} rowKey="id" />
    </div>
  );
}
```

- [ ] **Step 3: Add to componentMap**

The component is already registered in `componentMap.ts` from Task 6.

- [ ] **Step 4: Build and verify**

Run: `cd Wolin/frontend/react && pnpm build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add Wolin/frontend/react/apps/admin/src/pages/users/
git add Wolin/frontend/react/apps/admin/src/api/users.ts
git commit -m "feat: add UserManager page with list and actions"
```

---

## Task 9: RoleManager Page

**Files:**
- Create: `Wolin/frontend/react/apps/admin/src/pages/roles/RoleManager.tsx`
- Create: `Wolin/frontend/react/apps/admin/src/api/roles.ts`

**Interfaces:**
- Consumes: Backend `/api/auth/roles` endpoints
- Produces: Role management UI with list, create, edit, permission config

- [ ] **Step 1: Create roles API module**

Create `Wolin/frontend/react/apps/admin/src/api/roles.ts`:

```typescript
import { apiClient } from '@interview/shared';

export interface Role {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  permissions: string[];
  source_module: string;
  is_builtin: boolean;
}

export async function getRoles(sourceModule: string) {
  const res = await apiClient.get('/api/auth/roles', { params: { source_module: sourceModule } });
  return res.data.data;
}

export async function createRole(data: { name: string; display_name: string; permissions: string[]; description?: string; source_module: string }) {
  const res = await apiClient.post('/api/auth/roles', data);
  return res.data;
}

export async function updateRolePermissions(roleName: string, permissions: string[], sourceModule: string) {
  const res = await apiClient.put('/api/auth/roles/permissions', { role_name: roleName, permissions, source_module: sourceModule });
  return res.data;
}

export async function getPermissions() {
  const res = await apiClient.get('/api/auth/permissions');
  return res.data.data;
}
```

- [ ] **Step 2: Create RoleManager page**

Create `Wolin/frontend/react/apps/admin/src/pages/roles/RoleManager.tsx`:

```typescript
import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Checkbox, message } from 'antd';
import { getRoles, createRole, updateRolePermissions, getPermissions, type Role } from '../../api/roles';

export default function RoleManager() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRoles();
    loadPermissions();
  }, []);

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await getRoles('wolin');
      setRoles(data.roles || []);
    } catch (err) {
      message.error('加载角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPermissions = async () => {
    try {
      const data = await getPermissions();
      setPermissions(data.permissions || []);
    } catch (err) {
      console.error('Failed to load permissions');
    }
  };

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue(role);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRole) {
        await updateRolePermissions(editingRole.name, values.permissions, 'wolin');
        message.success('权限更新成功');
      } else {
        await createRole({ ...values, source_module: 'wolin' });
        message.success('角色创建成功');
      }
      setModalVisible(false);
      loadRoles();
    } catch (err) {
      message.error('保存失败');
    }
  };

  const columns = [
    { title: '角色名', dataIndex: 'name', key: 'name' },
    { title: '显示名', dataIndex: 'display_name', key: 'display_name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '权限', dataIndex: 'permissions', key: 'permissions', render: (perms: string[]) => perms?.join(', ') },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, role: Role) => (
        <Button size="small" onClick={() => handleEdit(role)}>编辑权限</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>角色管理</h2>
      <Button type="primary" onClick={handleCreate} style={{ marginBottom: 16 }}>创建角色</Button>
      <Table columns={columns} dataSource={roles} loading={loading} rowKey="id" />

      <Modal
        title={editingRole ? '编辑权限' : '创建角色'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          {!editingRole && (
            <>
              <Form.Item name="name" label="角色标识" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="description" label="描述">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          <Form.Item name="permissions" label="权限" rules={[{ required: true }]}>
            <Checkbox.Group>
              {permissions.map((perm) => (
                <Checkbox key={perm} value={perm}>{perm}</Checkbox>
              ))}
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 3: Add to componentMap**

Already registered.

- [ ] **Step 4: Build and verify**

Run: `cd Wolin/frontend/react && pnpm build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add Wolin/frontend/react/apps/admin/src/pages/roles/
git add Wolin/frontend/react/apps/admin/src/api/roles.ts
git commit -m "feat: add RoleManager page with permission config"
```

---

## Task 10: MenuManager Page

**Files:**
- Create: `Wolin/frontend/react/apps/admin/src/pages/menus/MenuManager.tsx`
- Create: `Wolin/frontend/react/apps/admin/src/api/menus.ts`

**Interfaces:**
- Consumes: Backend `/api/auth/menus` endpoints
- Produces: Menu management UI with tree view, create, edit, delete, sort

- [ ] **Step 1: Create menus API module**

Create `Wolin/frontend/react/apps/admin/src/api/menus.ts`:

```typescript
import { apiClient } from '@interview/shared';

export interface Menu {
  id: number;
  parent_id?: number;
  name: string;
  path: string;
  component: string;
  icon?: string;
  permission?: string;
  sort_order: number;
  is_visible: boolean;
  children: Menu[];
}

export async function getMenus(sourceModule: string) {
  const res = await apiClient.get('/api/auth/menus', { params: { source_module: sourceModule } });
  return res.data.data;
}

export async function createMenu(data: Partial<Menu> & { source_module: string }) {
  const res = await apiClient.post('/api/auth/menus', data);
  return res.data;
}

export async function updateMenu(id: number, data: Partial<Menu>) {
  const res = await apiClient.put(`/api/auth/menus/${id}`, data);
  return res.data;
}

export async function deleteMenu(id: number) {
  const res = await apiClient.delete(`/api/auth/menus/${id}`);
  return res.data;
}
```

- [ ] **Step 2: Create MenuManager page**

Create `Wolin/frontend/react/apps/admin/src/pages/menus/MenuManager.tsx`:

```typescript
import { useState, useEffect } from 'react';
import { Tree, Button, Modal, Form, Input, InputNumber, Select, message, Popconfirm } from 'antd';
import { getMenus, createMenu, updateMenu, deleteMenu, type Menu } from '../../api/menus';

export default function MenuManager() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMenu, setEditingMenu] = useState<Menu | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadMenus();
  }, []);

  const loadMenus = async () => {
    setLoading(true);
    try {
      const data = await getMenus('wolin');
      setMenus(data.menus || []);
    } catch (err) {
      message.error('加载菜单失败');
    } finally {
      setLoading(false);
    }
  };

  const convertToTreeData = (menus: Menu[]): any[] => {
    return menus.map((menu) => ({
      key: menu.id,
      title: `${menu.name} (${menu.path})`,
      children: menu.children ? convertToTreeData(menu.children) : [],
    }));
  };

  const handleCreate = () => {
    setEditingMenu(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (menuId: number) => {
    const findMenu = (menus: Menu[]): Menu | null => {
      for (const menu of menus) {
        if (menu.id === menuId) return menu;
        if (menu.children) {
          const found = findMenu(menu.children);
          if (found) return found;
        }
      }
      return null;
    };

    const menu = findMenu(menus);
    if (menu) {
      setEditingMenu(menu);
      form.setFieldsValue(menu);
      setModalVisible(true);
    }
  };

  const handleDelete = async (menuId: number) => {
    try {
      await deleteMenu(menuId);
      message.success('删除成功');
      loadMenus();
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingMenu) {
        await updateMenu(editingMenu.id, values);
        message.success('更新成功');
      } else {
        await createMenu({ ...values, source_module: 'wolin' });
        message.success('创建成功');
      }
      setModalVisible(false);
      loadMenus();
    } catch (err) {
      message.error('保存失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>菜单管理</h2>
      <Button type="primary" onClick={handleCreate} style={{ marginBottom: 16 }}>创建菜单</Button>

      <Tree
        treeData={convertToTreeData(menus)}
        defaultExpandAll
        style={{ marginBottom: 16 }}
      />

      <Modal
        title={editingMenu ? '编辑菜单' : '创建菜单'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="菜单名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="path" label="路由路径" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="component" label="组件 key" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="icon" label="图标">
            <Input placeholder="如 UserOutlined" />
          </Form.Item>
          <Form.Item name="permission" label="权限标识">
            <Input placeholder="如 user:manage" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 3: Add to componentMap**

Already registered.

- [ ] **Step 4: Build and verify**

Run: `cd Wolin/frontend/react && pnpm build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add Wolin/frontend/react/apps/admin/src/pages/menus/
git add Wolin/frontend/react/apps/admin/src/api/menus.ts
git commit -m "feat: add MenuManager page with tree view"
```

---

## Task 11: Final Integration Test

**Files:**
- No new files

**Interfaces:**
- Consumes: All previous tasks
- Produces: Verified end-to-end functionality

- [ ] **Step 1: Run initialization script**

Run: `python Wolin/scripts/init_wolin.py`
Expected: Creates roles, menus, and admin account

- [ ] **Step 2: Start backend server**

Run: `python Wolin/main.py` (or your usual backend startup command)
Expected: Backend starts on :8001

- [ ] **Step 3: Start frontend dev servers**

Run: `cd Wolin/frontend/react && python run_server.py`
Expected: User app on :3000, Admin app on :3001

- [ ] **Step 4: Test login flow**

1. Open http://localhost:3001
2. Login with `admin` / `admin123`
3. Expected: Redirected to admin dashboard, see 4 menu items

- [ ] **Step 5: Test menu visibility**

1. Verify all 4 menus are visible (记录管理, 用户管理, 角色管理, 菜单管理)
2. Click each menu and verify page loads

- [ ] **Step 6: Test user management**

1. Go to 用户管理 page
2. Verify user list loads
3. Test search functionality

- [ ] **Step 7: Test role management**

1. Go to 角色管理 page
2. Verify role list loads
3. Test edit permissions

- [ ] **Step 8: Test menu management**

1. Go to 菜单管理 page
2. Verify menu tree displays
3. Test create/edit/delete

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "feat: complete Wolin auth & menu management system

- Backend: MenuModel, menu CRUD API, /me/menus endpoint
- Frontend: Dynamic routing, sidebar rendering, 3 admin pages
- Initialization: Default menus + super_admin account
- All tests passing"
```

---

## Summary

**Total tasks:** 11
**Estimated time:** 7-10 days
**Key deliverables:**
- MenuModel with tree structure support
- Complete menu CRUD API
- Dynamic menu loading and routing
- 3 admin management pages (User/Role/Menu)
- Default Wolin admin account

**Next steps after implementation:**
- Add more icons to iconMap as needed
- Implement button-level permissions (already scaffolded)
- Add menu drag-and-drop sorting
- Implement menu caching for performance

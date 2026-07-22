# Wolin 认证与菜单管理系统设计

**日期**: 2026-07-22
**作者**: AI Assistant
**状态**: 已批准，待实施

---

## 1. 概述

### 1.1 目标

为 Wolin 面试系统实现完整的认证、授权和动态菜单管理系统：
- 对接后端真实认证接口（登录/注册）
- 基于角色的动态菜单配置
- 管理后台支持用户管理、角色管理、菜单管理
- 用户注册时自动关联 Wolin 模块（`source_module="wolin"`）

### 1.2 核心需求

| 需求 | 说明 |
|------|------|
| 真实认证 | 前端从 mock 模式切换到 API 模式，对接 `/api/auth/*` |
| Wolin 归属 | 用户注册时 `source_module="wolin"`，数据按模块隔离 |
| 动态菜单 | 管理员可配置每个角色可见的菜单树，前端动态渲染 |
| 角色权限 | 5 个内置角色：super_admin / admin / moderator / user / guest |
| 数据隔离 | 不做数据级隔离，菜单权限控制可见性 |
| 默认账号 | 系统初始化时创建 Wolin 模块的 super_admin 账号 |

### 1.3 非目标

- 用户端（:3000）保持公开，无需登录
- 不做按钮级权限控制（但预留扩展点）
- 不做 WebSocket 实时推送菜单变更

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  User App    │  │  Admin App   │  │ Shared Pkg   │  │
│  │  (Public)    │  │  (Auth)      │  │              │  │
│  │  :3000       │  │  :3001       │  │ - AuthProv   │  │
│  │              │  │              │  │ - DynRouter  │  │
│  │              │  │ - Login      │  │ - usePerm    │  │
│  │              │  │ - Records    │  │ - Toast      │  │
│  │              │  │ - Users      │  │              │  │
│  │              │  │ - Roles      │  │              │  │
│  │              │  │ - Menus      │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓ HTTP
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Base/Api/authApi.py                             │   │
│  │  - POST /api/auth/register                       │   │
│  │  - POST /api/auth/login                          │   │
│  │  - GET  /api/auth/me                             │   │
│  │  - GET  /api/auth/me/menus  ← 新增               │   │
│  │  - CRUD /api/auth/menus     ← 新增               │   │
│  │  - CRUD /api/auth/roles                          │   │
│  │  - CRUD /api/auth/users                          │   │
│  └──────────────────────────────────────────────────┘   │
│                           ↓                              │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Base/Models/                                    │   │
│  │  - UserModel (base_user)                         │   │
│  │  - RoleModel (base_role)                         │   │
│  │  - UserRoleModel (base_user_role)                │   │
│  │  - MenuModel (base_menu)  ← 新增                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户登录:
  1. 前端 POST /api/auth/login {username, password, source_module="wolin"}
  2. 后端验证 → 返回 {access_token, refresh_token, user_info}
  3. 前端存储 token 到 localStorage
  4. 前端调用 GET /api/auth/me/menus → 获取菜单树
  5. 前端动态渲染侧边栏 + 动态路由

菜单渲染:
  1. 后端查询用户所有角色的 permissions 并集
  2. 查询 source_module="wolin" 的所有菜单
  3. 过滤：permission 为空 OR permission 在并集中
  4. 组装成树形结构返回
  5. 前端根据 component 字段从 componentMap 加载组件
```

### 2.3 模块分工

| 层 | 职责 | 位置 |
|---|---|---|
| **Base 模块** | 用户/角色/权限/菜单 的模型、服务、API | `Base/Models/`, `Base/Service/`, `Base/Api/` |
| **Wolin 模块** | 业务数据（面试记录等） | `Wolin/` |
| **前端 shared** | AuthProvider、动态菜单渲染、路由守卫 | `packages/shared/src/` |
| **前端 admin** | 管理页面：用户/角色/菜单/记录管理 | `apps/admin/src/` |
| **前端 user** | 保持公开，无需改动 | `apps/user/src/` |

---

## 3. 数据库设计

### 3.1 MenuModel（新增）

**文件**: `Base/Models/menuModel.py`
**表名**: `base_menu`

```sql
CREATE TABLE `base_menu` (
  `id`            INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `parent_id`     INT DEFAULT NULL,              -- 父菜单 ID，NULL=顶级（无外键）
  `name`          VARCHAR(50) NOT NULL,          -- 菜单名称（如"用户管理"）
  `path`          VARCHAR(200) NOT NULL,         -- 路由路径（如"/users"）
  `component`     VARCHAR(200) NOT NULL,         -- 前端组件 key（如"pages/users/UserList"）
  `icon`          VARCHAR(50),                   -- 图标标识（如"UserOutlined"）
  `permission`    VARCHAR(100),                  -- 权限标识（如"user:manage"），空=所有用户可见
  `sort_order`    INT NOT NULL DEFAULT 0,        -- 排序权重
  `is_visible`    TINYINT(1) NOT NULL DEFAULT 1, -- 是否在侧边栏显示
  `source_module` VARCHAR(50) NOT NULL DEFAULT 'default',
  `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE,
  INDEX `idx_parent` (`parent_id`),
  INDEX `idx_module` (`source_module`)
);
```

**设计要点**:
- `parent_id` 无外键约束，仅逻辑关联
- `permission` 可为空 → 空表示所有登录用户可见
- `component` 是前端 componentMap 的 key，不是直接的文件路径
- `source_module` 隔离不同模块的菜单配置

### 3.2 内置角色（已有）

| 角色 | 权限 | 默认可见菜单 |
|------|------|-------------|
| `super_admin` | 所有权限 | 所有菜单 |
| `admin` | user:manage, user:read, content:*, module:manage, data:export | 记录管理 + 用户管理 + 角色管理 |
| `moderator` | user:read, content:manage, content:read | 记录管理 |
| `user` | user:read, content:read | 记录管理 |
| `guest` | content:read | （无） |

### 3.3 默认菜单初始化

Wolin 模块启动时自动创建以下菜单：

| 菜单 | path | component | permission | sort | icon |
|------|------|-----------|------------|------|------|
| 📋 记录管理 | `/records` | `pages/records/RecordManager` | `content:manage` | 1 | `TableOutlined` |
| 👥 用户管理 | `/users` | `pages/users/UserManager` | `user:manage` | 2 | `UserOutlined` |
| 🎭 角色管理 | `/roles` | `pages/roles/RoleManager` | `role:manage` | 3 | `TeamOutlined` |
| 📁 菜单管理 | `/menus` | `pages/menus/MenuManager` | `system:config` | 4 | `MenuOutlined` |

### 3.4 默认管理员账号

系统初始化时创建 Wolin 模块的超级管理员：

```python
# Wolin/scripts/init_admin.py
AuthService.register(
    username="admin",
    password="admin123",
    source_module="wolin",
    role_name="super_admin"
)
```

---

## 4. 后端 API 设计

### 4.1 新增接口

#### 4.1.1 获取当前用户菜单

```
GET /api/auth/me/menus
Authorization: Bearer <token>
响应: { "menus": [菜单树] }
```

**逻辑**:
1. 从 JWT 解析 user_id 和 source_module
2. 查询用户所有角色的 permissions 并集
3. 查询 source_module 的所有菜单
4. 过滤：`permission` 为空 OR `permission` 在并集中
5. 组装成树形结构（parent_id → children）
6. 按 `sort_order` 排序

#### 4.1.2 菜单管理（需 `system:config` 权限）

| Method | Path | 说明 | 请求体 |
|--------|------|------|--------|
| `GET` | `/api/auth/menus` | 获取菜单列表 | query: `source_module` |
| `POST` | `/api/auth/menus` | 创建菜单 | `CreateMenuRequest` |
| `PUT` | `/api/auth/menus/{id}` | 更新菜单 | `UpdateMenuRequest` |
| `DELETE` | `/api/auth/menus/{id}` | 删除菜单（含子菜单） | - |
| `PUT` | `/api/auth/menus/sort` | 批量更新排序 | `{items: [{id, sort_order}]}` |

### 4.2 现有接口调整

| 接口 | 变更 |
|------|------|
| `POST /api/auth/register` | 已有 `source_module` 参数，Wolin 前端传 `"wolin"` |
| `POST /api/auth/login` | 响应可选附带 `menus` 字段（减少一次请求） |
| `GET /api/auth/roles` | 返回角色时附带 `menu_count` 字段 |

### 4.3 菜单树响应格式

```json
{
  "menus": [
    {
      "id": 1,
      "parent_id": null,
      "name": "记录管理",
      "path": "/records",
      "component": "pages/records/RecordManager",
      "icon": "TableOutlined",
      "permission": "content:manage",
      "sort_order": 1,
      "is_visible": true,
      "children": []
    },
    {
      "id": 5,
      "parent_id": null,
      "name": "系统设置",
      "path": "/system",
      "component": "Layout",
      "icon": "SettingOutlined",
      "permission": null,
      "sort_order": 5,
      "is_visible": true,
      "children": [
        {
          "id": 2,
          "parent_id": 5,
          "name": "用户管理",
          "path": "/system/users",
          "component": "pages/users/UserManager",
          "icon": "UserOutlined",
          "permission": "user:manage",
          "sort_order": 1,
          "is_visible": true,
          "children": []
        }
      ]
    }
  ]
}
```

---

## 5. 前端设计

### 5.1 Auth 切换

**文件**: `apps/admin/.env`
```
VITE_AUTH_MODE=api   # 从 mock 改为 api
```

**删除**: `packages/shared/src/api/auth.ts` 中的 `MockAuthStrategy`（保留文件但不再使用）

### 5.2 动态菜单加载

**新增**: `packages/shared/src/api/menus.ts`
```ts
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
  return res.data.menus;
}
```

### 5.3 AuthProvider 增强

**修改**: `packages/shared/src/auth/AuthProvider.tsx`

新增状态和方法：
```ts
interface AuthContextType {
  user: User | null;
  ready: boolean;
  menus: MenuItem[];
  login: (form: LoginForm) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}
```

**逻辑**:
- 登录成功后调用 `fetchUserMenus()` 存入 context
- 每次 mount 时重新获取菜单（支持管理员修改后刷新可见）
- `hasPermission(perm)` 检查 `user.permissions.includes(perm)`

### 5.4 动态路由

**新增**: `packages/shared/src/router/DynamicRouter.tsx`

```tsx
// 根据菜单树动态生成路由
// 从 componentMap 查找组件，用 React.lazy 加载
```

**修改**: `apps/admin/src/App.tsx`
- 移除硬编码路由
- 用 `<DynamicRouter menus={menus} />` 替代

### 5.5 组件映射表

**新增**: `apps/admin/src/router/componentMap.ts`
```ts
import { lazy } from 'react';

export const componentMap = {
  'pages/records/RecordManager': lazy(() => import('../pages/records/RecordManager')),
  'pages/users/UserManager': lazy(() => import('../pages/users/UserManager')),
  'pages/roles/RoleManager': lazy(() => import('../pages/roles/RoleManager')),
  'pages/menus/MenuManager': lazy(() => import('../pages/menus/MenuManager')),
};
```

**白名单机制**: 只有 componentMap 中注册的组件才能被加载，防止组件路径注入攻击。

### 5.6 侧边栏动态渲染

**修改**: `apps/admin/src/components/AdminLayout.tsx`

- 从 `useAuth().menus` 获取菜单树
- 递归渲染 `<Menu>` 组件（支持多级嵌套）
- 图标根据 `icon` 字段从 `@ant-design/icons` 动态加载

### 5.7 新增管理页面

#### 5.7.1 UserManager（用户管理）

**文件**: `apps/admin/src/pages/users/UserManager.tsx`

**功能**:
- 用户列表（表格展示）
- 搜索（按用户名、邮箱、手机号）
- 启禁用用户（修改 status）
- 重置密码
- 分配角色（弹窗选择角色）

**API 调用**:
- `GET /api/auth/users` - 列表
- `PUT /api/auth/users/status` - 启禁用
- `POST /api/auth/users/reset-password` - 重置密码
- `POST /api/auth/roles/set` - 分配角色

#### 5.7.2 RoleManager（角色管理）

**文件**: `apps/admin/src/pages/roles/RoleManager.tsx`

**功能**:
- 角色列表
- 创建/编辑角色（名称、描述、权限）
- 配置角色权限（复选框选择 permissions）
- 查看角色用户数

**API 调用**:
- `GET /api/auth/roles` - 列表
- `POST /api/auth/roles` - 创建
- `PUT /api/auth/roles/permissions` - 更新权限

#### 5.7.3 MenuManager（菜单管理）

**文件**: `apps/admin/src/pages/menus/MenuManager.tsx`

**功能**:
- 菜单树展示（可展开/折叠）
- 创建/编辑菜单（名称、路径、组件、图标、权限、排序）
- 删除菜单（级联删除子菜单）
- 拖拽排序（可选，初期用数字输入）

**API 调用**:
- `GET /api/auth/menus` - 列表
- `POST /api/auth/menus` - 创建
- `PUT /api/auth/menus/{id}` - 更新
- `DELETE /api/auth/menus/{id}` - 删除
- `PUT /api/auth/menus/sort` - 排序

---

## 6. 安全设计

### 6.1 组件路径注入防护

**风险**: 管理员被黑客控制，创建恶意 `component` 路径

**防护**:
- 前端 `componentMap` 是白名单，只加载已注册的组件
- 后端 `component` 字段只作为 key，不直接拼接到 `import()` 路径
- 即使 `component` 被篡改，也无法加载未注册的模块

### 6.2 权限校验

**服务端**:
- 所有管理接口使用 `require_permission()` 装饰器
- 菜单管理接口需要 `system:config` 权限
- 用户管理接口需要 `user:manage` 权限
- 角色管理接口需要 `role:manage` 权限

**客户端**:
- `RequireAuth` 组件检查 `user.is_admin` 或 `hasPermission()`
- 页面内按钮用 `hasPermission()` 控制显示（预留扩展）

### 6.3 Token 管理

- Access Token 有效期 30 分钟
- Refresh Token 有效期 7 天
- 401 响应时自动清除 token 并跳转登录页
- 暂不实现自动刷新（后续可优化）

---

## 7. 性能优化

### 7.1 菜单缓存

**后端**:
- Redis 缓存菜单树（key: `menus:{source_module}`）
- 菜单更新时清除缓存

**前端**:
- 登录后缓存菜单到 localStorage
- 每次 mount 时重新获取（保证最新）
- 可选：设置 5 分钟缓存过期时间

### 7.2 懒加载

- 所有管理页面使用 `React.lazy()` 懒加载
- 路由切换时只加载对应组件
- 减少首屏加载时间

---

## 8. 数据迁移

### 8.1 现有用户处理

- Wolin 前端登录时传 `source_module="wolin"`
- 后端根据 `username + source_module` 查找用户
- 如果用户存在但 `source_module` 不匹配，提示"该账号不属于 Wolin 模块"
- 如果用户不存在，提示注册

### 8.2 初始化脚本

**文件**: `Wolin/scripts/init_wolin.py`

```python
# 1. 确保 Wolin 模块的内置角色存在
RoleModel.ensure_builtin_roles("wolin")

# 2. 创建默认菜单
MenuModel.ensure_default_menus("wolin")

# 3. 创建默认管理员
AuthService.register(
    username="admin",
    password="admin123",
    source_module="wolin",
    role_name="super_admin"
)
```

---

## 9. 扩展性设计

### 9.1 按钮级权限（预留）

**前端**:
```tsx
const { hasPermission } = useAuth();
{hasPermission('user:delete') && <Button>删除</Button>}
```

**后端**:
```python
@router.delete("/users/{id}")
async def delete_user(user = Depends(require_permission("user:delete"))):
    ...
```

### 9.2 多语言菜单（预留）

- `MenuModel` 新增 `name_i18n: JSON` 字段
- 前端根据 `navigator.language` 选择语言

### 9.3 菜单图标库（预留）

- 支持自定义 SVG 图标
- 上传图标到 OSS，菜单表存储 URL

---

## 10. 测试计划

### 10.1 后端测试

- [ ] MenuModel CRUD 测试
- [ ] 菜单树组装逻辑测试
- [ ] 权限过滤逻辑测试
- [ ] API 接口集成测试

### 10.2 前端测试

- [ ] 登录流程测试
- [ ] 动态菜单渲染测试
- [ ] 权限控制测试（hasPermission）
- [ ] 管理页面功能测试

### 10.3 端到端测试

- [ ] 注册 → 登录 → 查看菜单 → 访问页面
- [ ] 管理员配置菜单 → 用户刷新 → 菜单更新
- [ ] 超级管理员分配角色 → 用户权限变化

---

## 11. 实施计划

### Phase 1: 后端基础（2-3 天）

- [ ] 创建 MenuModel
- [ ] 实现菜单 CRUD API
- [ ] 实现 `/me/menus` 接口
- [ ] 编写初始化脚本

### Phase 2: 前端 Auth（1-2 天）

- [ ] 切换为 API 模式
- [ ] 增强 AuthProvider（menus + hasPermission）
- [ ] 实现动态菜单加载

### Phase 3: 前端页面（3-4 天）

- [ ] 实现动态路由
- [ ] 实现 UserManager 页面
- [ ] 实现 RoleManager 页面
- [ ] 实现 MenuManager 页面

### Phase 4: 集成测试（1 天）

- [ ] 端到端测试
- [ ] 性能测试
- [ ] 安全测试

**总计**: 7-10 天

---

## 12. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 菜单配置复杂度高 | 中 | 中 | 提供默认配置，简化初期使用 |
| 前端动态路由性能 | 低 | 低 | 懒加载 + 代码分割 |
| 权限配置错误 | 中 | 高 | 提供权限模板，限制 super_admin 数量 |
| 数据迁移问题 | 低 | 中 | 提供迁移脚本，手动验证 |

---

## 13. 附录

### 13.1 权限常量定义

**文件**: `Base/Models/roleModel.py`

```python
class Permission:
    USER_MANAGE = "user:manage"
    USER_READ = "user:read"
    ROLE_MANAGE = "role:manage"
    CONTENT_MANAGE = "content:manage"
    CONTENT_READ = "content:read"
    SYSTEM_CONFIG = "system:config"
    MODULE_MANAGE = "module:manage"
    DATA_EXPORT = "data:export"
```

### 13.2 图标映射

**文件**: `apps/admin/src/utils/iconMap.ts`

```ts
import * as Icons from '@ant-design/icons';

export const iconMap: Record<string, ComponentType> = {
  'UserOutlined': Icons.UserOutlined,
  'TeamOutlined': Icons.TeamOutlined,
  'TableOutlined': Icons.TableOutlined,
  'MenuOutlined': Icons.MenuOutlined,
  'SettingOutlined': Icons.SettingOutlined,
  // ... 更多图标
};
```

---

**文档结束**

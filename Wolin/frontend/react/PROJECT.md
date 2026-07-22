# AI 面试分析系统 - 前端项目文档

> **目标读者**：AI 助手 / 新加入的开发者。读完本文档即可了解整个 React 前端项目的架构、文件职责、数据流与开发约定，无需额外上下文。

---

## 1. 项目概述

| 维度 | 说明 |
|---|---|
| **项目名称** | AI 面试分析系统（Interview Analysis System） |
| **定位** | 基于 AI 的面试录音分析平台的前端界面。用户上传面试录音 + 简历，后端 AI 自动分析并生成报告；同时提供模拟面试对话、摄像头测试等功能。 |
| **所属分支** | `Education`（教育项目分支） |
| **技术栈** | React 19 + TypeScript 6 + Vite 8 + react-router-dom 7 |
| **UI 方案** | 纯 CSS（无 UI 组件库），暗色主题 + 玻璃拟态设计，响应式布局 |
| **HTTP 客户端** | Axios |
| **包管理** | npm（有 package-lock.json） |
| **开发端口** | 3000（Vite dev server） |
| **后端地址** | `http://localhost:8001`（通过 Vite proxy 代理） |

---

## 2. 目录架构

```
Wolin/frontend/react/
├── index.html                    # 入口 HTML（标题：面试分析系统）
├── package.json                  # 依赖与脚本定义
├── vite.config.ts                # Vite 配置（端口、proxy、@/ 别名）
├── tsconfig.json                 # TypeScript 总配置（引用 app + node）
├── tsconfig.app.json             # 前端 TS 配置（ES2023, path alias @/）
├── tsconfig.node.json            # Node 端 TS 配置（vite.config 等）
├── eslint.config.js              # ESLint 配置（TS + React Hooks + Refresh）
├── public/
│   ├── favicon.svg               # 站点图标
│   └── icons.svg                 # 图标集合
├── src/
│   ├── main.tsx                  # 应用入口（挂载 React 根组件）
│   ├── App.tsx                   # 路由 + 侧边栏布局
│   ├── index.css                 # 全局样式（主题变量 + 所有页面样式）
│   ├── types/
│   │   └── index.ts              # TypeScript 类型定义
│   ├── api/
│   │   ├── client.ts             # Axios 实例（baseURL 为空，10min 超时）
│   │   ├── analysis.ts           # 面试分析提交 API
│   │   ├── interview.ts          # 模拟面试相关 API（获取问题、提交回答、语音转文字）
│   │   └── records.ts            # 记录管理 CRUD API
│   ├── components/
│   │   ├── FileUploadProgress.tsx # 文件上传进度条组件
│   │   └── Toast.tsx             # 全局 Toast 提示（DOM 操作方式）
│   ├── hooks/
│   │   └── useFileUpload.ts      # 文件上传状态管理 Hook
│   └── pages/
│       ├── InterviewAnalysis.tsx  # 面试分析页（上传音频+简历 → 提交分析）
│       ├── CameraTest.tsx         # 摄像头测试页（摄像头 + 按住录音 → ASR）
│       ├── InterviewChat.tsx      # 模拟面试对话页（交互式面试）
│       └── InterviewRecordManager.tsx # 记录管理页（CRUD + 详情查看）
└── dist/                          # 构建产物（已 gitignore）
```

---

## 3. 整体架构

### 3.1 路由与布局

- **路由方案**：`HashRouter`（URL 格式 `/#/path`），不使用 BrowserRouter
- **布局**：左侧侧边栏（可折叠）+ 右侧主内容区
- **页面加载**：所有页面组件使用 `React.lazy()` + `Suspense` 懒加载

**路由表：**

| 路径 | 页面组件 | 导航栏标签 |
|---|---|---|
| `/` | `InterviewAnalysis` | 📊 面试分析 |
| `/record-manager` | `InterviewRecordManager` | 📋 记录管理 |
| `/interview-chat` | `InterviewChat` | 🎤 模拟面试 |
| `/camera-test` | `CameraTest` | 📷 摄像头测试 |

### 3.2 数据流

```
用户操作 → 页面组件（state） → api/*.ts（Axios 封装）
                                  ↓
                        Vite Proxy (/interview → localhost:8001)
                                  ↓
                            FastAPI 后端
```

所有 API 请求通过 `src/api/client.ts` 的统一 Axios 实例发出，响应拦截器仅做错误日志。

### 3.3 样式方案

- **单文件 CSS**：所有样式集中在 `src/index.css`（~2200 行）
- **CSS 变量主题**：`:root` 定义了完整的暗色主题变量体系
- **主色调**：深蓝背景 + 青色/蓝色/紫色渐变强调色
- **字体**：Inter（正文）+ JetBrains Mono（代码/等宽）
- **动画**：fadeInUp、shimmer（标题渐变流动）、recording-pulse 等
- **响应式断点**：1100px、900px、768px

---

## 4. 逐文件详解

### 4.1 入口文件

#### `index.html`
- HTML5 入口，`lang="zh-CN"`
- 引入两个外部字体（Clash Display、Satoshi，来自 fontshare）
- 挂载点：`<div id="root">`

#### `src/main.tsx`
- 标准 React 19 入口：`createRoot` + `StrictMode`
- 引入全局样式 `index.css`
- 渲染 `<App />`

#### `src/App.tsx`
- **Layout 组件**：内部定义，包含侧边栏 + 路由区域
- **侧边栏**：4 个导航项，使用 `NavLink` 高亮当前路由，支持折叠（`collapsed` state）
- **路由区域**：每个路由用 `<Suspense>` 包裹，fallback 为居中加载动画
- **导出**：`default export App`，内部用 `HashRouter` 包裹 `Layout`

---

### 4.2 类型定义 — `src/types/index.ts`

| 类型名 | 说明 |
|---|---|
| `InterviewRecord` | 面试记录实体，含 id、uuid、用户信息、状态（processing/completed/failed）、音频文本、分析结果、QA 数据等 |
| `InterviewQuestion` | 面试问题：`{ question: string; audio_url: string }` |
| `PaginatedResponse<T>` | 分页响应：`{ status_code, data: { items, total, page, page_size } }` |
| `SingleResponse<T>` | 单条响应：`{ status_code, data: T }` |
| `DownloadFileItem` | 文件下载项：`{ url, label, file_type }` |

---

### 4.3 API 层 — `src/api/`

#### `client.ts`
- 创建 Axios 实例，`baseURL: ''`（依赖 Vite proxy）
- 超时：10 分钟（大文件上传需要）
- 响应拦截器：错误时 `console.error` 并 reject

#### `analysis.ts`
| 函数 | 方法 | 路径 | 说明 |
|---|---|---|---|
| `submitAnalysis(formData, onProgress?)` | POST | `/interview/interview_analysis` | 提交面试分析（multipart/form-data，含音频+简历+用户信息），支持上传进度回调 |

#### `interview.ts`
| 函数 | 方法 | 路径 | 说明 |
|---|---|---|---|
| `getInterviewQuestions(uuid)` | GET | `/interview/interview/questions/{uuid}` | 获取面试问题列表（含 TTS 音频 URL） |
| `submitAnswer(formData)` | POST | `/interview/interview/audio_answer` | 提交面试回答音频（multipart） |
| `audioToText(formData)` | POST | `/interview/audio_to_text` | 音频转文字（ASR） |

#### `records.ts`
| 函数 | 方法 | 路径 | 说明 |
|---|---|---|---|
| `fetchRecords(params)` | GET | `/interview/records` | 分页查询记录（支持 user_name/company_name/email/status/日期范围 筛选） |
| `fetchRecord(id)` | GET | `/interview/record/{id}` | 获取单条记录详情 |
| `createRecord(data)` | POST | `/interview/record` | 创建记录（FormData） |
| `updateRecord(id, data)` | PUT | `/interview/record/{id}` | 更新记录 |
| `deleteRecord(id)` | DELETE | `/interview/record/{id}` | 删除记录 |
| `fetchDownloadUrls(id)` | GET | `/interview/record/{id}/download-url` | 获取记录关联文件的下载 URL |

---

### 4.4 通用组件 — `src/components/`

#### `FileUploadProgress.tsx`
- **职责**：显示文件上传进度条
- **Props**：`fileName`, `fileSize`, `state`（来自 `useFileUpload` hook）
- **状态**：idle → uploading（蓝色进度条 + 百分比）→ success（绿色）/ error（红色 + 错误信息）
- **工具函数**：`formatFileSize(bytes)` — 自动转换 B/KB/MB

#### `Toast.tsx`
- **职责**：全局 Toast 提示
- **方式**：直接操作 DOM（`document.getElementById('toast')`），非 React 组件
- **导出**：`show(msg, type)` — type 为 `info | success | error`
- **行为**：3 秒后自动隐藏，带 show/hide CSS 动画

> **注意**：Toast 需要在 `index.html` 或 App 中有一个 `<div id="toast">` 元素，当前代码中该元素通过 CSS `.toast` 类定义但未在 JSX 中显式渲染——依赖 DOM 中存在该元素。

---

### 4.5 自定义 Hook — `src/hooks/useFileUpload.ts`

- **职责**：封装文件上传的状态机逻辑
- **状态类型** `UploadState`：
  ```ts
  { status: 'idle' }
  | { status: 'uploading'; progress: number }
  | { status: 'success' }
  | { status: 'error'; message: string }
  ```
- **返回值**：`{ state, upload, reset }`
  - `upload(file, apiCall, formDataBuilder?)` — 执行上传，自动管理状态转换
  - `reset()` — 重置为 idle
- **默认 FormData 字段**：`audio_file`（可通过 `formDataBuilder` 自定义）

---

### 4.6 页面组件 — `src/pages/`

#### `InterviewAnalysis.tsx` — 面试分析页
- **功能**：用户填写邮箱、姓名、公司名，上传音频文件和简历文件，提交后后端 AI 分析并将结果发送至邮箱
- **表单字段**：
  - `receive_email`（邮箱）
  - `user_name`（姓名，禁止纯英文）
  - `company_name`（公司名，禁止纯英文）
  - `audio_file`（音频：mp3/wav/m4a/caf/aac/ogg/flac/amr）
  - `resume_file`（简历：pdf/doc/docx）
- **防重复提交**：使用 `useRef` 而非 `useState`（不受 React 异步批处理影响）
- **上传进度**：集成 `useFileUpload` hook + `FileUploadProgress` 组件
- **成功后**：清空表单 + 重置上传状态

#### `CameraTest.tsx` — 摄像头测试页
- **功能**：测试摄像头和麦克风，按住录音后调用 ASR 接口转写文字
- **布局**：左右分栏 — 左侧视频画面 + 控制按钮，右侧识别结果列表
- **核心流程**：
  1. 请求摄像头 + 麦克风权限（`getUserMedia`）
  2. 按住录音按钮 → `MediaRecorder` 录制音频（webm 格式）
  3. 松开 → 调用 `audioToText` API → 显示识别结果
- **权限错误处理**：区分 NotAllowedError / NotFoundError / NotReadableError 给出不同提示
- **TranscriptEntry**：`{ id, text, timestamp }` — 带时间戳的识别记录

#### `InterviewChat.tsx` — 模拟面试对话页
- **功能**：基于已有面试记录的交互式模拟面试。用户输入 record_uuid，加载该记录的面试问题，逐个播放（TTS 音频），用户按住录音回答，录音上传后 AI 识别并进入下一题。
- **流程**：
  1. 页面加载自动请求摄像头权限
  2. 用户输入 UUID → 点击「开始面试」→ 调用 `getInterviewQuestions(uuid)`
  3. 点击「开始面试」按钮 → 逐题展示：
     - 显示面试官问题 + 播放 TTS 音频（`new Audio(audio_url)`）
     - 用户按住录音 → 松开后调用 `submitAnswer`
     - 识别成功后显示回答文字 → 自动进入下一题
  4. 所有题目完成 → 显示「面试已结束」
- **消息类型**：`interviewer`（面试官，左侧）、`user`（用户，右侧）、`system`（系统提示，居中）
- **特殊状态**：
  - 音频播放中：气泡显示「正在播放语音...」
  - 摄像头未就绪时：禁用录音按钮
  - 面试官发言中：录音按钮显示「面试官发言中...」
- **音频播放**：使用 `useRef` 管理 Audio 实例，支持播放结束/失败/被拦截的状态处理

#### `InterviewRecordManager.tsx` — 记录管理页
- **功能**：面试记录的完整 CRUD + 详情查看，是最复杂的页面（~900 行）
- **主要功能**：
  - **搜索筛选**：可折叠的高级筛选面板（姓名、公司、邮箱、状态、日期范围）
  - **分页表格**：支持页码跳转、每页条数切换（10/20/50/100）
  - **详情弹窗**：5 个 Tab 页展示记录详情
  - **创建/编辑弹窗**：表单模态框（目前被注释，待鉴权功能完成后恢复）

**详情弹窗 Tab 结构：**

| Tab | 键名 | 内容 |
|---|---|---|
| 📋 基本信息 | `basic` | ID、状态、UUID（可复制）、姓名、邮箱、公司、音频时长、时间等 |
| 📎 文件下载 | `files` | 关联文件下载链接卡片（音频、文本、报告、简历等） |
| 💬 问答分析 | `qa` | 音频转写文本 + QA 问答对 + QA 分析（使用 `QaDisplay` 组件递归渲染） |
| 📊 报告内容 | `report` | 开篇语、简历分析、面试官评价、自我评价、结束语（可折叠 + 一键复制） |
| 🔧 原始数据 | `raw` | `resume_info` 和 `interview_json` 的结构化卡片展示（`DataCard` 组件） |

**内置辅助组件（均在同一文件内定义）：**
- `DataCard` — 智能数据卡片：自动识别数值型字段渲染进度条，嵌套对象自动折叠
- `QaDisplay` — Q&A 展示器：支持数组/对象/嵌套结构，自动识别 question/answer 字段
- `CopyableBlock` — 可复制文本块（hover 显示复制图标）
- `InlineCopyIcon` — 行内复制图标
- `SectionHeader` — 可折叠区块标题
- `CopyUuid` — UUID 复制组件

---

## 5. 后端 API 对照表

所有 API 路径均以 `/interview` 为前缀，通过 Vite proxy 转发到 `http://localhost:8001`。

| 方法 | 路径 | Content-Type | 用途 | 调用页面 |
|---|---|---|---|---|
| POST | `/interview/interview_analysis` | multipart/form-data | 提交面试分析任务 | InterviewAnalysis |
| GET | `/interview/interview/questions/{uuid}` | - | 获取面试问题 | InterviewChat |
| POST | `/interview/interview/audio_answer` | multipart/form-data | 提交面试回答音频 | InterviewChat |
| POST | `/interview/audio_to_text` | multipart/form-data | 音频转文字 | CameraTest |
| GET | `/interview/records` | - | 分页查询记录 | InterviewRecordManager |
| GET | `/interview/record/{id}` | - | 获取记录详情 | InterviewRecordManager |
| POST | `/interview/record` | FormData | 创建记录 | InterviewRecordManager |
| PUT | `/interview/record/{id}` | FormData | 更新记录 | InterviewRecordManager |
| DELETE | `/interview/record/{id}` | - | 删除记录 | InterviewRecordManager |
| GET | `/interview/record/{id}/download-url` | - | 获取文件下载 URL | InterviewRecordManager |

---

## 6. 开发约定

### 6.1 路径别名
- `@/` → `src/`（在 `tsconfig.app.json` 的 `paths` 和 `vite.config.ts` 的 `resolve.alias` 中同时配置）

### 6.2 Vite Proxy
```ts
proxy: {
  '/interview': {
    target: 'http://localhost:8001',
    changeOrigin: true,
  },
}
```
所有 `/interview` 开头的请求自动代理到后端。

### 6.3 CSS 主题变量
- 定义在 `:root` 中，全局可用
- 关键变量：
  - `--bg-primary: #0a0e27` — 主背景（深蓝）
  - `--accent-cyan: #00d4ff` — 主要强调色
  - `--gradient-main` — 青→紫→蓝 渐变
  - `--gradient-btn` — 蓝→紫 按钮渐变
  - `--font-sans` / `--font-mono` — 字体族
  - `--radius-sm/md/lg/xl` — 圆角 8/12/16/20px
  - `--transition-fast/normal/slow` — 150/250/400ms

### 6.4 页面布局约定
- `.page` 类：`flex: 1; overflow: hidden;` — 页面自身不滚动
- 每个页面必须自行提供内部滚动容器（如 `.chat-messages`、`.table-wrapper`）
- 新增页面如果忘记加内部滚动，内容会被静默裁切

### 6.5 组件规范
- 函数组件 + Hooks（无 class 组件）
- 导出方式：页面组件用 `export default`，工具组件用 `export function`
- 内联 SVG 图标（未使用图标库）

---

## 7. 依赖说明

### 生产依赖
| 包 | 版本 | 用途 |
|---|---|---|
| `react` | ^19.2.6 | UI 框架 |
| `react-dom` | ^19.2.6 | DOM 渲染 |
| `react-router-dom` | ^7.15.0 | 路由（HashRouter + NavLink） |
| `axios` | ^1.16.1 | HTTP 请求 |

### 开发依赖
| 包 | 版本 | 用途 |
|---|---|---|
| `vite` | ^8.0.12 | 构建工具 |
| `@vitejs/plugin-react` | ^6.0.1 | React 支持（Oxc） |
| `typescript` | ~6.0.2 | 类型检查 |
| `eslint` | ^10.3.0 | 代码检查 |
| `typescript-eslint` | ^8.59.2 | TS lint 规则 |
| `eslint-plugin-react-hooks` | ^7.1.1 | React Hooks 规则 |
| `eslint-plugin-react-refresh` | ^0.5.2 | Fast Refresh 兼容 |

---

## 8. 已知限制与待办

### 功能待恢复
- **创建/编辑记录按钮**：在 `InterviewRecordManager.tsx` 中被注释，标注「待鉴权完成后恢复」
- **删除记录**：API 已封装（`deleteRecord`），但页面未暴露删除按钮

### Toast 组件
- `Toast.tsx` 导出 `show()` 函数操作 DOM，但当前没有 `<div id="toast">` 元素在 JSX 中被渲染
- `InterviewChat.tsx` 使用了自实现的 inline toast（state-based），未依赖 `Toast.tsx`

### 鉴权
- 当前无登录/鉴权逻辑，所有接口直接调用
- 新增/编辑功能被注释，等待后端鉴权接口完成后恢复

### 构建脚本
```bash
npm run dev      # 启动开发服务器（端口 3000）
npm run build    # TypeScript 编译 + Vite 打包
npm run lint     # ESLint 检查
npm run preview  # 预览构建产物
```

---

## 9. 关键设计决策备注

1. **HashRouter 而非 BrowserRouter**：可能是为了在没有后端路由配置的情况下直接打开 HTML 文件也能工作
2. **单文件 CSS**：所有样式在 `index.css` 中，未使用 CSS Modules 或 CSS-in-JS，样式类名全局可见
3. **无状态管理库**：未使用 Redux/Zustand/Jotai，所有状态通过 `useState`/`useRef` 在组件内管理
4. **无 UI 组件库**：所有 UI（表格、弹窗、按钮、分页）均手写 CSS 实现
5. **FormData 上传**：所有文件上传使用 `multipart/form-data`，通过原生 `FormData` 构建
6. **防重复提交**：`InterviewAnalysis` 使用 `useRef` 而非 `useState` 做提交锁，避免 React 异步批处理导致的竞态

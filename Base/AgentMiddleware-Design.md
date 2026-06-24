# BaseAgent 可观测性、可评估性、安全性增强设计文档

> **版本**: v1.0  
> **日期**: 2026-06-23  
> **状态**: 设计完成，待实施

---

## 目录

1. [概述与目标](#1-概述与目标)
2. [整体架构](#2-整体架构)
3. [中间件基类设计](#3-中间件基类设计)
4. [可观测性中间件](#4-可观测性中间件)
5. [评估中间件](#5-评估中间件)
6. [安全中间件](#6-安全中间件)
7. [与 BaseAgent 集成](#7-与-baseagent-集成)
8. [数据库变更清单](#8-数据库变更清单)
9. [使用示例](#9-使用示例)
10. [实施计划](#10-实施计划)

---

## 1. 概述与目标

### 1.1 背景

当前 `BaseAgent` 基类具备基础的 Agent 能力（LLM 调用、工具注册、记忆管理、多种执行范式），但缺乏以下关键特性：

- **可观测性**：仅有基础日志，缺乏结构化追踪和指标收集
- **可评估性**：无评估框架，无法量化 Agent 输出质量和实验效果
- **安全性**：无安全防护，存在 prompt 注入、敏感信息泄露等风险

### 1.2 设计目标

| 目标 | 描述 |
|------|------|
| **轻量级** | 本地单机部署，日志写入文件，不依赖复杂监控系统 |
| **可选启用** | 采用中间件模式，按需启用，保持基类轻量 |
| **可扩展** | 评估框架支持从基础指标扩展到质量评估和 A/B 实验 |
| **完整安全** | 输入/输出/工具三层防护 |

### 1.3 设计原则

- **中间件链模式**：借鉴 Koa.js 洋葱模型，灵活组合功能
- **复用现有基础设施**：使用已有的 MySQL 持久化层（BaseModuleDBModel）
- **向后兼容**：不破坏现有 BaseAgent 接口

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent 执行流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户输入 ──→ MiddlewareChain.process()                         │
│                  │                                              │
│                  ├─→ LoggingMiddleware      (记录请求)          │
│                  │       │                                      │
│                  │       ↓                                      │
│                  ├─→ SafetyMiddleware       (输入安全检查)       │
│                  │       │                                      │
│                  │       ↓                                      │
│                  ├─→ MetricsMiddleware      (开始计时)          │
│                  │       │                                      │
│                  │       ↓                                      │
│                  └─→ EvalMiddleware         (记录上下文)        │
│                          │                                      │
│                          ↓                                      │
│                   ┌──────────────┐                              │
│                   │  Agent Core  │  ← BaseAgent.run()           │
│                   │  (LLM+Tools) │                              │
│                   └──────────────┘                              │
│                          │                                      │
│                          ↓ (逆向执行)                           │
│                                                                 │
│                  ┌─→ EvalMiddleware         (质量评估)          │
│                  │       │                                      │
│                  │       ↓                                      │
│                  ├─→ MetricsMiddleware      (记录指标)          │
│                  │       │                                      │
│                  │       ↓                                      │
│                  ├─→ SafetyMiddleware       (输出安全检查)       │
│                  │       │                                      │
│                  │       ↓                                      │
│                  └─→ LoggingMiddleware      (记录响应)          │
│                          │                                      │
│                          ↓                                      │
│                      最终输出                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 中间件执行顺序

| 阶段 | 中间件 | 职责 |
|------|--------|------|
| 请求 | LoggingMiddleware | 记录请求日志 |
| 请求 | SafetyMiddleware | 输入安全检查、脱敏 |
| 请求 | MetricsMiddleware | 开始计时 |
| 请求 | EvalMiddleware | 记录评估上下文 |
| 响应 | EvalMiddleware | 执行质量评估 |
| 响应 | MetricsMiddleware | 持久化指标到 MySQL |
| 响应 | SafetyMiddleware | 输出安全检查、PII 脱敏 |
| 响应 | LoggingMiddleware | 记录响应日志 |

---

## 3. 中间件基类设计

### 3.1 上下文对象

```python
class AgentContext(BaseModel):
    """中间件共享的上下文对象"""
    
    request_id: str           # 唯一请求 ID（UUID）
    user_input: str           # 用户输入
    agent_name: str           # Agent 名称
    start_time: float         # 开始时间（time.time()）
    output: str = ""          # Agent 输出
    duration_ms: int = 0      # 总耗时（毫秒）
    token_usage: Dict[str, int] = Field(default_factory=dict)  # token 使用
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)  # 工具调用记录
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 扩展元数据
    error: Optional[Exception] = None  # 错误信息
```

### 3.2 中间件抽象基类

```python
class Middleware(ABC):
    """中间件抽象基类"""
    
    @abstractmethod
    async def process_request(
        self, 
        ctx: AgentContext, 
        next: Callable
    ) -> None:
        """
        处理请求（进入时）
        
        Args:
            ctx: 上下文对象
            next: 下一个中间件
        """
        pass
    
    @abstractmethod
    async def process_response(
        self, 
        ctx: AgentContext
    ) -> None:
        """
        处理响应（返回时）
        
        Args:
            ctx: 上下文对象
        """
        pass
```

### 3.3 中间件链执行器

```python
class MiddlewareChain:
    """
    中间件链管理器
    
    采用洋葱模型：先进入的中间件，后处理响应
    """
    
    def __init__(self):
        self._middlewares: List[Middleware] = []
    
    def use(self, middleware: Middleware):
        """注册中间件"""
        self._middlewares.append(middleware)
    
    async def execute(
        self, 
        ctx: AgentContext, 
        handler: Callable
    ) -> AgentContext:
        """
        执行中间件链
        
        Args:
            ctx: 上下文对象
            handler: 核心处理逻辑
        """
        index = 0
        
        async def next():
            nonlocal index
            if index < len(self._middlewares):
                middleware = self._middlewares[index]
                index += 1
                await middleware.process_request(ctx, next)
            else:
                # 到达核心逻辑
                await handler(ctx)
            
            # 逆向执行响应处理
            if index > 0:
                index -= 1
                middleware = self._middlewares[index]
                await middleware.process_response(ctx)
        
        await next()
        return ctx
```

---

## 4. 可观测性中间件

### 4.1 LoggingMiddleware — 结构化日志

**功能**：使用 JSON 格式记录请求/响应日志，写入本地文件，支持按天轮转。

**日志文件**：`logs/agent/agent-trace.log`

**日志格式示例**：

```json
// 请求日志
{
    "timestamp": "2026-06-23T10:30:00.123456",
    "event": "request",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "NL2CypherAgent",
    "user_input": "查询所有学生的成绩",
    "metadata": {"user_id": "u123", "session_id": "s456"}
}

// 响应日志
{
    "timestamp": "2026-06-23T10:30:02.456789",
    "event": "response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "NL2CypherAgent",
    "duration_ms": 2333,
    "output": "MATCH (s:Student) RETURN s.name, s.score...",
    "tool_calls_count": 1,
    "success": true,
    "error": null
}
```

**配置参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `log_dir` | str | "logs/agent" | 日志目录 |
| `log_level` | str | "INFO" | 日志级别 |
| `log_request_body` | bool | True | 是否记录请求体 |
| `log_response_body` | bool | True | 是否记录响应体 |
| `max_body_length` | int | 1000 | 内容截断长度 |

### 4.2 MetricsMiddleware — 指标收集

**功能**：收集 Agent 运行指标，持久化到 MySQL（复用现有 BaseAgentCallLog 模型）。

**持久化模型**：
- 主记录：`BaseAgentCallLog` → `base_agent_call_log` 表
- 工具明细：`BaseAgentToolCallLog` → `base_agent_tool_call_log` 表

**收集的指标**：

| 指标 | 字段 | 描述 |
|------|------|------|
| 请求总数 | `id` | 自增主键 |
| Agent 名称 | `agent_name` | 执行 Agent 名称 |
| 用户/会话 | `user_id`, `session_id` | 来源追踪 |
| 耗时 | `duration_ms` | 总耗时（毫秒） |
| 状态 | `status` | success / failed / timeout |
| 迭代次数 | `iterations` | 工具调用循环次数 |
| Token 消耗 | `prompt_tokens`, `completion_tokens`, `total_tokens` | LLM token 使用 |
| 错误信息 | `error_msg` | 失败原因 |

**查询接口**：

```python
metrics = MetricsMiddleware()

# 获取最近 24 小时统计
stats = metrics.get_stats(agent_name="NL2CypherAgent", hours=24)
# 返回:
# {
#     "total_requests": 100,
#     "success_rate": 0.95,
#     "avg_duration_ms": 1200,
#     "p50_duration_ms": 800,
#     "p90_duration_ms": 2500,
#     "total_tokens": 50000
# }
```

---

## 5. 评估中间件

### 5.1 分层评估架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     EvalMiddleware 架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 3: A/B 实验层 (可选)                              │   │
│  │  - 实验分组、流量分配、效果对比                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↑                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 2: 质量评估层 (可选)                              │   │
│  │  - LLM-as-Judge、人工评分、多维度评分                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↑                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 1: 基础指标层 (内置)                              │   │
│  │  - 成功率、响应时间、token 消耗、工具调用次数            │   │
│  │  → 由 MetricsMiddleware 实现                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 评估器基类

```python
class BaseEvaluator(ABC):
    """评估器抽象基类"""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    async def evaluate(self, ctx: AgentContext) -> EvalResult:
        """执行评估"""
        pass
    
    @abstractmethod
    def is_applicable(self, ctx: AgentContext) -> bool:
        """判断是否适用于当前请求"""
        pass


class EvalResult(BaseModel):
    """评估结果"""
    evaluator_name: str
    score: float  # 0.0 ~ 1.0
    dimensions: Dict[str, float] = Field(default_factory=dict)  # 多维度评分
    feedback: str = ""  # 评估反馈
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 5.3 LLM-as-Judge 评估器

**功能**：使用另一个 LLM 评估 Agent 输出的质量。

**支持维度**：
- `accuracy` — 准确性
- `relevance` — 相关性
- `completeness` — 完整性
- `safety` — 安全性
- 自定义维度

**评估提示词模板**：

```
你是一个专业的 AI 输出质量评估专家。请评估以下 Agent 回答的质量。

## 用户输入
{user_input}

## Agent 回答
{output}

## 评估维度
请对以下维度分别打分（0-1 之间的小数）：
- accuracy
- relevance
- completeness

## 输出格式
请以 JSON 格式输出：
{
    "scores": {"维度名": 分数, ...},
    "overall_score": 总分,
    "feedback": "评估理由和改进建议"
}
```

### 5.4 A/B 实验评估器

**功能**：对比不同配置（模型/prompt/工具）的效果。

**流量分配**：基于 `request_id` 的 MD5 哈希，确保同一请求总是分配到同一变体。

```python
# 配置示例
evaluator = ABTestEvaluator(
    experiment_name="model_comparison",
    variants={
        "gpt4": {"model": "gpt-4", "temperature": 0.7},
        "qwen": {"model": "qwen-max", "temperature": 0.7},
    },
    traffic_split={"gpt4": 0.5, "qwen": 0.5}
)

# 获取变体配置
config = evaluator.get_variant_config(request_id)
# 返回: {"model": "gpt-4", "temperature": 0.7}

# 获取实验结果
results = evaluator.get_experiment_results()
# 返回:
# {
#     "gpt4": {"total_requests": 50, "success_rate": 0.96, "avg_duration_ms": 1500},
#     "qwen": {"total_requests": 50, "success_rate": 0.92, "avg_duration_ms": 1200}
# }
```

### 5.5 评估结果存储

评估结果持久化到新增的 `base_agent_eval_log` 表（见数据库变更清单）。

---

## 6. 安全中间件

### 6.1 安全防护架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    SafetyMiddleware 架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入阶段                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  InputGuard                                              │   │
│  │  ├─ PromptInjectionDetector   (Prompt 注入检测)          │   │
│  │  ├─ InputValidator            (输入格式/长度验证)        │   │
│  │  └─ SensitiveWordFilter       (敏感词过滤)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ToolGuard                                               │   │
│  │  ├─ ToolWhitelist             (工具白名单控制)           │   │
│  │  ├─ ArgumentValidator         (参数校验)                 │   │
│  │  └─ DangerousOperationDetector (危险操作拦截)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          ↓                                       │
│                    Agent Core 执行                               │
│                          ↓                                       │
│  输出阶段                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  OutputGuard                                             │   │
│  │  ├─ ContentModerator          (内容审核)                 │   │
│  │  ├─ PIIMasker                 (敏感信息脱敏)             │   │
│  │  └─ OutputValidator           (输出格式验证)             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 防护器基类

```python
class SafetyGuard(ABC):
    """安全防护器基类"""
    
    name: str = ""
    
    @abstractmethod
    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """检查内容"""
        pass


class GuardResult(BaseModel):
    """防护检查结果"""
    passed: bool = True
    reason: str = ""
    masked_content: Optional[str] = None  # 脱敏后的内容
    risk_level: str = "low"  # low, medium, high, critical


class SafetyException(Exception):
    """安全防护异常"""
    def __init__(self, reason: str, risk_level: str = "high"):
        self.reason = reason
        self.risk_level = risk_level
        super().__init__(f"[{risk_level}] {reason}")
```

### 6.3 Prompt 注入检测

**检测模式**：

```python
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|above)",
    r"forget\s+(all\s+)?(previous|above)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"act\s+as\s+(a|an|if)\s+",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"\bDAN\b",  # Do Anything Now
    r"jailbreak",
    r"bypass\s+(filter|restriction|safety)",
]
```

**行为**：检测到注入模式时，抛出 `SafetyException` 阻断请求。

### 6.4 敏感词过滤

**功能**：
- 支持自定义敏感词库
- 支持从文件加载
- 自动脱敏（替换为 `*`）

**行为**：脱敏但不阻断请求。

### 6.5 工具调用防护

**功能**：
- 工具白名单/黑名单控制
- 参数长度校验
- 危险操作拦截（DROP、DELETE、rm -rf 等）

**危险操作关键词**：

```python
DANGEROUS_OPERATIONS = [
    "drop", "delete", "truncate", "destroy",
    "rm -rf", "format", "shutdown", "reboot",
    "DROP TABLE", "DELETE FROM",
]
```

**行为**：检测到危险操作时，抛出 `SafetyException` 阻断执行。

### 6.6 PII 脱敏

**脱敏类型**：

| 类型 | 正则模式 | 示例 |
|------|----------|------|
| 手机号 | `1[3-9]\d{9}` | 138****5678 |
| 身份证号 | `\b\d{17}[\dXx]\b` | 11**********1234 |
| 邮箱 | `[\w.-]+@[\w.-]+\.\w+` | ab***@example.com |
| 银行卡号 | `\b\d{16,19}\b` | 6222**********1234 |
| IP 地址 | `(?:\d{1,3}\.){3}\d{1,3}` | 192.***.*.* |

**脱敏策略**：
- `partial` — 保留前后部分字符（默认）
- `full` — 全部替换为 `***`
- `hash` — 替换为 MD5 哈希前 8 位

**行为**：脱敏但不阻断输出。

---

## 7. 与 BaseAgent 集成

### 7.1 BaseAgent 扩展

```python
class BaseAgent(ABC):
    # ... 现有代码 ...
    
    def __init__(self, ...):
        # ... 现有初始化 ...
        self._middleware_chain = MiddlewareChain()
    
    def use(self, middleware: Middleware):
        """注册中间件"""
        self._middleware_chain.use(middleware)
    
    def run(self, user_input: str, **kwargs) -> AgentResult:
        """同步执行（保持向后兼容）"""
        # 如果没有中间件，走原有逻辑
        if not self._middleware_chain._middlewares:
            return self._run_legacy(user_input, **kwargs)
        
        # 有中间件时，走中间件链
        import asyncio
        return asyncio.run(self.arun(user_input, **kwargs))
    
    async def arun(self, user_input: str, **kwargs) -> AgentResult:
        """异步执行"""
        # 如果没有中间件，走原有逻辑
        if not self._middleware_chain._middlewares:
            return await self._arun_legacy(user_input, **kwargs)
        
        # 创建上下文
        ctx = AgentContext(
            request_id=str(uuid.uuid4()),
            user_input=user_input,
            agent_name=self.name,
            start_time=time.time(),
            metadata=kwargs
        )
        
        # 定义核心处理逻辑
        async def handler(ctx):
            result = await self._arun_legacy(ctx.user_input, **ctx.metadata)
            ctx.output = result.output
            ctx.duration_ms = result.duration_ms
            ctx.token_usage = result.token_usage or {}
            ctx.tool_calls = result.tool_calls
            if not result.success:
                ctx.error = Exception(result.error_msg)
        
        # 执行中间件链
        ctx = await self._middleware_chain.execute(ctx, handler)
        
        # 构建返回结果
        return AgentResult(
            success=ctx.error is None,
            output=ctx.output,
            tool_calls=ctx.tool_calls,
            duration_ms=ctx.duration_ms,
            error_msg=str(ctx.error) if ctx.error else None,
            metadata=ctx.metadata
        )
```

### 7.2 Token 统计集成

需要修改 `BaseAgent._call_llm()` 方法，捕获 token 使用信息：

```python
def _call_llm(self, messages: List[Dict[str, Any]]) -> Any:
    # ... 现有代码 ...
    response = self.llm.model_client.chat.completions.create(**kwargs)
    
    # 提取 token 使用信息
    if hasattr(response, 'usage') and response.usage:
        self._last_token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    
    return response
```

### 7.3 AgentResult 扩展

```python
class AgentResult(BaseModel):
    """Agent 单次运行的结果"""
    success: bool = True
    output: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    iterations: int = 0
    duration_ms: int = 0
    error_msg: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None  # 新增
    metadata: Optional[Dict[str, Any]] = None  # 新增
```

---

## 8. 数据库变更清单

> **重要**：以下是本次设计涉及的数据库表变更，请在实施前确认。

### 8.1 修改现有表：`base_agent_call_log`

**变更类型**：新增字段

**新增字段**：

| 字段名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `prompt_tokens` | INT UNSIGNED | 0 | Prompt tokens 消耗 |
| `completion_tokens` | INT UNSIGNED | 0 | Completion tokens 消耗 |
| `total_tokens` | INT UNSIGNED | 0 | 总 tokens 消耗 |

**变更 SQL**：

```sql
ALTER TABLE `base_agent_call_log`
ADD COLUMN `prompt_tokens` INT UNSIGNED DEFAULT 0 COMMENT 'Prompt tokens 消耗' AFTER `ai_model`,
ADD COLUMN `completion_tokens` INT UNSIGNED DEFAULT 0 COMMENT 'Completion tokens 消耗' AFTER `prompt_tokens`,
ADD COLUMN `total_tokens` INT UNSIGNED DEFAULT 0 COMMENT '总 tokens 消耗' AFTER `completion_tokens`;
```

### 8.2 新增表：`base_agent_eval_log`

**表名**：`base_agent_eval_log`  
**描述**：Agent 评估记录表

**表结构**：

```sql
CREATE TABLE `base_agent_eval_log` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `agent_call_id` BIGINT UNSIGNED COMMENT 'FK → base_agent_call_log.id',
    `evaluator_name` VARCHAR(100) COMMENT '评估器名称',
    `score` DECIMAL(5,4) COMMENT '总分（0-1）',
    `dimensions` JSON COMMENT '多维度评分',
    `feedback` TEXT COMMENT '评估反馈',
    `metadata` JSON COMMENT '额外元数据',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_agent_call_id` (`agent_call_id`),
    KEY `idx_evaluator_name` (`evaluator_name`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Agent 评估记录表';
```

### 8.3 变更汇总

| 操作 | 表名 | 描述 |
|------|------|------|
| ALTER | `base_agent_call_log` | 新增 3 个 token 统计字段 |
| CREATE | `base_agent_eval_log` | 新增评估记录表 |

---

## 9. 使用示例

### 9.1 基础使用 — 启用所有中间件

```python
from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.middlewares import (
    LoggingMiddleware,
    MetricsMiddleware,
    SafetyMiddleware,
    EvalMiddleware,
)

# 创建 Agent
agent = ReActAgent(
    llm=my_llm,
    name="MyAgent",
    tools=[my_tool],
)

# 注册中间件（按顺序）
agent.use(LoggingMiddleware(log_dir="logs/agent"))
agent.use(MetricsMiddleware(user_id="u123", session_id="s456"))
agent.use(SafetyMiddleware())

# 运行
result = agent.run("查询所有学生的成绩")
print(result.output)
```

### 9.2 启用质量评估

```python
from Base.Ai.middlewares import EvalMiddleware, LLMJudgeEvaluator

# 创建评估器
judge = LLMJudgeEvaluator(
    judge_llm=judge_llm,
    dimensions=["accuracy", "relevance", "completeness"],
)

# 创建评估中间件
eval_middleware = EvalMiddleware(evaluators=[judge])

# 注册
agent.use(eval_middleware)
```

### 9.3 启用 A/B 实验

```python
from Base.Ai.middlewares import ABTestEvaluator

# 配置实验
ab_evaluator = ABTestEvaluator(
    experiment_name="model_comparison",
    variants={
        "gpt4": {"model": "gpt-4"},
        "qwen": {"model": "qwen-max"},
    },
    traffic_split={"gpt4": 0.5, "qwen": 0.5}
)

# 获取当前请求的变体
variant_config = ab_evaluator.get_variant_config(request_id)

# 根据变体配置创建不同的 Agent
if variant_config["model"] == "gpt-4":
    agent = create_gpt4_agent()
else:
    agent = create_qwen_agent()
```

### 9.4 自定义安全防护

```python
from Base.Ai.middlewares import (
    SafetyMiddleware,
    PromptInjectionDetector,
    SensitiveWordFilter,
    ToolGuard,
    PIIMasker,
)

# 自定义输入防护
input_guards = [
    PromptInjectionDetector(
        custom_patterns=[r"custom_attack_pattern"],
        block_on_detect=True,
    ),
    SensitiveWordFilter(
        word_file="config/sensitive_words.txt",
        replace_char="*",
    ),
]

# 自定义工具防护
tool_guard = ToolGuard(
    allowed_tools=["search", "calculate"],  # 只允许这些工具
    max_argument_length=5000,
)

# 自定义输出防护
output_guards = [
    PIIMasker(
        enabled_types=["phone", "id_card", "email"],
        mask_strategy="partial",
    ),
]

# 创建安全中间件
safety = SafetyMiddleware(
    input_guards=input_guards,
    output_guards=output_guards,
    tool_guards=[tool_guard],
)

agent.use(safety)
```

### 9.5 仅启用部分功能

```python
# 只启用日志和指标
agent.use(LoggingMiddleware())
agent.use(MetricsMiddleware())

# 不启用安全和评估
```

---

## 10. 实施计划

### 10.1 阶段划分

| 阶段 | 内容 | 预估工作量 |
|------|------|------------|
| **Phase 1** | 中间件基类 + BaseAgent 集成 | 2-3 天 |
| **Phase 2** | LoggingMiddleware + MetricsMiddleware | 2-3 天 |
| **Phase 3** | SafetyMiddleware（输入/输出/工具防护） | 3-4 天 |
| **Phase 4** | EvalMiddleware（LLM-as-Judge + A/B 实验） | 3-4 天 |
| **Phase 5** | 数据库变更 + 测试 + 文档 | 2 天 |

### 10.2 文件结构

```
Base/Ai/
├── base/
│   ├── baseAgent.py          # 修改：添加中间件集成
│   └── ...
├── middlewares/               # 新增目录
│   ├── __init__.py
│   ├── base.py               # Middleware, AgentContext, MiddlewareChain
│   ├── logging.py            # LoggingMiddleware
│   ├── metrics.py            # MetricsMiddleware
│   ├── safety/               # 安全子模块
│   │   ├── __init__.py
│   │   ├── base.py           # SafetyGuard, GuardResult
│   │   ├── input_guards.py   # PromptInjectionDetector, SensitiveWordFilter
│   │   ├── output_guards.py  # PIIMasker
│   │   └── tool_guards.py    # ToolGuard
│   └── eval/                 # 评估子模块
│       ├── __init__.py
│       ├── base.py           # BaseEvaluator, EvalResult
│       ├── llm_judge.py      # LLMJudgeEvaluator
│       └── ab_test.py        # ABTestEvaluator
└── ...
```

### 10.3 测试计划

| 测试类型 | 内容 |
|----------|------|
| 单元测试 | 各中间件独立测试 |
| 集成测试 | 中间件链执行流程测试 |
| 安全测试 | Prompt 注入检测、PII 脱敏效果 |
| 性能测试 | 中间件开销评估 |

---

## 附录 A：AgentResult 字段说明

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | bool | 是否成功 |
| `output` | str | Agent 输出文本 |
| `tool_calls` | List[Dict] | 工具调用记录 |
| `iterations` | int | 循环迭代次数 |
| `duration_ms` | int | 总耗时（毫秒） |
| `error_msg` | Optional[str] | 错误信息 |
| `token_usage` | Optional[Dict] | token 使用统计 |
| `metadata` | Optional[Dict] | 扩展元数据（含评估结果） |

## 附录 B：配置参考

### 日志配置

```python
LoggingMiddleware(
    log_dir="logs/agent",           # 日志目录
    log_level="INFO",               # 日志级别
    log_request_body=True,          # 记录请求体
    log_response_body=True,         # 记录响应体
    max_body_length=1000,           # 内容截断长度
)
```

### 指标配置

```python
MetricsMiddleware(
    user_id="u123",                 # 用户 ID
    session_id="s456",              # 会话 ID
    save_input=True,                # 保存输入到数据库
    save_output=True,               # 保存输出到数据库
)
```

### 安全配置

```python
SafetyMiddleware(
    input_guards=[...],             # 输入防护器列表
    output_guards=[...],            # 输出防护器列表
    tool_guards=[...],              # 工具防护器列表
    log_violations=True,            # 记录违规日志
)
```

### 评估配置

```python
EvalMiddleware(
    evaluators=[...],               # 评估器列表
    save_results=True,              # 保存评估结果到数据库
)
```

---

**文档结束**

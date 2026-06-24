# BaseAgent 中间件使用教程

> 本文档介绍如何使用 BaseAgent 中间件系统为你的 Agent 添加可观测性、安全性和评估能力。

---

## 目录

1. [快速开始](#1-快速开始)
2. [LoggingMiddleware - 结构化日志](#2-loggingmiddleware---结构化日志)
3. [MetricsMiddleware - 指标收集](#3-metricsmiddleware---指标收集)
4. [SafetyMiddleware - 安全防护](#4-safetymiddleware---安全防护)
5. [EvalMiddleware - 质量评估](#5-evalmiddleware---质量评估)
6. [完整示例](#6-完整示例)
7. [最佳实践](#7-最佳实践)
8. [常见问题](#8-常见问题)

---

## 1. 快速开始

### 1.1 安装中间件

中间件已内置于 `Base.Ai.middlewares` 模块，无需额外安装。

### 1.2 基础用法

**方式一：初始化时注册（推荐）**

```python
from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.middlewares import (
    LoggingMiddleware,
    MetricsMiddleware,
    SafetyMiddleware,
)

# 创建 Agent 时直接注册中间件
agent = ReActAgent(
    llm=your_llm,
    name="MyAgent",
    tools=[your_tool],
    middlewares=[
        LoggingMiddleware(),
        MetricsMiddleware(),
        SafetyMiddleware(),
    ],
)

# 运行 Agent
result = agent.run("你的问题")
print(result.output)
```

**方式二：后续注册**

```python
# 先创建 Agent
agent = ReActAgent(
    llm=your_llm,
    name="MyAgent",
    tools=[your_tool],
)

# 再注册中间件
agent.use(LoggingMiddleware())
agent.use(MetricsMiddleware())
agent.use(SafetyMiddleware())
```

### 1.3 中间件执行顺序

中间件按**洋葱模型**执行：

```
请求阶段：LoggingMiddleware → MetricsMiddleware → SafetyMiddleware → Agent Core
响应阶段：SafetyMiddleware → MetricsMiddleware → LoggingMiddleware
```

**建议注册顺序**：
1. `LoggingMiddleware` - 最先注册，最后执行响应处理
2. `MetricsMiddleware` - 记录完整耗时
3. `SafetyMiddleware` - 安全防护
4. `EvalMiddleware` - 质量评估

---

## 2. LoggingMiddleware - 结构化日志

### 2.1 功能

- 使用 JSON 格式记录请求和响应
- 日志按天轮转，保留 30 天
- 支持内容截断，防止日志过大

### 2.2 配置参数

```python
LoggingMiddleware(
    log_dir="logs/agent",           # 日志目录
    log_level="INFO",               # 日志级别：DEBUG/INFO/WARNING/ERROR
    log_request_body=True,          # 是否记录请求体
    log_response_body=True,         # 是否记录响应体
    max_body_length=1000,           # 内容截断长度
)
```

### 2.3 使用示例

```python
# 基础使用
agent.use(LoggingMiddleware())

# 自定义配置
agent.use(LoggingMiddleware(
    log_dir="logs/my_agent",
    log_level="DEBUG",
    max_body_length=500,
))
```

### 2.4 日志格式

**请求日志**：
```json
{
    "timestamp": "2026-06-24T10:30:00.123456",
    "event": "request",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "MyAgent",
    "user_input": "查询学生成绩",
    "metadata": {"user_id": "u123"}
}
```

**响应日志**：
```json
{
    "timestamp": "2026-06-24T10:30:02.456789",
    "event": "response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "MyAgent",
    "duration_ms": 2333,
    "output": "查询结果...",
    "tool_calls_count": 1,
    "success": true,
    "error": null
}
```

---

## 3. MetricsMiddleware - 指标收集

### 3.1 功能

- 记录每次调用的指标（耗时、Token、状态等）
- 持久化到 MySQL（复用现有模型）
- 提供统计查询接口

### 3.2 配置参数

```python
MetricsMiddleware(
    user_id="u123",                 # 用户 ID（可选）
    session_id="s456",              # 会话 ID（可选）
    save_input=True,                # 是否保存输入到数据库
    save_output=True,               # 是否保存输出到数据库
)
```

### 3.3 使用示例

```python
# 基础使用
agent.use(MetricsMiddleware())

# 带用户信息
agent.use(MetricsMiddleware(
    user_id="user_123",
    session_id="session_456",
))

# 不保存输入输出（节省存储）
agent.use(MetricsMiddleware(
    save_input=False,
    save_output=False,
))
```

### 3.4 查询统计

```python
metrics = MetricsMiddleware()

# 获取最近 24 小时统计
stats = metrics.get_stats(hours=24)
print(stats)
# 输出:
# {
#     "total_requests": 100,
#     "success_rate": 0.95,
#     "avg_duration_ms": 1200,
#     "p50_duration_ms": 800,
#     "p90_duration_ms": 2500,
#     "total_tokens": 50000
# }

# 按 Agent 名称过滤
stats = metrics.get_stats(agent_name="MyAgent", hours=24)
```

### 3.5 数据库表

指标存储到以下表：
- `base_agent_call_log` - 主调用记录
- `base_agent_tool_call_log` - 工具调用明细

---

## 4. SafetyMiddleware - 安全防护

### 4.1 功能

三层安全防护：
- **输入防护**：Prompt 注入检测、敏感词过滤
- **输出防护**：PII 脱敏（手机号、身份证、邮箱等）
- **工具防护**：白名单/黑名单、危险操作拦截

### 4.2 基础使用

```python
# 使用默认配置
agent.use(SafetyMiddleware())
```

### 4.3 自定义输入防护

```python
from Base.Ai.middlewares import (
    SafetyMiddleware,
    PromptInjectionDetector,
    SensitiveWordFilter,
)

# 自定义 Prompt 注入检测
injection_detector = PromptInjectionDetector(
    custom_patterns=[
        r"自定义攻击模式",
        r"另一个攻击模式",
    ],
    block_on_detect=True,  # 检测到攻击时阻断
)

# 自定义敏感词过滤
sensitive_filter = SensitiveWordFilter(
    words=["敏感词1", "敏感词2"],      # 直接指定
    word_file="config/sensitive.txt", # 或从文件加载
    replace_char="*",                 # 替换字符
)

# 创建安全中间件
agent.use(SafetyMiddleware(
    input_guards=[injection_detector, sensitive_filter],
))
```

### 4.4 自定义输出防护（PII 脱敏）

```python
from Base.Ai.middlewares import PIIMasker

# 自定义 PII 脱敏
pii_masker = PIIMasker(
    enabled_types=["phone", "id_card", "email"],  # 启用的脱敏类型
    mask_strategy="partial",  # 脱敏策略：partial/full/hash
)

agent.use(SafetyMiddleware(
    output_guards=[pii_masker],
))
```

**脱敏策略**：
- `partial` - 部分脱敏：`138****5678`
- `full` - 完全脱敏：`***`
- `hash` - 哈希脱敏：`a1b2c3d4`

**支持的 PII 类型**：
- `phone` - 手机号
- `id_card` - 身份证号
- `email` - 邮箱
- `bank_card` - 银行卡号
- `ipv4` - IP 地址

### 4.5 自定义工具防护

```python
from Base.Ai.middlewares import ToolGuard

# 工具白名单（只允许指定工具）
tool_guard = ToolGuard(
    allowed_tools=["search", "calculate", "query_db"],
    max_argument_length=5000,  # 参数最大长度
)

# 或工具黑名单（禁止指定工具）
tool_guard = ToolGuard(
    blocked_tools=["delete_data", "drop_table"],
)

agent.use(SafetyMiddleware(
    tool_guards=[tool_guard],
))
```

### 4.6 完整安全配置

```python
agent.use(SafetyMiddleware(
    input_guards=[
        PromptInjectionDetector(),
        SensitiveWordFilter(word_file="config/sensitive.txt"),
    ],
    output_guards=[
        PIIMasker(enabled_types=["phone", "id_card", "email"]),
    ],
    tool_guards=[
        ToolGuard(allowed_tools=["search", "query"]),
    ],
    log_violations=True,  # 记录违规日志
))
```

---

## 5. EvalMiddleware - 质量评估

### 5.1 功能

- **LLM-as-Judge**：使用 LLM 评估输出质量
- **A/B 实验**：对比不同配置的效果

### 5.2 LLM-as-Judge 评估

```python
from Base.Ai.middlewares import EvalMiddleware, LLMJudgeEvaluator

# 创建评估 LLM（用于评估的 LLM，可以与主 LLM 不同）
judge_llm = your_judge_llm

# 创建评估器
judge = LLMJudgeEvaluator(
    judge_llm=judge_llm,
    dimensions=["accuracy", "relevance", "completeness"],  # 评估维度
    # custom_prompt="自定义评估提示词..."  # 可选
)

# 创建评估中间件
agent.use(EvalMiddleware(
    evaluators=[judge],
    save_results=True,  # 保存评估结果到数据库
))
```

**评估维度说明**：
- `accuracy` - 准确性：回答是否正确
- `relevance` - 相关性：回答是否与问题相关
- `completeness` - 完整性：回答是否完整
- 可自定义维度

### 5.3 A/B 实验

```python
from Base.Ai.middlewares import ABTestEvaluator

# 配置实验
ab_evaluator = ABTestEvaluator(
    experiment_name="model_comparison",
    variants={
        "gpt4": {"model": "gpt-4", "temperature": 0.7},
        "qwen": {"model": "qwen-max", "temperature": 0.7},
    },
    traffic_split={"gpt4": 0.5, "qwen": 0.5}  # 流量分配比例
)

# 获取当前请求的变体
request_id = "some-request-id"
variant_config = ab_evaluator.get_variant_config(request_id)
# 返回: {"model": "gpt-4", "temperature": 0.7}

# 根据变体创建不同的 Agent
if variant_config["model"] == "gpt-4":
    agent = create_gpt4_agent()
else:
    agent = create_qwen_agent()

# 注册评估中间件
agent.use(EvalMiddleware(evaluators=[ab_evaluator]))
```

**获取实验结果**：
```python
results = ab_evaluator.get_experiment_results()
print(results)
# 输出:
# {
#     "gpt4": {"total_requests": 50, "success_rate": 0.96, "avg_duration_ms": 1500},
#     "qwen": {"total_requests": 50, "success_rate": 0.92, "avg_duration_ms": 1200}
# }
```

### 5.4 自定义评估器

```python
from Base.Ai.middlewares.eval.base import BaseEvaluator, EvalResult
from Base.Ai.middlewares.base import AgentContext

class MyCustomEvaluator(BaseEvaluator):
    name = "custom_evaluator"
    
    def is_applicable(self, ctx: AgentContext) -> bool:
        # 判断是否需要评估
        return ctx.error is None and ctx.output
    
    async def evaluate(self, ctx: AgentContext) -> EvalResult:
        # 你的评估逻辑
        score = self.calculate_score(ctx.output)
        
        return EvalResult(
            evaluator_name=self.name,
            score=score,
            dimensions={"custom_dim": 0.8},
            feedback="评估反馈",
        )
    
    def calculate_score(self, output: str) -> float:
        # 计算分数
        return 0.9

# 使用自定义评估器
agent.use(EvalMiddleware(evaluators=[MyCustomEvaluator()]))
```

---

## 6. 完整示例

### 6.1 基础示例

```python
from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.middlewares import (
    LoggingMiddleware,
    MetricsMiddleware,
    SafetyMiddleware,
)

# 创建 Agent 并注册中间件
agent = ReActAgent(
    llm=your_llm,
    name="StudentQueryAgent",
    tools=[search_tool, db_query_tool],
    middlewares=[
        LoggingMiddleware(log_dir="logs/agent"),
        MetricsMiddleware(user_id="u123"),
        SafetyMiddleware(),
    ],
)

# 运行
result = agent.run("查询张三的成绩")
print(result.output)
print(result.token_usage)  # Token 使用统计
```

### 6.2 完整配置示例

```python
from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.middlewares import (
    LoggingMiddleware,
    MetricsMiddleware,
    SafetyMiddleware,
    EvalMiddleware,
    PromptInjectionDetector,
    SensitiveWordFilter,
    PIIMasker,
    ToolGuard,
    LLMJudgeEvaluator,
)

# 创建 Agent 并一次性注册所有中间件
agent = ReActAgent(
    llm=your_llm,
    name="ProductionAgent",
    tools=[search_tool, db_query_tool],
    middlewares=[
        # 1. 日志中间件
        LoggingMiddleware(
            log_dir="logs/production",
            log_level="INFO",
            max_body_length=2000,
        ),
        # 2. 指标中间件
        MetricsMiddleware(
            user_id=user_id,
            session_id=session_id,
            save_input=True,
            save_output=True,
        ),
        # 3. 安全中间件
        SafetyMiddleware(
            input_guards=[
                PromptInjectionDetector(
                    custom_patterns=[r"自定义攻击模式"],
                ),
                SensitiveWordFilter(
                    word_file="config/sensitive_words.txt",
                ),
            ],
            output_guards=[
                PIIMasker(
                    enabled_types=["phone", "id_card", "email"],
                    mask_strategy="partial",
                ),
            ],
            tool_guards=[
                ToolGuard(
                    allowed_tools=["search", "query_db"],
                    max_argument_length=10000,
                ),
            ],
            log_violations=True,
        ),
        # 4. 评估中间件
        EvalMiddleware(
            evaluators=[
                LLMJudgeEvaluator(
                    judge_llm=judge_llm,
                    dimensions=["accuracy", "relevance", "completeness"],
                ),
            ],
            save_results=True,
        ),
    ],
)

# 运行
result = agent.run("查询学生信息")
print(f"输出: {result.output}")
print(f"耗时: {result.duration_ms}ms")
print(f"Token: {result.token_usage}")
print(f"评估: {result.metadata.get('eval_results')}")
```

### 6.3 生产环境配置

```python
import logging
from Base.Ai.base.baseAgent import ReActAgent
from Base.Ai.middlewares import *

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

class ProductionAgent(ReActAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 生产环境中间件配置
        self.use(LoggingMiddleware(
            log_dir="logs/production",
            log_level="INFO",
            log_request_body=False,  # 生产环境不记录请求体（隐私）
            log_response_body=False,
        ))
        
        self.use(MetricsMiddleware(
            save_input=False,  # 生产环境不保存输入输出
            save_output=False,
        ))
        
        self.use(SafetyMiddleware(
            input_guards=[
                PromptInjectionDetector(),
                SensitiveWordFilter(word_file="config/sensitive.txt"),
            ],
            output_guards=[
                PIIMasker(enabled_types=["phone", "id_card", "email", "bank_card"]),
            ],
            tool_guards=[
                ToolGuard(
                    allowed_tools=["safe_search", "read_query"],  # 只允许安全工具
                    max_argument_length=5000,
                ),
            ],
        ))

# 使用
agent = ProductionAgent(
    llm=production_llm,
    name="ProductionAgent",
    tools=[safe_search_tool, read_query_tool],
)

result = agent.run("用户问题")
```

---

## 7. 最佳实践

### 7.1 中间件顺序

推荐的注册顺序：

```python
# 1. 日志（最外层，记录完整请求）
agent.use(LoggingMiddleware())

# 2. 指标（记录完整耗时）
agent.use(MetricsMiddleware())

# 3. 安全（防护在评估之前）
agent.use(SafetyMiddleware())

# 4. 评估（最内层，评估最终输出）
agent.use(EvalMiddleware())
```

### 7.2 性能优化

```python
# 生产环境：关闭不必要的日志和存储
agent.use(LoggingMiddleware(
    log_request_body=False,
    log_response_body=False,
))

agent.use(MetricsMiddleware(
    save_input=False,
    save_output=False,
))
```

### 7.3 安全加固

```python
# 严格模式：只允许白名单工具
agent.use(SafetyMiddleware(
    tool_guards=[
        ToolGuard(
            allowed_tools=["safe_search"],  # 严格白名单
            blocked_tools=["delete", "update", "drop"],  # 黑名单双重保护
        ),
    ],
))
```

### 7.4 错误处理

```python
from Base.Ai.middlewares.safety.base import SafetyException

try:
    result = agent.run("用户问题")
except SafetyException as e:
    print(f"安全检查未通过: {e.reason}")
    print(f"风险等级: {e.risk_level}")
```

---

## 8. 常见问题

### Q1: 中间件会影响性能吗？

**A**: 影响很小。中间件主要是：
- 日志写入：异步 I/O，影响可忽略
- 指标记录：数据库写入，约 5-10ms
- 安全检查：正则匹配，约 1-2ms

### Q2: 如何只启用部分中间件？

**A**: 只注册你需要的中间件即可：

```python
# 只启用日志和安全
agent.use(LoggingMiddleware())
agent.use(SafetyMiddleware())
```

### Q3: 如何自定义日志格式？

**A**: 继承 `LoggingMiddleware` 并重写日志方法：

```python
class CustomLoggingMiddleware(LoggingMiddleware):
    async def process_request(self, ctx, next):
        # 自定义日志格式
        self._logger.info(f"[{ctx.agent_name}] {ctx.request_id}: {ctx.user_input[:50]}")
        await next()
```

### Q4: 如何处理安全检查误报？

**A**: 调整检测规则：

```python
# 添加白名单模式
detector = PromptInjectionDetector(
    custom_patterns=[],  # 清空默认模式
    # 只保留你需要的检测规则
)
```

### Q5: 评估会消耗额外 Token 吗？

**A**: 是的，LLM-as-Judge 会调用评估 LLM，消耗额外 Token。建议：
- 使用较小的模型作为评估 LLM
- 只在需要时启用评估
- 可以采样评估（不是每个请求都评估）

### Q6: 如何查看中间件执行顺序？

**A**: 启用 DEBUG 日志：

```python
import logging
logging.getLogger('Base.Ai.middlewares').setLevel(logging.DEBUG)
```

---

## 附录：API 参考

### AgentResult

```python
class AgentResult:
    success: bool              # 是否成功
    output: str                # 输出文本
    tool_calls: List[Dict]     # 工具调用记录
    duration_ms: int           # 耗时（毫秒）
    token_usage: Dict[str, int]  # Token 使用统计
    error_msg: Optional[str]   # 错误信息
    metadata: Dict[str, Any]   # 元数据（含评估结果）
```

### 中间件列表

| 中间件 | 功能 | 必选 |
|--------|------|------|
| LoggingMiddleware | 结构化日志 | 推荐 |
| MetricsMiddleware | 指标收集 | 推荐 |
| SafetyMiddleware | 安全防护 | 生产环境必选 |
| EvalMiddleware | 质量评估 | 可选 |

---

**文档版本**: v1.0  
**更新日期**: 2026-06-24

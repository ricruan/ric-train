"""
指标收集中间件

收集 Agent 运行指标，持久化到 MySQL。
"""
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .base import AgentContext, Middleware

logger = logging.getLogger(__name__)


class MetricsMiddleware(Middleware):
    """
    指标收集中间件

    复用已有的 BaseAgentCallLog 和 BaseAgentToolCallLog 模型持久化到 MySQL。
    """

    def __init__(
        self,
        user_id: str = None,
        session_id: str = None,
        save_input: bool = True,
        save_output: bool = True,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.save_input = save_input
        self.save_output = save_output

    async def process_request(self, ctx: AgentContext, next: Callable):
        """记录开始时间"""
        ctx.start_time = time.time()
        await next()

    async def process_response(self, ctx: AgentContext):
        """持久化调用记录到 MySQL"""
        from Base.Models.baseAgentCallLogModel import BaseAgentCallLog
        from Base.Models.baseAgentToolCallLogModel import BaseAgentToolCallLog

        duration_ms = int((time.time() - ctx.start_time) * 1000)
        ctx.duration_ms = duration_ms

        try:
            # 1. 保存主调用记录
            call_log = BaseAgentCallLog(
                agent_name=ctx.agent_name,
                user_id=self.user_id or ctx.metadata.get("user_id"),
                session_id=self.session_id or ctx.metadata.get("session_id"),
                input_data=json.dumps({"user_input": ctx.user_input}, ensure_ascii=False)
                if self.save_input
                else None,
                output_data=ctx.output[:2000] if self.save_output and ctx.output else None,
                status="failed" if ctx.error else "success",
                error_msg=str(ctx.error) if ctx.error else None,
                duration_ms=duration_ms,
                iterations=ctx.metadata.get("iterations", 0),
                ai_model=ctx.metadata.get("ai_model"),
                prompt_tokens=ctx.token_usage.get("prompt_tokens", 0),
                completion_tokens=ctx.token_usage.get("completion_tokens", 0),
                total_tokens=ctx.token_usage.get("total_tokens", 0),
            )
            call_log.save()

            # 2. 保存工具调用明细
            for i, tc in enumerate(ctx.tool_calls):
                tool_log = BaseAgentToolCallLog(
                    agent_call_id=call_log.id,
                    tool_name=tc.get("name"),
                    tool_input=json.dumps(tc.get("arguments", {}), ensure_ascii=False),
                    tool_output=str(tc.get("result", ""))[:5000],
                    status=tc.get("status", "success"),
                    error_msg=tc.get("error"),
                    duration_ms=tc.get("duration_ms", 0),
                    call_order=i + 1,
                )
                tool_log.save()

        except Exception as e:
            logger.error(f"MetricsMiddleware 持久化失败: {e}", exc_info=True)

    def get_stats(
        self,
        agent_name: str = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        获取统计数据

        Args:
            agent_name: Agent 名称过滤
            hours: 统计时间范围（小时）

        Returns:
            统计信息字典
        """
        from Base.Models.baseAgentCallLogModel import BaseAgentCallLog

        since = datetime.now() - timedelta(hours=hours)

        # 构建查询条件
        conditions = {}
        if agent_name:
            conditions["agent_name"] = agent_name

        # 查询记录
        try:
            records = BaseAgentCallLog.find_by(**conditions)

            # 按时间过滤
            records = [r for r in records if r.created_at and r.created_at > since]

            if not records:
                return {
                    "total_requests": 0,
                    "success_rate": 0,
                    "avg_duration_ms": 0,
                    "p50_duration_ms": 0,
                    "p90_duration_ms": 0,
                    "total_tokens": 0,
                }

            # 计算统计值
            total = len(records)
            success_count = sum(1 for r in records if r.status == "success")
            durations = sorted([r.duration_ms for r in records if r.duration_ms])
            total_tokens = sum(getattr(r, "total_tokens", 0) or 0 for r in records)

            return {
                "total_requests": total,
                "success_rate": round(success_count / total, 4) if total > 0 else 0,
                "avg_duration_ms": round(sum(durations) / len(durations), 1)
                if durations
                else 0,
                "p50_duration_ms": self._percentile(durations, 50),
                "p90_duration_ms": self._percentile(durations, 90),
                "total_tokens": total_tokens,
            }
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}", exc_info=True)
            return {
                "total_requests": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
                "total_tokens": 0,
            }

    @staticmethod
    def _percentile(sorted_data: List[int], p: int) -> int:
        """计算百分位数"""
        if not sorted_data:
            return 0
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

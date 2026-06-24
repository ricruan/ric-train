"""
A/B 实验评估器

支持对比不同配置的效果。
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

from .base import BaseEvaluator, EvalResult
from ..base import AgentContext

logger = logging.getLogger(__name__)


class ABTestEvaluator(BaseEvaluator):
    """
    A/B 实验评估器

    支持对比不同配置（模型/prompt/工具）的效果。
    """

    name = "ab_test"

    def __init__(
        self,
        experiment_name: str,
        variants: Dict[str, Dict[str, Any]],
        traffic_split: Dict[str, float] = None,
    ):
        self.experiment_name = experiment_name
        self.variants = variants

        if traffic_split:
            self.traffic_split = traffic_split
        else:
            # 均等分配
            n = len(variants)
            self.traffic_split = {k: 1.0 / n for k in variants}

        # 验证流量分配
        total = sum(self.traffic_split.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"流量分配总和必须为 1，当前为 {total}")

    def is_applicable(self, ctx: AgentContext) -> bool:
        return True

    def assign_variant(self, request_id: str) -> str:
        """根据 request_id 分配变体"""
        hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        normalized = (hash_val % 10000) / 10000.0

        cumulative = 0
        for variant, ratio in self.traffic_split.items():
            cumulative += ratio
            if normalized < cumulative:
                return variant

        return list(self.variants.keys())[-1]

    async def evaluate(self, ctx: AgentContext) -> EvalResult:
        """记录变体分配结果"""
        variant = self.assign_variant(ctx.request_id)

        return EvalResult(
            evaluator_name=self.name,
            score=1.0,
            metadata={
                "experiment": self.experiment_name,
                "variant": variant,
                "config": self.variants[variant],
            }
        )

    def get_variant_config(self, request_id: str) -> Dict[str, Any]:
        """获取变体配置"""
        variant = self.assign_variant(request_id)
        return self.variants[variant]

    def get_experiment_results(self) -> Dict[str, Any]:
        """获取实验结果统计"""
        from Base.Models.baseAgentCallLogModel import BaseAgentCallLog

        results = {}
        for variant_name in self.variants:
            try:
                records = BaseAgentCallLog.find_by(
                    agent_name=f"{self.experiment_name}_{variant_name}"
                )
                if records:
                    total = len(records)
                    success = sum(1 for r in records if r.status == "success")
                    avg_duration = sum(r.duration_ms or 0 for r in records) / total

                    results[variant_name] = {
                        "total_requests": total,
                        "success_rate": success / total if total > 0 else 0,
                        "avg_duration_ms": avg_duration,
                    }
            except Exception as e:
                logger.error(f"获取实验结果失败: {e}")

        return results

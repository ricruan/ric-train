"""
评估中间件

在 Agent 响应后执行评估器链。
"""
import json
import logging
from typing import Callable, List

from .base import AgentContext, Middleware
from .eval.base import BaseEvaluator, EvalResult

logger = logging.getLogger(__name__)


class EvalMiddleware(Middleware):
    """
    评估中间件

    在 Agent 响应后执行评估器链。
    """

    def __init__(
        self,
        evaluators: List[BaseEvaluator] = None,
        save_results: bool = True,
    ):
        self.evaluators = evaluators or []
        self.save_results = save_results

    def add_evaluator(self, evaluator: BaseEvaluator):
        """添加评估器"""
        self.evaluators.append(evaluator)

    async def process_request(self, ctx: AgentContext, next: Callable):
        """请求阶段：不做评估"""
        await next()

    async def process_response(self, ctx: AgentContext):
        """响应阶段：执行评估"""
        eval_results = []

        for evaluator in self.evaluators:
            if not evaluator.is_applicable(ctx):
                continue

            try:
                result = await evaluator.evaluate(ctx)
                eval_results.append(result)
            except Exception as e:
                logger.error(f"评估器 {evaluator.name} 执行失败: {e}", exc_info=True)

        # 保存评估结果到上下文
        ctx.metadata["eval_results"] = [
            r.model_dump() for r in eval_results
        ]

        # 持久化到 MySQL
        if self.save_results:
            self._save_eval_results(ctx, eval_results)

    def _save_eval_results(
        self,
        ctx: AgentContext,
        results: List[EvalResult]
    ):
        """保存评估结果到数据库"""
        from Base.Models.baseAgentEvalLogModel import BaseAgentEvalLog

        # 获取 agent_call_id
        agent_call_id = ctx.metadata.get("agent_call_id")

        for result in results:
            try:
                eval_log = BaseAgentEvalLog(
                    agent_call_id=agent_call_id,
                    evaluator_name=result.evaluator_name,
                    score=result.score,
                    dimensions=json.dumps(result.dimensions, ensure_ascii=False) if result.dimensions else None,
                    feedback=result.feedback,
                    metadata=json.dumps(result.metadata, ensure_ascii=False) if result.metadata else None,
                )
                eval_log.save()
            except Exception as e:
                logger.error(f"保存评估结果失败: {e}", exc_info=True)

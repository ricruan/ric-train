"""
LLM-as-Judge 评估器

使用 LLM 评估 Agent 输出质量。
"""
import json
import logging
from typing import List, Optional

from .base import BaseEvaluator, EvalResult
from ..base import AgentContext
from Base.Ai.base.baseLlm import BaseLlm

logger = logging.getLogger(__name__)


class LLMJudgeEvaluator(BaseEvaluator):
    """
    LLM-as-Judge 评估器

    使用另一个 LLM 评估 Agent 输出的质量。
    """

    name = "llm_judge"
    description = "使用 LLM 评估输出质量"

    def __init__(
        self,
        judge_llm: BaseLlm,
        dimensions: List[str] = None,
        custom_prompt: str = None,
    ):
        self.judge_llm = judge_llm
        self.dimensions = dimensions or ["accuracy", "relevance", "completeness"]
        self.custom_prompt = custom_prompt

    def is_applicable(self, ctx: AgentContext) -> bool:
        """只在成功响应时评估"""
        return ctx.error is None and ctx.output

    async def evaluate(self, ctx: AgentContext) -> EvalResult:
        """执行 LLM 评估"""
        eval_prompt = self._build_eval_prompt(ctx)

        try:
            response = await self.judge_llm.ainvoke(eval_prompt)
            return self._parse_eval_response(response)
        except Exception as e:
            logger.error(f"LLM 评估失败: {e}", exc_info=True)
            return EvalResult(
                evaluator_name=self.name,
                score=0,
                feedback=f"评估失败: {str(e)}",
            )

    def _build_eval_prompt(self, ctx: AgentContext) -> str:
        """构建评估提示词"""
        if self.custom_prompt:
            return self.custom_prompt.format(
                user_input=ctx.user_input,
                output=ctx.output,
                dimensions=", ".join(self.dimensions),
            )

        dimensions_list = "\n".join(f"- {d}" for d in self.dimensions)

        return f"""你是一个专业的 AI 输出质量评估专家。请评估以下 Agent 回答的质量。

## 用户输入
{ctx.user_input}

## Agent 回答
{ctx.output}

## 评估维度
请对以下维度分别打分（0-1 之间的小数）：
{dimensions_list}

## 输出格式
请以 JSON 格式输出：
{{
    "scores": {{"维度名": 分数, ...}},
    "overall_score": 总分,
    "feedback": "评估理由和改进建议"
}}"""

    def _parse_eval_response(self, response: str) -> EvalResult:
        """解析评估响应"""
        try:
            data = json.loads(response)
            scores = data.get("scores", {})
            overall = data.get("overall_score", 0)
            feedback = data.get("feedback", "")

            return EvalResult(
                evaluator_name=self.name,
                score=overall,
                dimensions=scores,
                feedback=feedback,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"评估结果解析失败: {e}")
            return EvalResult(
                evaluator_name=self.name,
                score=0,
                feedback=f"评估解析失败: {response[:200]}",
            )

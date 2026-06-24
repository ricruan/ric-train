"""
输出防护器

提供 PII 脱敏等功能。
"""
import re
import hashlib
import logging
from typing import List, Optional

from .base import GuardResult, SafetyGuard
from ..base import AgentContext

logger = logging.getLogger(__name__)


class PIIMasker(SafetyGuard):
    """
    PII（个人身份信息）脱敏器

    检测并脱敏输出中的敏感信息。
    """

    name = "pii_masker"

    # PII 正则模式
    PII_PATTERNS = {
        "phone": r"1[3-9]\d{9}",
        "id_card": r"\b\d{17}[\dXx]\b",
        "email": r"\b[\w.-]+@[\w.-]+\.\w+\b",
        "bank_card": r"\b\d{16,19}\b",
        "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }

    def __init__(
        self,
        enabled_types: List[str] = None,
        mask_strategy: str = "partial",
    ):
        self.enabled_types = enabled_types or list(self.PII_PATTERNS.keys())
        self.mask_strategy = mask_strategy

        # 编译正则
        self.compiled_patterns = {
            k: re.compile(v)
            for k, v in self.PII_PATTERNS.items()
            if k in self.enabled_types
        }

    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """检测并脱敏 PII"""
        masked = content
        found_types = []

        for pii_type, pattern in self.compiled_patterns.items():
            matches = pattern.findall(masked)
            if matches:
                found_types.append(pii_type)
                masked = pattern.sub(
                    lambda m, t=pii_type: self._mask(m.group(), t), masked
                )

        if found_types:
            return GuardResult(
                passed=True,
                masked_content=masked,
                reason=f"脱敏 PII 类型: {found_types}",
                risk_level="medium",
            )

        return GuardResult(passed=True)

    def _mask(self, value: str, pii_type: str) -> str:
        """脱敏处理"""
        if self.mask_strategy == "full":
            return "***"
        elif self.mask_strategy == "hash":
            return hashlib.md5(value.encode()).hexdigest()[:8]
        else:  # partial
            if len(value) <= 4:
                return "***"
            return value[:2] + "*" * (len(value) - 4) + value[-2:]

"""
输入防护器

提供 Prompt 注入检测和敏感词过滤。
"""
import os
import re
import logging
from typing import List, Optional

from .base import GuardResult, SafetyGuard
from ..base import AgentContext

logger = logging.getLogger(__name__)


class PromptInjectionDetector(SafetyGuard):
    """
    Prompt 注入检测器

    检测用户输入是否包含 prompt 注入攻击模式。
    """

    name = "prompt_injection_detector"

    # 常见注入模式
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|above)\s+instructions",
        r"disregard\s+(all\s+)?(previous|above)",
        r"forget\s+(all\s+)?(previous|above)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"act\s+as\s+(a|an|if)\s+",
        r"pretend\s+(to\s+be|you\s+are)",
        r"system\s*:\s*",
        r"<\|im_start\|>",
        r"\bDAN\b",
        r"jailbreak",
        r"bypass\s+(filter|restriction|safety)",
    ]

    def __init__(
        self,
        custom_patterns: List[str] = None,
        block_on_detect: bool = True,
    ):
        self.patterns = self.INJECTION_PATTERNS + (custom_patterns or [])
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]
        self.block_on_detect = block_on_detect

    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """检测 prompt 注入"""
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                return GuardResult(
                    passed=False,
                    reason=f"检测到 prompt 注入模式: {pattern.pattern}",
                    risk_level="high",
                )

        return GuardResult(passed=True)


class SensitiveWordFilter(SafetyGuard):
    """
    敏感词过滤器

    支持自定义敏感词库，支持模糊匹配。
    """

    name = "sensitive_word_filter"

    def __init__(
        self,
        words: List[str] = None,
        word_file: str = None,
        replace_char: str = "*",
    ):
        self.words = set(words or [])
        self.replace_char = replace_char

        # 从文件加载
        if word_file and os.path.exists(word_file):
            with open(word_file, "r", encoding="utf-8") as f:
                self.words.update(line.strip() for line in f if line.strip())

        # 构建正则
        self._build_pattern()

    def _build_pattern(self):
        """构建匹配正则"""
        if self.words:
            escaped = [re.escape(w) for w in self.words]
            pattern = "|".join(escaped)
            self.pattern = re.compile(pattern, re.IGNORECASE)
        else:
            self.pattern = None

    async def check(self, content: str, ctx: AgentContext) -> GuardResult:
        """检查并脱敏敏感词"""
        if not self.pattern:
            return GuardResult(passed=True)

        matches = self.pattern.findall(content)
        if not matches:
            return GuardResult(passed=True)

        # 脱敏处理
        masked = self.pattern.sub(
            lambda m: self.replace_char * len(m.group()), content
        )

        return GuardResult(
            passed=True,
            masked_content=masked,
            reason=f"发现敏感词: {matches[:5]}",
            risk_level="medium",
        )

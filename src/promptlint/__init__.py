"""promptlint:规则式提示词体检工具。"""

from .engine import Finding, lint_text

__all__ = ["Finding", "lint_text"]
__version__ = "0.1.0"

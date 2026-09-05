"""examples/ 与 README 的自检:文档里贴的"真实输出"必须仍然真实。

这三条测试的作用是挡住文档漂移 —— 规则改了而 README 没跟着改,CI 会先发现。
"""

from pathlib import Path

from promptlint import lint_text
from promptlint.engine import has_errors, summary

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_clean_example_is_actually_clean():
    """作为"好提示词"范例发出去的那份,自己必须零检出。"""
    assert lint_text(read("examples/clean-prompt.txt")) == []


def test_messy_example_has_warnings_but_no_error():
    findings = lint_text(read("examples/messy-prompt.txt"))
    assert not has_errors(findings)
    assert any(f.severity == "warn" for f in findings)


def test_readme_quoted_summary_matches_real_output():
    actual = summary(lint_text(read("examples/messy-prompt.txt")))
    assert actual in read("README.md"), f"README 里的合计行已过期,现在应是:{actual}"

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


def test_readme_test_count_matches_reality():
    """README 里写的测试数必须等于真实收集到的用例数。

    加这条的由头：README 与仓库描述长期停在「16 项测试」，实际已经 23 项 ——
    正是这个文件要挡的那种漂移，却漏在了文件自己身上。数字自校验后就不会再飘。
    """
    import re
    import subprocess
    import sys

    m = re.search(r"#\s*(\d+)\s*项测试", read("README.md"))
    assert m, "README 里找不到「# N 项测试」那行注释"
    claimed = int(m.group(1))

    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only"],
                       cwd=ROOT, capture_output=True, text=True)
    n = re.search(r"(\d+)\s+tests?\s+collected", r.stdout) \
        or re.search(r"collected\s+(\d+)", r.stdout)
    assert n, f"数不出实际用例数：{r.stdout[-300:]}"
    actual = int(n.group(1))

    assert claimed == actual, f"README 写 {claimed} 项，实际收集到 {actual} 项"

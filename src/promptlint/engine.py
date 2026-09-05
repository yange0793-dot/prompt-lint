"""核心引擎:跑规则、汇总检出、定退出码。"""

from dataclasses import asdict, dataclass

from .rules import RULES, Hit

SEVERITY_RANK = {"error": 2, "warn": 1, "info": 0}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    suggestion: str
    line: int
    excerpt: str


def lint_text(text: str) -> list[Finding]:
    """对一段提示词跑全部规则,返回按严重度降序的检出列表。"""
    hits: list[Hit] = []
    for rule in RULES:
        hits.extend(rule(text))
    findings = [Finding(**asdict(h)) for h in hits]
    findings.sort(key=lambda f: -SEVERITY_RANK.get(f.severity, 0))
    return findings


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)


def summary(findings: list[Finding]) -> str:
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("error", "warn", "info")}
    return f"{counts['error']} error, {counts['warn']} warn, {counts['info']} info"

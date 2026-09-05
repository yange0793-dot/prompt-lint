"""输出格式:text(带颜色)与 json。"""

import json
import sys
from dataclasses import asdict

from .engine import Finding, summary

SEVERITY_STYLE = {
    "error": ("\033[31m", "✗"),
    "warn": ("\033[33m", "⚠"),
    "info": ("\033[36m", "ℹ"),
}
RESET = "\033[0m"
BOLD = "\033[1m"


def format_text(findings: list[Finding], source: str, color: bool = True) -> str:
    lines: list[str] = []
    for f in findings:
        if color:
            style, mark = SEVERITY_STYLE[f.severity]
            head = f"{style}{mark}{RESET} {style}{f.rule_id}{RESET}"
        else:
            mark = {"error": "✗", "warn": "⚠", "info": "ℹ"}[f.severity]
            head = f"{mark} {f.rule_id}"
        where = f"{source}:{f.line}" if f.line else source
        lines.append(f"{head} {where}  {f.message}")
        if f.excerpt:
            lines.append(f"    └ {f.excerpt}")
        if f.suggestion:
            lines.append(f"    └ 建议:{f.suggestion}")
    lines.append(f"{BOLD if color else ''}{summary(findings)}{RESET if color else ''}")
    return "\n".join(lines)


def format_json(findings: list[Finding], source: str) -> str:
    return json.dumps(
        {
            "source": source,
            "findings": [asdict(f) for f in findings],
            "summary": summary(findings),
        },
        ensure_ascii=False,
        indent=2,
    )


def supports_color() -> bool:
    return sys.stdout.isatty() and sys.platform != "win32"

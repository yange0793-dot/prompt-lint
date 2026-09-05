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


def format_findings(findings: list[Finding], source: str, color: bool = True) -> str:
    """只渲染检出行,不带合计 —— 多文件模式下由调用方统一给一行合计。"""
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
    return "\n".join(lines)


def format_text(findings: list[Finding], source: str, color: bool = True) -> str:
    """单个输入的完整报告:检出行 + 合计行。"""
    body = format_findings(findings, source, color=color)
    tail = f"{BOLD if color else ''}{summary(findings)}{RESET if color else ''}"
    return f"{body}\n{tail}" if body else tail


def format_file_section(findings: list[Finding], source: str, color: bool = True) -> str:
    """多文件模式下单个文件的段落:干净的文件也要留一行,否则看不出它被体检过。"""
    body = format_findings(findings, source, color=color)
    if body:
        return body
    head = f"{BOLD}{source}{RESET}" if color else source
    return f"✓ {head}  无检出"


def format_total(findings: list[Finding], file_count: int, color: bool = True) -> str:
    """多文件时的合计行。"""
    line = f"共 {file_count} 个文件:{summary(findings)}"
    return f"{BOLD}{line}{RESET}" if color else line


def _report_dict(findings: list[Finding], source: str) -> dict:
    return {
        "source": source,
        "findings": [asdict(f) for f in findings],
        "summary": summary(findings),
    }


def format_json(findings: list[Finding], source: str) -> str:
    return json.dumps(_report_dict(findings, source), ensure_ascii=False, indent=2)


def format_json_reports(reports: list[tuple[str, list[Finding]]]) -> str:
    """单个输入输出对象,多个输入输出同形对象的数组 —— 单文件的形态保持不变。"""
    if len(reports) == 1:
        source, findings = reports[0]
        return format_json(findings, source)
    payload = [_report_dict(findings, source) for source, findings in reports]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def supports_color() -> bool:
    return sys.stdout.isatty() and sys.platform != "win32"

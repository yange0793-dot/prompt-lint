"""命令行入口。

用法:
  promptlint FILE [FILE ...]   体检一个或多个文件
  promptlint -                 读 stdin
  promptlint -p "提示词"       直接体检一段文本
  promptlint --json FILE       机器可读输出
  promptlint --max-warn 0 FILE warn 超过 N 条也算失败(挂 CI 用)

退出码:0 = 通过;1 = 存在 error 或 warn 超过 --max-warn;2 = 用法/IO 错误。
"""

import argparse
import sys

from . import __version__
from .engine import Finding, count_severity, has_errors, lint_text
from .formatters import (
    format_file_section,
    format_json_reports,
    format_text,
    format_total,
    supports_color,
)

Report = tuple[str, list[Finding]]


def read_sources(args: argparse.Namespace) -> list[tuple[str, str]]:
    """返回 [(source 标签, 文本)],顺序与命令行一致。"""
    if args.prompt is not None:
        return [("<prompt>", args.prompt)]
    if args.paths in (None, []):
        return [("<stdin>", sys.stdin.read())]
    sources: list[tuple[str, str]] = []
    for path in args.paths:
        if path == "-":
            sources.append(("<stdin>", sys.stdin.read()))
            continue
        with open(path, encoding="utf-8") as f:
            sources.append((path, f.read()))
    return sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptlint",
        description="规则式提示词体检:离线、确定性,在调用模型之前先抓住低级问题。",
    )
    parser.add_argument("paths", nargs="*", help="要体检的文件,可给多个;- 表示 stdin")
    parser.add_argument("-p", "--prompt", help="直接体检一段文本")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-color", action="store_true", help="关闭颜色")
    parser.add_argument(
        "--max-warn",
        type=int,
        metavar="N",
        help="warn 数超过 N 时以退出码 1 结束(默认不限制)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sources = read_sources(args)
    except (OSError, UnicodeDecodeError) as e:
        print(f"promptlint: 读取失败:{e}", file=sys.stderr)
        return 2

    reports: list[Report] = [(label, lint_text(text)) for label, text in sources]
    every_finding = [f for _, findings in reports for f in findings]

    if args.json:
        print(format_json_reports(reports))
    else:
        color = supports_color() and not args.no_color
        if len(reports) == 1:
            label, findings = reports[0]
            print(format_text(findings, label, color=color))
        else:
            sections = [format_file_section(f, label, color=color) for label, f in reports]
            print("\n".join(sections) + "\n" + format_total(every_finding, len(reports), color=color))

    if has_errors(every_finding):
        return 1
    if args.max_warn is not None and count_severity(every_finding, "warn") > args.max_warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

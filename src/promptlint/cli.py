"""命令行入口。

用法:
  promptlint FILE [...]     体检文件
  promptlint -              读 stdin
  promptlint -p "提示词"    直接体检一段文本
  promptlint --json FILE    机器可读输出

退出码:0 = 无 error;1 = 存在 error;2 = 用法/IO 错误。
"""

import argparse
import sys

from .engine import Finding, has_errors, lint_text
from .formatters import format_json, format_text, supports_color

VERSION = "0.1.0"


def read_input(args: argparse.Namespace) -> tuple[str, str]:
    """返回 (source 标签, 文本)。"""
    if args.prompt is not None:
        return "<prompt>", args.prompt
    if args.paths in (None, []) or args.paths == ["-"]:
        return "<stdin>", sys.stdin.read()
    path = args.paths[0]
    with open(path, encoding="utf-8") as f:
        return path, f.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptlint",
        description="规则式提示词体检:离线、确定性,在调用模型之前先抓住低级问题。",
    )
    parser.add_argument("paths", nargs="*", help="要体检的文件,- 表示 stdin")
    parser.add_argument("-p", "--prompt", help="直接体检一段文本")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--no-color", action="store_true", help="关闭颜色")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source, text = read_input(args)
    except (OSError, UnicodeDecodeError) as e:
        print(f"promptlint: 读取失败:{e}", file=sys.stderr)
        return 2

    findings: list[Finding] = lint_text(text)
    if args.json:
        print(format_json(findings, source))
    else:
        color = supports_color() and not args.no_color
        print(format_text(findings, source, color=color))

    return 1 if has_errors(findings) else 0


if __name__ == "__main__":
    sys.exit(main())

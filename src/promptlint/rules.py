"""内置规则。每条规则是一个函数:文本 -> 该规则的检出列表。

约定:规则只做「确定性、可解释」的静态检查,不发任何网络请求。
"""

import re
import unicodedata
from dataclasses import dataclass

SEVERITIES = ("error", "warn", "info")


@dataclass(frozen=True)
class Hit:
    rule_id: str
    severity: str
    message: str
    suggestion: str
    line: int
    excerpt: str


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _excerpt(text: str, pos: int, width: int = 24) -> str:
    chunk = text[max(0, pos - 4) : pos + width].replace("\n", " ")
    return chunk.strip()


def rule_too_short(text: str) -> list[Hit]:
    if len(text.strip()) < 20:
        return [
            Hit(
                "RL001",
                "error",
                f"提示词仅 {len(text.strip())} 个字符,缺少上下文",
                "补充目标、背景信息与输出要求",
                1,
                text.strip()[:30],
            )
        ]
    return []


def rule_too_long(text: str) -> list[Hit]:
    if len(text) > 2000:
        return [
            Hit(
                "RL002",
                "warn",
                f"提示词长达 {len(text)} 字符,单次请求难以聚焦",
                "拆成多个步骤,或把背景材料单独给",
                1,
                "",
            )
        ]
    return []


VAGUE_WORDS = (
    "随便", "大概", "尽量", "差不多", "优化一下", "完善一下",
    "搞一下", "弄一下", "写个东西", "帮我看看", "改改", "弄好一点",
)


def rule_vague_words(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for word in VAGUE_WORDS:
        for m in re.finditer(re.escape(word), text):
            hits.append(
                Hit(
                    "RL003",
                    "warn",
                    f"模糊表述「{word}」,模型只能靠猜",
                    "换成可验证的具体要求,例如「优化一下」→「把首屏加载压到 1s 内」",
                    _line_of(text, m.start()),
                    _excerpt(text, m.start()),
                )
            )
    return hits


FORMAT_HINTS = re.compile(
    r"格式|JSON|json|表格|列表|要点|步骤|markdown|Markdown|字数|schema|模板|结构"
)


def rule_no_output_format(text: str) -> list[Hit]:
    if not FORMAT_HINTS.search(text):
        return [
            Hit(
                "RL004",
                "info",
                "没有声明期望的输出格式",
                "明确输出形态:JSON / 表格 / 要点列表 / 字数上限,下游解析会稳定很多",
                1,
                "",
            )
        ]
    return []


NUMBERED_ITEM = re.compile(r"^\s*(?:\d{1,2}[.、)]|[①②③④⑤⑥⑦⑧⑨⑩])", re.M)


def rule_multi_step(text: str) -> list[Hit]:
    items = NUMBERED_ITEM.findall(text)
    if len(items) >= 4:
        return [
            Hit(
                "RL005",
                "info",
                f"检测到 {len(items)} 个编号条目,像是多个任务打包",
                "多任务建议拆开逐个确认,出错时更容易定位是哪一步的锅",
                1,
                "",
            )
        ]
    return []


REPEATED_PUNCT = re.compile(r"？{2,}|！{2,}|。{2,}|，{2,}|!{2,}|\?{2,}")


def rule_repeated_punct(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for m in REPEATED_PUNCT.finditer(text):
        hits.append(
            Hit(
                "RL006",
                "warn",
                f"重复标点「{m.group(0)}」",
                "单个标点足以表达语气,重复符号通常是草稿痕迹",
                _line_of(text, m.start()),
                _excerpt(text, m.start()),
            )
        )
    return hits


FULLWIDTH_ALNUM = re.compile(r"[０-９Ａ-Ｚａ-ｚ]+")


def rule_fullwidth_alnum(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for m in FULLWIDTH_ALNUM.finditer(text):
        halfwidth = unicodedata.normalize("NFKC", m.group(0))
        hits.append(
            Hit(
                "RL007",
                "warn",
                "使用了全角字母/数字,复制到代码或 JSON 里会出错",
                f"改用半角「{halfwidth}」",
                _line_of(text, m.start()),
                _excerpt(text, m.start()),
            )
        )
    return hits


CN_EN_GAP = re.compile(r"([\u4e00-\u9fff])([A-Za-z0-9])|([A-Za-z0-9])([\u4e00-\u9fff])")


def rule_cn_en_spacing(text: str) -> list[Hit]:
    gaps = list(CN_EN_GAP.finditer(text))
    if not gaps:
        return []
    hits = [
        Hit(
            "RL008",
            "info",
            "中文与英文/数字之间没有空格",
            "加空格(盘古之白)能显著提升分词与阅读质量",
            _line_of(text, m.start()),
            _excerpt(text, m.start()),
        )
        for m in gaps[:3]
    ]
    if len(gaps) > 3:
        hits.append(
            Hit("RL008", "info", f"还有 {len(gaps) - 3} 处同类问题,略", "", 0, "")
        )
    return hits


CONFLICT_PAIRS = (
    ("不要解释", r"解释(一下|原因|理由)|说明(一下|原因)"),
    ("不要改动", r"(重构|重写)一下|换个(写法|实现)"),
    ("保持简短", r"(详细|展开)说明|深入(分析|探讨)"),
)


def rule_conflicting(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for keep, opposite in CONFLICT_PAIRS:
        if keep in text and re.search(opposite, text):
            hits.append(
                Hit(
                    "RL009",
                    "warn",
                    f"指令自相矛盾:既有「{keep}」又有相反的要求",
                    "二选一,或者写清适用范围(如「代码保持简短,但解释要详细」)",
                    1,
                    "",
                )
            )
    return hits


RULES = [
    rule_too_short,
    rule_too_long,
    rule_vague_words,
    rule_no_output_format,
    rule_multi_step,
    rule_repeated_punct,
    rule_fullwidth_alnum,
    rule_cn_en_spacing,
    rule_conflicting,
]

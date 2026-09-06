# promptlint

[![CI](https://github.com/yange0793-dot/prompt-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/yange0793-dot/prompt-lint/actions/workflows/ci.yml)

**规则式提示词体检工具:离线、确定性、可测试——在调用模型之前,先抓住低级问题。**
Rule-based linter for prompts: offline, deterministic, testable — catch the cheap mistakes before you pay for tokens.

## 为什么是规则式

用 LLM 评审提示词是可行的,但 把 LLM 当 linter 有三个问题:结果不确定(同一输入两次跑给不同结论)、有成本、自己也需要被评审。promptlint 只做**确定性规则**:同样输入永远同样输出,零网络请求,每条规则都有单测,误报可以直接定位到代码修掉。它不解决"提示词写得好不好"这种 judgment 问题——那部分留给人和模型;它解决的是"这提示词有没有低级毛病"。

## 安装

```bash
pipx install git+https://github.com/yange0793-dot/prompt-lint      # 或
uv tool install git+https://github.com/yange0793-dot/prompt-lint   # 或
pip install git+https://github.com/yange0793-dot/prompt-lint
```

要求 Python ≥ 3.10,零第三方依赖。

> **注意 PyPI 上的 `promptlint` 不是本项目** —— 那个名字属于另一个无关的包。本项目发行名是 `prompt-lint`(`import promptlint`、命令仍是 `promptlint`),暂未发布到 PyPI,请按上面的 git 方式安装。

## 使用

```bash
promptlint my-prompt.txt                       # 体检文件
promptlint prompts/*.txt                       # 一次多个文件,末尾给合计
cat my-prompt.txt | promptlint -               # 从 stdin 读
promptlint -p "帮我优化一下这个函数,让它快点"   # 直接体检一段文本
promptlint --json my-prompt.txt                # 机器可读输出
promptlint --max-warn 0 prompts/*.txt          # 把 warn 也当失败(挂 CI 用)
```

退出码:`0` 通过;`1` 有 error,或 warn 数超过 `--max-warn`;`2` 用法/IO 错误。
默认只有 error 会让退出码非零 —— 想让 warn 也拦住流水线就加 `--max-warn N`。

多文件模式下每个文件的检出照常按 `文件:行` 定位,干净的文件也会留一行,最后给一行合计
(下面是 `promptlint examples/messy-prompt.txt examples/clean-prompt.txt --no-color` 的真实尾部):

```text
✓ examples/clean-prompt.txt  无检出
共 2 个文件:0 error, 11 warn, 2 info
```

`examples/` 里放了一对照:`messy-prompt.txt` 是毛病密集的草稿,`clean-prompt.txt` 是零检出的范例
—— 后者由测试钉住,一旦规则改动让它不再零检出,CI 会先失败。

`--json` 在单文件时是一个对象,多文件时是同形对象的数组 —— 单文件的形态不会因为这个功能变化。

对一份「毛病密集」的提示词,真实输出(节选):

```text
⚠ RL003 examples/messy-prompt.txt:1  模糊表述「优化一下」,模型只能靠猜
    └ 帮我优化一下这个函数，让它快点。大概就行，随便弄弄，
    └ 建议:换成可验证的具体要求,例如「优化一下」→「把首屏加载压到 1s 内」
⚠ RL006 examples/messy-prompt.txt:1  重复标点「！！」
    └ 非常感谢！！ 另外第１部分要用ｊｓｏｎ输出。
⚠ RL007 examples/messy-prompt.txt:2  使用了全角字母/数字,复制到代码或 JSON 里会出错
    └ 另外第１部分要用ｊｓｏｎ输出。
    └ 建议:改用半角「json」
ℹ RL004 examples/messy-prompt.txt:1  没有声明期望的输出格式
    └ 建议:明确输出形态:JSON / 表格 / 要点列表 / 字数上限
0 error, 11 warn, 2 info
```

## 规则一览

| ID | 级别 | 检查 | 说明 |
| --- | --- | --- | --- |
| RL001 | error | 提示词过短(<20 字符) | 缺少上下文,模型只能靠猜 |
| RL002 | warn | 提示词过长(>2000 字符) | 单次请求难以聚焦,建议拆步 |
| RL003 | warn | 模糊表述 | 「随便 / 大概 / 优化一下 / 搞一下」这类词逐个定位 |
| RL004 | info | 未声明输出格式 | JSON / 表格 / 字数等约定缺失 |
| RL005 | info | 多任务打包(≥4 个编号条目) | 建议拆开逐个确认 |
| RL006 | warn | 重复标点 | 「！！」「？？」草稿痕迹 |
| RL007 | warn | 全角字母/数字 | 复制进代码/JSON 会出错 |
| RL008 | info | 中英文之间缺空格 | 盘古之白 |
| RL009 | warn | 指令自相矛盾 | 「不要解释」+「解释一下」并存 |

级别语义:`error` = 大概率直接产出坏结果;`warn` = 明确的草稿气味;`info` = 改了更好。

## 扩展:加一条自己的规则

```python
from promptlint.rules import Hit
from promptlint.engine import lint_text
import promptlint.rules as rules

def rule_no_deliberate_flattery(text: str) -> list[Hit]:
    if "夸我" in text:
        return [Hit("RL900", "info", "请求吹捧会显著拉低回答的信息量", "改成请模型列出风险与不足", 1, "")]
    return []

rules.RULES.append(rule_no_deliberate_flattery)
findings = lint_text("帮我看看这个方案,记得夸我")
```

## 设计取舍

- 只做静态文本规则,不解析语义——误报率换确定性,每条规则的判定逻辑都是十几行可读代码;
- 行号与摘录直接指向问题位置,改起来不用猜;
- README 里贴的"真实输出"由测试钉住(`tests/test_examples.py`):合计行与示例文件的检出对不上时 CI 先挂,免得文档随规则漂移;
- LLM 评审器(可选、可解释、带仲裁)在路线图里,但永远不作为默认路径。

## 挂进 pre-commit

仓库自带 `.pre-commit-hooks.yaml`,在你自己的项目里这样用:

```yaml
repos:
  - repo: https://github.com/yange0793-dot/prompt-lint
    rev: v0.1.0          # 钉到 tag,别用 main
    hooks:
      - id: promptlint
        files: ^prompts/.*\.(txt|md)$   # 只体检提示词目录,按需改
        args: [--max-warn, "3"]
```

## 开发

```bash
pip install -e . pytest
pytest -q        # 24 项测试
```

## License

[MIT](LICENSE)

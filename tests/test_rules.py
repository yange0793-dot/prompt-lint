import pytest

from promptlint import lint_text


def ids_of(text):
    return {f.rule_id for f in lint_text(text)}


def test_clean_prompt_has_no_findings():
    text = (
        "你是一位资深 Python 工程师。请审查下面这个函数的时间复杂度,"
        "按「问题 → 修复建议 → 代码片段」的结构输出 JSON,每条不超过 50 字。"
    )
    assert ids_of(text) == set()


def test_too_short_is_error():
    findings = lint_text("帮我写个东西")
    assert any(f.rule_id == "RL001" and f.severity == "error" for f in findings)


def test_vague_word_detected():
    findings = [f for f in lint_text("请帮我把这个页面优化一下,输出成表格") if f.rule_id == "RL003"]
    assert len(findings) == 1
    assert findings[0].line == 1


def test_missing_output_format():
    text = "请总结这篇文章的核心观点,用中文回答,内容准确完整。" * 1
    assert len(text) >= 20
    assert "RL004" in ids_of(text)


def test_repeated_punctuation():
    assert "RL006" in ids_of("这个方案真的可以吗？？我需要确定的答复,别含糊。")


def test_fullwidth_alnum():
    findings = [f for f in lint_text("第１步要先跑测试,通过后再部署,输出处理的要点列表") if f.rule_id == "RL007"]
    assert findings and "１" in findings[0].excerpt


def test_conflicting_instructions():
    assert "RL009" in ids_of("不要解释。请解释一下你为什么这么改,输出为列表。")


def test_findings_sorted_by_severity():
    findings = lint_text("帮我写个东西,搞一下！！")
    ranks = [f.severity for f in findings]
    assert ranks == sorted(ranks, key=lambda s: {"error": 2, "warn": 1, "info": 0}[s], reverse=True)


@pytest.mark.parametrize(
    "text",
    [
        "第１步做这个,第２步做那个",  # 少于 4 个编号条目,不触发 RL005
        "正常的一句话输出 JSON",  # 太短会触发 RL001,此处只关注无其他误报
    ],
)
def test_no_false_multi_step(text):
    assert "RL005" not in ids_of(text)

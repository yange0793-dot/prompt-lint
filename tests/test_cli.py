import json

import pytest

from promptlint.cli import main


def test_exit_code_1_when_error(tmp_path, capsys):
    bad = tmp_path / "bad.txt"
    bad.write_text("帮我写个东西", encoding="utf-8")
    assert main([str(bad), "--no-color"]) == 1
    assert "RL001" in capsys.readouterr().out


def test_exit_code_0_for_clean_file(tmp_path, capsys):
    good = tmp_path / "good.txt"
    good.write_text(
        "你是一位资深 Python 工程师。请审查下面这个函数的时间复杂度,"
        "按「问题 → 修复建议 → 代码片段」的结构输出 JSON,每条不超过 50 字。",
        encoding="utf-8",
    )
    assert main([str(good), "--no-color"]) == 0


def test_json_output(tmp_path, capsys):
    bad = tmp_path / "bad.txt"
    bad.write_text("帮我写个东西", encoding="utf-8")
    assert main([str(bad), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["source"] == str(bad)
    assert data["findings"][0]["rule_id"] == "RL001"
    assert "1 error" in data["summary"]


def test_prompt_option(capsys):
    text = "随便帮我写一点东西吧,大概这样差不多就行,尽量快一点。"
    assert main(["-p", text, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    rule_ids = {f["rule_id"] for f in data["findings"]}
    assert "RL003" in rule_ids


def test_missing_file_returns_2(capsys):
    assert main(["/nonexistent/file.txt"]) == 2
    assert "读取失败" in capsys.readouterr().err


def test_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", open("/dev/null", encoding="utf-8"))
    # stdin 为空 → 触发「太短」error
    assert main(["-", "--no-color"]) == 1

"""Parser ReAct — các biến thể format model hay sinh ra."""

import pytest

from src.chatbot.react import _ACTION_RE, _FINAL_RE, _THOUGHT_RE, _parse_args, _tool_name


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('{"query": "CP3"}', {"query": "CP3"}),
        ('{"query": "CP3", "k": 2}', {"query": "CP3", "k": 2}),
        ('```json\n{"query": "CP3"}\n```', {"query": "CP3"}),
        ('```\n{"query": "CP3"}\n```', {"query": "CP3"}),
        ('Dùng: {"query": "CP3"} nhé', {"query": "CP3"}),
        ('  {"query": "CP3"}  ', {"query": "CP3"}),
    ],
)
def test_parse_args_cac_bien_the(raw, expected):
    assert _parse_args(raw) == expected


@pytest.mark.parametrize("raw", ['{"query": }', "khong phai json", "{"])
def test_parse_args_json_hong(raw):
    with pytest.raises(ValueError, match="không phải JSON hợp lệ"):
        _parse_args(raw)


@pytest.mark.parametrize("raw", ["[1, 2]", '"chuoi"', "42"])
def test_parse_args_khong_phai_object(raw):
    with pytest.raises(ValueError, match="phải là JSON object"):
        _parse_args(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "search_docs",
        "`search_docs`",
        '"search_docs"',
        "**search_docs**",
        'search_docs("CP3")',
        "search_docs(query='CP3', k=2)",
        "  search_docs  ",
    ],
)
def test_chuan_hoa_ten_tool(raw):
    assert _tool_name(raw) == "search_docs"


def test_action_re_cat_truoc_observation():
    raw = 'Thought: t\nAction: search_docs\nAction Input: {"query": "CP3"}\nObservation: cu'
    m = _ACTION_RE.search(raw)
    assert m and _parse_args(m.group("args")) == {"query": "CP3"}


def test_action_re_cat_truoc_thought_ke_tiep():
    raw = 'Action: search_docs\nAction Input: {"query": "a"}\nThought: tiep theo'
    m = _ACTION_RE.search(raw)
    assert m and _parse_args(m.group("args")) == {"query": "a"}


def test_final_re_bat_dap_an_nhieu_dong():
    m = _FINAL_RE.search("Thought: xong\nFinal Answer: dòng 1\ndòng 2")
    assert m and m.group("answer").strip() == "dòng 1\ndòng 2"


def test_thought_re_chi_lay_mot_dong():
    m = _THOUGHT_RE.search("Thought: can tim tai lieu\nAction: search_docs")
    assert m and m.group("thought").strip() == "can tim tai lieu"

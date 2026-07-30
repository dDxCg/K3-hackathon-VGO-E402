"""ToolRegistry — lỗi phải thành chuỗi Observation, không được raise ra vòng ReAct."""

from src.chatbot.mock.rag import Chunk, InMemoryRetriever, NullRetriever
from src.chatbot.mock.tools import Tool, ToolRegistry, make_search_docs


def _tool(func, name="echo") -> Tool:
    return Tool(name=name, description="d", signature="echo(x: str) -> str", func=func)


def test_register_get_names_len():
    reg = ToolRegistry()
    assert len(reg) == 0 and reg.get("echo") is None
    reg.register(_tool(lambda x: x))
    assert len(reg) == 1
    assert reg.names() == ["echo"]
    assert reg.get("echo") is not None


def test_decorator_dang_ky_tool():
    reg = ToolRegistry()

    @reg.tool("add", "cộng hai số", "add(a: int, b: int) -> int")
    def add(a: int, b: int) -> int:
        return a + b

    assert reg.names() == ["add"]
    assert reg.call("add", {"a": 1, "b": 2}) == "3"
    assert add(1, 2) == 3  # decorator trả lại hàm gốc


def test_signatures_dung_duoc_cho_prompt(registry: ToolRegistry):
    sig = registry.signatures()[0]
    assert (sig.name, sig.description, sig.signature) == (
        "search_docs",
        "Tìm đoạn tài liệu khoá học liên quan tới truy vấn.",
        "search_docs(query: str, k: int = 5) -> str",
    )


def test_tool_khong_ton_tai_tra_loi_kem_danh_sach(registry: ToolRegistry):
    out = registry.call("khong_ton_tai", {})
    assert out.startswith("Lỗi: không có tool tên 'khong_ton_tai'")
    assert "search_docs" in out


def test_sai_kwargs_thanh_chuoi_loi_khong_raise(registry: ToolRegistry):
    out = registry.call("search_docs", {"wrong": 1})
    assert out.startswith("Lỗi khi chạy 'search_docs'")
    assert "TypeError" in out


def test_tool_nem_exception_thi_nuot_thanh_chuoi():
    def boom(x: str) -> str:
        raise RuntimeError("hong roi")

    reg = ToolRegistry([_tool(boom)])
    out = reg.call("echo", {"x": "a"})
    assert "RuntimeError" in out and "hong roi" in out


def test_search_docs_format_ket_qua(retriever: InMemoryRetriever):
    out = make_search_docs(retriever)(query="CP3")
    assert out.startswith("[rubric.md] ")
    assert "CP3" in out


def test_search_docs_khong_thay():
    assert make_search_docs(NullRetriever())(query="x") == "Không tìm thấy tài liệu khớp."


def test_search_docs_truyen_k_xuong_retriever():
    r = InMemoryRetriever([Chunk(f"alpha {i}", f"{i}.md") for i in range(5)])
    assert make_search_docs(r)(query="alpha", k=2).count("[") == 2

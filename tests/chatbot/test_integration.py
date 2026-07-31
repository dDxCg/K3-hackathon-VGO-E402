"""Nối RAG + 2 tool + vòng ReAct — chạy trên payload retrieval giả, không cần ChromaDB."""

import pytest

from src.chatbot.admission_agent import ADMISSION_POLICY, build_admission_agent
from src.chatbot.agent_tools import build_registry
from src.chatbot.rag_bridge import (
    NO_GROUNDING_THRESHOLD,
    ChromaRetriever,
    cache_key,
    payload_to_chunks,
)

WEB_RESULT = {
    "rank": 1,
    "id": "chunk_web_1",
    "cosine_similarity": 0.85,
    "content": "Lộ trình 12 tuần, học online kết hợp offline.",
    "metadata": {
        "muc_lon": "5. Lộ trình 12 tuần",
        "ten_tai_lieu": "thong-tin-tuyen-sinh-...-khoa-co-ban.md",
        "source_link": "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/",
        "loai_nguon": "web",
    },
}
FB_RESULT = {
    "rank": 2,
    "id": "chunk_fb_1",
    "cosine_similarity": 0.72,
    "content": "Học viên kể là mỗi tuần khoảng 10 tiếng.",
    "metadata": {
        "ten_tai_lieu": "feedback_nguoi_dung_tren_Facebook",
        "source_link": "https://www.facebook.com/groups/2125430681651241",
        "loai_nguon": "facebook",
    },
}


def fake_payload(*results, question="Chương trình học bao lâu?"):
    return {
        "question": question,
        "embedding_model": "intfloat/multilingual-e5-large",
        "returned_results": len(results),
        "results": list(results),
    }


@pytest.fixture
def rag() -> ChromaRetriever:
    """Retriever thật, chỉ thay hàm gọi ChromaDB bằng payload tĩnh."""
    return ChromaRetriever(retrieve_fn=lambda q, top_k=5: fake_payload(WEB_RESULT, FB_RESULT))


# --- rag_bridge: đổi JSON retrieval thành Chunk -------------------------------


def test_payload_to_chunks_giu_id_va_doi_ten_loai_nguon():
    web, fb = payload_to_chunks(fake_payload(WEB_RESULT, FB_RESULT))
    assert web.text.startswith("Lộ trình 12 tuần")
    assert web.score == pytest.approx(0.85)
    assert web.metadata["chunk_id"] == "chunk_web_1"
    assert web.metadata["source_type"] == "official_web"
    assert fb.metadata["source_type"] == "community_facebook"
    assert fb.source == "feedback_nguoi_dung_tren_Facebook"


def test_payload_rong_thi_khong_co_chunk():
    assert payload_to_chunks(fake_payload()) == []


def test_grounding_theo_nguong_da_chot(rag: ChromaRetriever):
    rag.retrieve("x")
    assert rag.best_score() == pytest.approx(0.85)
    assert rag.has_grounding() is True

    weak = ChromaRetriever(retrieve_fn=lambda q, top_k=5: fake_payload({**WEB_RESULT, "cosine_similarity": 0.4}))
    weak.retrieve("x")
    assert weak.has_grounding() is False
    assert NO_GROUNDING_THRESHOLD == 0.7


def test_chunk_by_id_tich_luy_qua_nhieu_luot(rag: ChromaRetriever):
    rag.retrieve("lần 1")
    rag._retrieve_fn = lambda q, top_k=5: fake_payload({**WEB_RESULT, "id": "chunk_web_2"})
    rag.retrieve("lần 2")
    assert set(rag.chunk_by_id) == {"chunk_web_1", "chunk_fb_1", "chunk_web_2"}


# --- cache: mỗi miss là một request embedding 20-115s ------------------------


def counting_retriever(**kwargs) -> tuple[ChromaRetriever, list[str]]:
    calls: list[str] = []

    def fake(query, top_k=5):
        calls.append(query)
        return fake_payload(WEB_RESULT)

    return ChromaRetriever(retrieve_fn=fake, **kwargs), calls


def test_query_trung_thi_khong_goi_lai_api():
    rag, calls = counting_retriever()
    rag.retrieve("Chương trình học bao lâu?")
    rag.retrieve("Chương trình học bao lâu?")
    assert calls == ["Chương trình học bao lâu?"]
    assert (rag.cache_misses, rag.cache_hits) == (1, 1)


@pytest.mark.parametrize(
    "variant",
    ["chương trình học bao lâu", "Chương trình học bao lâu???", "  Chương trình  học bao lâu? "],
)
def test_khac_dau_cau_hoa_thuong_van_dung_chung_vector(variant):
    rag, calls = counting_retriever()
    rag.retrieve("Chương trình học bao lâu?")
    rag.retrieve(variant)
    assert len(calls) == 1, f"'{variant}' đáng lẽ trúng cache"


def test_khac_k_thi_phai_goi_lai():
    rag, calls = counting_retriever()
    rag.retrieve("x", k=5)
    rag.retrieve("x", k=10)
    assert len(calls) == 2


def test_cache_lru_gioi_han_kich_thuoc():
    rag, calls = counting_retriever(cache_size=2)
    for query in ("a", "b", "c", "a"):
        rag.retrieve(query)
    assert calls == ["a", "b", "c", "a"]  # "a" bị đẩy ra rồi phải gọi lại


def test_cache_key_chuan_hoa():
    assert cache_key("Chương trình  học?", 5) == cache_key("chương trình học", 5)
    assert cache_key("a", 5) != cache_key("a", 3)


def test_mot_luot_react_chi_embed_mot_lan(settings, script):
    """Hồi quy: trước đây pre-retrieve + search_docs = 2 lượt embedding mỗi câu."""
    rag, calls = counting_retriever()
    agent = build_admission_agent(settings=settings, retriever=rag, max_steps=4)
    script(
        agent.bot,
        'Thought: lấy nguồn\nAction: attach_source_link\nAction Input: {"chunk_ids": ["chunk_web_1"]}',
        "Thought: đủ\nFinal Answer: 12 tuần.",
    )
    result = agent.run("Chương trình học bao lâu?")

    assert len(calls) == 1, f"embed {len(calls)} lần: {calls}"
    assert result.retrieved[0].metadata["chunk_id"] == "chunk_web_1"


def test_hoi_lai_cau_tuong_tu_thi_dung_cache(settings, script):
    rag, calls = counting_retriever()
    agent = build_admission_agent(settings=settings, retriever=rag, max_steps=4)
    answer = "Thought: đủ\nFinal Answer: 12 tuần."
    script(agent.bot, answer, answer)
    agent.run("Chương trình học bao lâu?")
    agent.run("chương trình học bao lâu")

    assert len(calls) == 1
    assert rag.cache_hits == 1


# --- agent_tools: 2 tool thật -------------------------------------------------


def test_attach_source_link_tra_nguoc_id_thanh_url(rag: ChromaRetriever):
    registry = build_registry(rag)
    rag.retrieve("x")  # nạp chunk_by_id, như prefetch làm trong thực tế
    out = registry.call("attach_source_link", {"chunk_ids": ["chunk_web_1"]})
    assert "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh" in out
    assert "Thông tin tuyển sinh chính thức" in out
    assert "⚠" not in out


def test_attach_source_link_gan_canh_bao_cho_facebook(rag: ChromaRetriever):
    registry = build_registry(rag)
    rag.retrieve("x")
    out = registry.call("attach_source_link", {"chunk_ids": ["chunk_fb_1"]})
    assert "facebook.com/groups/2125430681651241" in out
    assert "không phải nguồn chính thức" in out


def test_attach_source_link_id_la_chuoi_tran(rag: ChromaRetriever):
    registry = build_registry(rag)
    rag.retrieve("x")
    assert "vinuni.edu.vn" in registry.call("attach_source_link", {"chunk_ids": "chunk_web_1"})


def test_attach_source_link_id_khong_ton_tai_thanh_feedback(rag: ChromaRetriever):
    registry = build_registry(rag)
    rag.retrieve("x")
    out = registry.call("attach_source_link", {"chunk_ids": ["chunk_bia_dat"]})
    assert out.startswith("Lỗi:")
    assert "Ngữ cảnh truy xuất" in out


def test_contact_support_tra_kenh_lien_he(rag: ChromaRetriever):
    out = build_registry(rag).call(
        "contact_support",
        {"reason": "out_of_scope", "user_question": "Em có nên nộp không?"},
    )
    assert "0979.489.846" in out
    assert "AIthucchien@vinuni.edu.vn" in out
    assert "Em có nên nộp không?" in out
    assert "ngoài phạm vi" in out


def test_contact_support_conflicting_hien_ca_hai_du_kien(rag: ChromaRetriever):
    out = build_registry(rag).call(
        "contact_support",
        {
            "reason": "conflicting_sources",
            "user_question": "Khai giảng ngày nào?",
            "partial_context": "Web: 01/09\nFacebook: 15/09",
        },
    )
    assert "Web: 01/09" in out and "Facebook: 15/09" in out
    assert "không tự chọn giúp" in out


def test_contact_support_reason_sai_thanh_chuoi_loi(rag: ChromaRetriever):
    out = build_registry(rag).call("contact_support", {"reason": "bia_dat", "user_question": "x"})
    assert out.startswith("Lỗi khi chạy 'contact_support'")


# --- lắp cả agent -------------------------------------------------------------


def test_agent_du_can_cu_thi_tra_loi_kem_nguon(rag: ChromaRetriever, settings, script):
    agent = build_admission_agent(settings=settings, retriever=rag, max_steps=4)
    llm = script(
        agent.bot,
        'Thought: có dữ kiện, lấy nguồn\nAction: attach_source_link\nAction Input: {"chunk_ids": ["chunk_web_1"]}',
        "Thought: đủ\nFinal Answer: Lộ trình 12 tuần. Nguồn: VinUni.",
    )
    result = agent.run("Chương trình học bao lâu?")

    assert [s.action for s in result.steps if s.action] == ["attach_source_link"]
    assert "vinuni.edu.vn" in result.steps[0].observation
    assert result.answer.startswith("Lộ trình 12 tuần")
    assert result.stopped_early is False

    system = llm.calls[0][0]["content"]
    assert "attach_source_link" in system and "contact_support" in system
    assert "no_grounding" in system  # chính sách phạm vi có trong prompt
    # Chunk nằm sẵn trong prompt kèm id, để model trích nguồn được mà không cần tool tìm.
    assert "Lộ trình 12 tuần" in system
    assert "id=chunk_web_1" in system
    assert "Đủ căn cứ" in system
    assert result.retrieved[0].metadata["chunk_id"] == "chunk_web_1"


def test_agent_khong_du_can_cu_thi_chuyen_nhan_vien(settings, script):
    weak = ChromaRetriever(retrieve_fn=lambda q, top_k=5: fake_payload({**WEB_RESULT, "cosine_similarity": 0.3}))
    agent = build_admission_agent(settings=settings, retriever=weak, max_steps=4)
    llm = script(
        agent.bot,
        'Thought: không đủ căn cứ\nAction: contact_support\nAction Input: {"reason": "no_grounding", "user_question": "Học phí năm 2030?"}',
        "Thought: xong\nFinal Answer: Mình chưa đủ căn cứ. Hotline 0979.489.846.",
    )
    result = agent.run("Học phí năm 2030?")

    system = llm.calls[0][0]["content"]
    assert "KHÔNG đủ căn cứ" in system  # kết luận ngưỡng nằm ngay trong prompt
    assert "0.300" in system
    assert result.steps[0].action == "contact_support"
    assert "0979.489.846" in result.steps[0].observation
    assert "0979.489.846" in result.answer


def test_policy_liet_ke_du_bon_reason():
    for reason in ("no_grounding", "out_of_scope", "conflicting_sources", "personal_data_request"):
        assert reason in ADMISSION_POLICY

from src.chatbot.types import Chunk
from src.demo_service import DemoService, classify_restricted


OFFICIAL_URL = (
    "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-"
    "nhan-tai-ai-thuc-chien-khoa-co-ban/"
)


class StaticRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def retrieve(self, query, k=5):
        self.calls.append((query, k))
        return self.chunks[:k]


class StubBot:
    def __init__(self):
        self.history = []
        self.received = []

    def remember(self, question, answer):
        self.history.append((question, answer))

    def chat_with_retrieved(self, question, chunks):
        self.received.append((question, chunks))
        answer = f"Lịch học có trong tài liệu [{chunks[0].source}]."
        self.remember(question, answer)
        return answer


def test_classify_restricted_covers_brief_boundaries():
    assert classify_restricted("Em có nên nộp hồ sơ không?") == "out_of_scope"
    assert classify_restricted("Kết quả hồ sơ của em đến đâu rồi?") == "personal_data_request"
    assert classify_restricted("Hồ sơ cần những gì?") is None


def test_low_score_uses_contact_support_without_llm():
    bot = StubBot()
    retriever = StaticRetriever([Chunk("gần đúng", "chunk_low", 0.69)])
    service = DemoService(retriever=retriever, bot_factory=lambda: bot)

    reply = service.chat("s1", "Một câu không đủ căn cứ")

    assert reply.path == "contact_support"
    assert reply.grounded is False
    assert reply.top_score == 0.69
    assert "AIthucchien@vinuni.edu.vn" in reply.answer
    assert bot.received == []


def test_grounded_answer_calls_llm_and_attaches_source():
    bot = StubBot()
    chunk = Chunk(
        "Học trực tiếp tại VinUni.",
        "chunk_123",
        0.88,
        {
            "chunk_id": "chunk_123",
            "loai_nguon": "web",
            "source_link": OFFICIAL_URL,
        },
    )
    service = DemoService(
        retriever=StaticRetriever([chunk]),
        bot_factory=lambda: bot,
    )

    reply = service.chat("s1", "Học ở đâu?")

    assert reply.path == "rag+attach_source_link"
    assert reply.grounded is True
    assert reply.top_score == 0.88
    assert "[chunk_123]" not in reply.answer
    assert reply.sources[0] == {
        "muc_lon": "",
        "muc_nho": "",
        "source_link": OFFICIAL_URL,
    }
    assert bot.received[0][1] == [chunk]


def test_restricted_question_skips_retrieval():
    bot = StubBot()
    retriever = StaticRetriever([])
    service = DemoService(retriever=retriever, bot_factory=lambda: bot)

    reply = service.chat("s1", "Em có đậu không?")

    assert reply.path == "contact_support"
    assert retriever.calls == []


def test_reset_drops_session_history():
    bots = []

    def factory():
        bot = StubBot()
        bots.append(bot)
        return bot

    service = DemoService(retriever=StaticRetriever([]), bot_factory=factory)
    service.chat("same", "Câu một")
    service.reset("same")
    service.chat("same", "Câu hai")
    assert len(bots) == 2


def test_missing_model_citation_uses_top_chunk_json_source():
    class NoCitationBot(StubBot):
        def chat_with_retrieved(self, question, chunks):
            return "Lịch học có trong tài liệu."

    chunk = Chunk(
        "Lịch học.",
        "chunk_top",
        0.9,
        {"chunk_id": "chunk_top", "loai_nguon": "web", "source_link": OFFICIAL_URL},
    )
    reply = DemoService(
        retriever=StaticRetriever([chunk]), bot_factory=NoCitationBot
    ).chat("s1", "Lịch học?")
    assert reply.answer == "Lịch học có trong tài liệu."
    assert reply.sources == [
        {"muc_lon": "", "muc_nho": "", "source_link": OFFICIAL_URL}
    ]


def test_answer_removes_generic_source_and_chunk_markers():
    class NoisyBot(StubBot):
        def chat_with_retrieved(self, question, chunks):
            return "Dữ kiện từ tài liệu. [source]\n\nNguồn: [chunk_top]"

    chunk = Chunk(
        "Dữ kiện.",
        "chunk_top",
        0.9,
        {
            "chunk_id": "chunk_top",
            "muc_lon": "I. THÔNG TIN CHUNG",
            "muc_nho": "2. Địa chỉ đào tạo",
            "loai_nguon": "web",
            "source_link": OFFICIAL_URL,
        },
    )
    reply = DemoService(
        retriever=StaticRetriever([chunk]), bot_factory=NoisyBot
    ).chat("s1", "Địa điểm?")
    assert reply.answer == "Dữ kiện từ tài liệu."
    assert reply.sources == [
        {
            "muc_lon": "I. THÔNG TIN CHUNG",
            "muc_nho": "2. Địa chỉ đào tạo",
            "source_link": OFFICIAL_URL,
        }
    ]

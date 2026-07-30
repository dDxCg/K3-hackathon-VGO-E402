# Review code — package `src/chatbot`

Ngày: 2026-07-30 · Phạm vi: toàn bộ [src/chatbot/](../../src/chatbot/) · Trạng thái: chạy được, 71 test xanh

## 1. Kiến trúc

```
src/chatbot/
├── config.py         Settings.from_env() — đọc .env
├── prompt.py         render_system_prompt() — Jinja2, StrictUndefined
├── prompts/system.j2 template: nguyên tắc + tool signature + giao thức ReAct + ngữ cảnh RAG
├── chatbot.py        Chatbot — chat/stream/complete/retrieve, history
├── react.py          ReActAgent — vòng Thought/Action/Observation/Final Answer
├── __main__.py       CLI: --react --trace --max-steps
└── mock/             DEV/TEST ONLY: rag.py (Chunk/Retriever/InMemory/Null), tools.py (Tool/ToolRegistry/make_search_docs)
```

Nguyên tắc phân tầng: `config → prompt → chatbot → react → __main__`, không có import vòng. `mock/` là tầng lá, chỉ bị import vào chứ không import ngược lên.

### Điểm mạnh
- **Một điểm chạm mạng duy nhất.** `Chatbot.complete()` ([chatbot.py:69](../../src/chatbot/chatbot.py#L69)) là hàm duy nhất gọi API trong đường ReAct. Nhờ đó toàn bộ vòng lặp test được offline mà không cần thư viện mock HTTP.
- **Prompt tách khỏi code.** Sửa văn phong, thêm ràng buộc, đổi ngôn ngữ chỉ động vào `system.j2`. `StrictUndefined` biến lỗi thiếu biến thành exception lúc render thay vì prompt câm lặng bị khuyết một khối.
- **Tool contract nhẹ.** Chỉ cần object có `.name/.description/.signature` và gọi được bằng kwargs. Không phụ thuộc JSON-schema hay function-calling API riêng của provider → đổi provider không phải viết lại.
- **Lỗi tool là dữ liệu, không phải exception.** `ToolRegistry.call()` nuốt mọi exception thành chuỗi tiếng Việt ([mock/tools.py:56](../../src/chatbot/mock/tools.py#L56)) rồi đưa vào `Observation`. Đây chính là vòng phản hồi: model đọc lỗi và tự sửa ở bước sau. Đã quan sát thật: sai tên tham số ở bước 1, gọi đúng ở bước 2.
- **Trace đầy đủ.** `ReActResult` giữ `steps` (thought/action/args/observation/raw), `retrieved`, `stopped_early` — đủ dữ liệu để đo số bước, tỉ lệ gọi tool hỏng, tỉ lệ chạm trần bước cho CP3.

## 2. Vòng phản hồi ReAct — các quyết định đáng chú ý

| Cơ chế | Vị trí | Lý do |
|---|---|---|
| Mồi lượt assistant bằng `"Thought:"` | [react.py:88](../../src/chatbot/react.py#L88) | `gpt-4o-mini` bỏ qua giao thức và trả lời thẳng nếu không ép format. Đây là fix có căn cứ quan sát, không phải phòng xa. |
| `stop=["Observation:"]` | [react.py:90](../../src/chatbot/react.py#L90) | Chặn model tự bịa kết quả tool rồi suy luận tiếp trên dữ liệu ma. |
| Chuẩn hoá tên tool `_tool_name()` | [react.py:40](../../src/chatbot/react.py#L40) | Model viết `Action: search_docs("CP3")`, backtick, hoặc `**bold**`. Không chuẩn hoá thì mất trắng 1 bước cho lỗi "không có tool tên". |
| Repeat-guard | [react.py:114](../../src/chatbot/react.py#L114) | Quan sát thật: model gọi `search_docs` 3 lần với query gần giống nhau rồi bỏ cuộc. Cảnh báo trong Observation cắt vòng xoay. |
| Ép chốt khi hết `max_steps` | [react.py:128](../../src/chatbot/react.py#L128) | Không có thì user nhận về chuỗi `Action:` dở dang. |
| RAG chạy **trước** vòng lặp | [react.py:70](../../src/chatbot/react.py#L70) | Chunk vào thẳng system prompt; `search_docs` chỉ để agent tự truy vấn thêm khi cần reformulate. Câu dễ trả lời trong 1 bước, không tốn lượt gọi tool. |

## 3. Vấn đề còn tồn

### Cao
- **`mock/` là dependency cứng của code production.** `chatbot.py:9` và `react.py:9-10` import trực tiếp `from .mock.rag import ...` / `from .mock.tools import ...`. Đúng theo yêu cầu hiện tại (dev trước, integrate sau), nhưng khi `src/rag` và `src/tools` thật xong thì phải sửa import ở 2 chỗ này. Cách sạch hơn: đưa `Chunk`, `Retriever` (Protocol), `Tool`, `ToolRegistry` lên `src/chatbot/types.py` — production import từ đó, `mock/` chỉ còn phần *triển khai* test. Chưa làm vì đang cố tình gom hết vào `mock/`.
- **`_remember` là API riêng nhưng bị gọi từ ngoài.** `ReActAgent.run()` gọi `self.bot._remember(...)` 4 lần. Nên đổi thành method công khai (`remember`) hoặc cho `run()` tự giữ history.

### Trung bình
- **`system_prompt()` có tác dụng phụ.** Nó gọi `retrieve()`, tức là *ghi* vào `self.last_retrieved`. Tên hàm nghe như thuần tuý đọc. Người đọc code dễ tưởng gọi được nhiều lần vô hại — thực tế mỗi lần gọi là một lượt truy vấn retriever.
- **Nhánh "không Action không Final Answer" trả nguyên văn output.** [react.py:103](../../src/chatbot/react.py#L103) đưa cả chuỗi bắt đầu bằng `"Thought: ..."` ra cho người dùng. Test `test_khong_action_khong_final_thi_lay_ca_output` ghi nhận hành vi này. Nên cắt nhãn `Thought:` trước khi trả.
- **Không có timeout / retry.** `OpenAI()` khởi tạo trần ([chatbot.py:27](../../src/chatbot/chatbot.py#L27)). OpenRouter treo là CLI treo theo. Thêm `timeout=` và `max_retries=` vào Settings.
- **`stream()` không hỗ trợ ReAct.** Chỉ chế độ chat thường stream được; `--react` chờ trọn vòng lặp mới in. Với `max_steps=6` người dùng nhìn màn hình trắng khá lâu. Ít nhất nên in trace theo thời gian thực.

### Thấp
- `_FINAL_RE` dùng `.*` với `DOTALL` → nếu model viết `Final Answer:` rồi vẫn nói thêm `Thought:` phía sau, cả phần đuôi bị nuốt vào đáp án.
- `Settings.from_env()` đọc `OPENAI_API` (không phải tên chuẩn `OPENAI_API_KEY`). Cố ý theo `.env` sẵn có, nhưng dễ gây nhầm cho người mới vào repo — nên ghi rõ trong `.env.example`.
- `history` không giới hạn độ dài. Hội thoại dài sẽ đội token và cuối cùng vượt context window. Cần cắt cửa sổ trượt trước khi demo dài.
- `context` (ngữ cảnh bổ sung) là chuỗi tĩnh gán lúc khởi tạo, chưa có đường cập nhật giữa phiên.

## 4. Việc nên làm trước khi integrate

1. Nâng `Chunk` / `Retriever` / `Tool` / `ToolRegistry` lên `src/chatbot/types.py`; `mock/` chỉ giữ `InMemoryRetriever`, `NullRetriever`, `make_search_docs`. Sau đó thay `src/rag` thật không phải sửa `chatbot.py`.
2. Đổi `_remember` → `remember` (API công khai).
3. Thêm `timeout` + `max_retries` vào `Settings`.
4. Cắt cửa sổ history theo số lượt hoặc số token.
5. Chốt tên biến môi trường trong `.env.example` cho khớp `config.py`.

## 5. Kết luận

Kiến trúc đúng cho giai đoạn hackathon: mỏng, không framework, mọi quyết định đều lần được về một dòng code. Vòng ReAct có đủ cơ chế chống hỏng thực tế (format sai, tool lỗi, lặp vô ích, chạm trần bước), và mỗi cơ chế đều sinh ra từ một lần quan sát model làm sai chứ không phải phòng thủ suy diễn. Nợ kỹ thuật lớn nhất là ranh giới `mock/` — cố ý và đã ghi rõ, xử lý gọn bằng một lần tách file khi integrate.

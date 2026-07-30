# Báo cáo đánh giá hệ thống

Ngày chạy: 2026-07-30  
Môi trường: Windows, Python 3.10  
Kết luận: **PASS — toàn bộ test offline và RAG local hoạt động ổn định.**

## 1. Kết quả test

Lệnh:

```powershell
python -m pytest tests -q --durations=10
```

Kết quả:

| Chỉ số | Giá trị |
| --- | ---: |
| Passed | 110 |
| Failed | 0 |
| Deselected | 11 |
| Thời gian | 4,07 giây |

`11 deselected` thuộc marker `live` và `e2e`, bị loại theo cấu hình mặc định vì gọi chat API thật. Đây không phải test lỗi.

Test chậm nhất:

| Test | Thời gian |
| --- | ---: |
| `test_http_health_page_chat_and_reset` | 0,91 giây |
| `test_http_rejects_empty_message` | 0,51 giây |

Các nhóm đã kiểm tra gồm chatbot, ReAct loop, prompt, RAG bridge, tool registry, source attachment, contact support, demo service và HTTP API.

## 2. Kiểm tra RAG local

### Schema và ChromaDB

```powershell
python src\rag\embedding.py --validate-only
```

| Kiểm tra | Kết quả |
| --- | --- |
| `chunks.json` | Hợp lệ |
| Số chunks | 82 |
| Số records Chroma | 82 |
| Model | `intfloat/multilingual-e5-large` |
| Vector dimension | 1.024 |
| Distance metric | cosine |
| Embedding backend | local-only |

### Smoke retrieval thật

Câu hỏi:

```text
Chương trình học trong bao lâu?
```

Kết quả top 1:

| Field | Giá trị |
| --- | --- |
| Chunk ID | `chunk_9286a7121125a5ea` |
| Nội dung | Lộ trình 12 tuần, mô hình 3+3+6 |
| Cosine similarity | `0.848624` |
| Model | `intfloat/multilingual-e5-large` local |
| Cold-start retrieval | 19,4 giây |

Kết quả đúng ngữ nghĩa câu hỏi. Metadata giữ đủ `source_link`, `loai_nguon`, `source_file` và `embedding_model` cho tầng chatbot/tool.

## 3. Kiểm tra kỹ thuật

```powershell
python -m compileall -q src eval
```

- Compile thành công, không có syntax error.
- Không còn reference tới `local_embedding.py` đã xóa.
- Không còn embedding API, API key embedding, HTTP embedding hoặc lexical fallback.
- `retrieval.py` gọi trực tiếp `embedding.embed_query()`.
- `rag_bridge.py` chuyển payload RAG sang `Chunk` chatbot và giữ registry nguồn cho `attach_source_link`.

## 4. Đánh giá

| Thành phần | Trạng thái |
| --- | --- |
| Chunking/JSON contract | PASS |
| E5-large local embedding | PASS |
| Chroma indexing/retrieval | PASS |
| RAG ↔ chatbot bridge | PASS |
| Tool `attach_source_link` | PASS |
| Tool `contact_support` | PASS |
| ReAct orchestration | PASS |
| Demo HTTP API | PASS |
| Chat provider thật | Chưa chạy trong lượt này |

Hệ thống đủ điều kiện chạy demo offline ở tầng RAG. Muốn xác nhận model chat/provider thật, chạy riêng `pytest -m live` hoặc `pytest -m e2e`; các lệnh này cần `OPENAI_API` và có thể phát sinh chi phí/network.

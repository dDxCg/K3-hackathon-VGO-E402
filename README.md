# Trợ Lý Tư Vấn Tuyển Sinh Có Căn Cứ (AI Admission Assistant) — Nhóm VGO-E402

Dự án phát triển trợ lý AI hỗ trợ đối chiếu thông tin tuyển sinh dành cho ứng viên quan tâm đến **Chương trình Đào tạo Nhân tài AI Thực Chiến** của VinUni. Dự án thuộc **Hướng C — Làn mở (Open Lane)** trong khuôn khổ chương trình Mini Hackathon AI (Batch 03).

---

## Thành viên & Phân công nhiệm vụ

| Họ và tên | Mã học viên | Vai trò & Phân công trách nhiệm chính |
| :--- | :--- | :--- |
| **Lương Thanh Trang** | 2A202601363 | **Team Lead, PM, UI Designer**|
| **Nguyễn Thanh Hoàn** | 2A202601201 | **RAG System Developer**|
| **Đỗ Đức Cường** | 2A202601455 | **System Prompt & Evaluation Engineer**|
| **Đỗ Tuấn Kiệt** | 2A202601335 | **Tools & Guardrail Engineer**|

---

## Mô tả dự án & Bài toán thực tế

### 1. Pain Point (Nỗi đau của người dùng)
Ứng viên đang cân nhắc nộp hồ sơ vào chương trình AI Thực Chiến phải đối mặt với tình trạng thông tin tuyển sinh rải rác:
- Thông tin chính thức nằm rải rác trên website VinUni, handbook tuyển sinh dạng PDF.
- Thông tin phi chính thức xuất hiện tràn lan trên các hội nhóm Facebook cộng đồng, thường bị cũ, sai lệch phiên bản, hoặc thiếu chính xác.
- **Hậu quả**: Ứng viên khó đối chiếu các ràng buộc của chương trình (lịch học full-time dày đặc, địa điểm học, điều kiện nộp hồ sơ) với hoàn cảnh cá nhân, dẫn đến việc bỏ lỡ kỳ tuyển sinh hoặc chuẩn bị sai hồ sơ.

### 2. Core JTBD (Công việc cốt lõi)
*Đối chiếu các ràng buộc tuyển sinh của đúng khóa đang tuyển với hoàn cảnh cá nhân để đưa ra quyết định có tiếp tục chuẩn bị hồ sơ hay dừng lại.*

### 3. Lát cắt Trải nghiệm (One-Sentence Slice)
> **Ứng viên chuẩn bị nộp hồ sơ** hỏi một câu hỏi ràng buộc tuyển sinh; **Hệ thống AI** tự động xác định xem câu hỏi có đủ căn cứ trong bộ dữ liệu đã được làm sạch hay không; **Người dùng** nhận được câu trả lời chính xác đính kèm nguồn trích dẫn tương ứng (hoặc chuyển sang kênh hỗ trợ chính thức nếu không đủ căn cứ/ngoài thẩm quyền).

---

## 💡 Giải pháp: Tự động hóa có điều kiện (Conditional Automation)

Hệ thống hoạt động theo nguyên tắc cốt lõi: **Đưa dữ kiện rõ ràng, không kết luận thay**, kết hợp chốt chặn an toàn đa tầng:

```
                  [Câu hỏi của ứng viên]
                            │
                            ▼
              ┌───────────────────────────┐
              │ Classify Restricted?      │
              │ (Regex / Deterministic)   │
              └─────────────┬─────────────┘
                            │
              ┌─────────────┴─────────────┐
        CÓ    │                           │ KHÔNG
   ┌──────────▼──────────┐         ┌──────▼──────┐
   │ Chuyển hỗ trợ người │         │ Query RAG   │
   │ (contact_support)   │         │ (ChromaDB)  │
   └─────────────────────┘         └──────┬──────┘
                                          │
                           ┌──────────────┴──────────────┐
                           │   Similarity Score >= 0.7?  │
                           └──────────────┬──────────────┘
                                          │
                                   ┌──────┴──────┐
                            KHÔNG  │             │ CÓ
                         ┌─────────▼─────────┐ ┌─▼──────────────────┐
                         │ Chuyển hỗ trợ     │ │ LLM tạo câu trả lời│
                         │ (contact_support) │ │ (Grounding facts)  │
                         └───────────────────┘ └─────────┬──────────┘
                                                         │
                                               ┌─────────▼──────────┐
                                               │ Gắn link nguồn     │
                                               │ attach_source_link │
                                               └─────────┬──────────┘
                                                         │
                                                         ▼
                                               [Hiện UI cho ứng viên]
```

### Các chốt chặn thông minh:
1. **Deterministic Guardrail Router**: Lớp lọc tĩnh (trước LLM) sử dụng Regex để chặn và chuyển kênh ngay lập tức các yêu cầu:
   - Tra cứu dữ liệu cá nhân nhạy cảm (Ví dụ: trạng thái hồ sơ của email/mã hồ sơ cụ thể).
   - Yêu cầu tư vấn chủ quan (Ví dụ: "Em có nên nộp không?", "Khả năng đậu của em cao không?").
   - Phát ngôn cam kết đầu ra/mức lương (Tránh cam kết sai chính sách).
2. **Cơ chế No-Grounding Fallback (Ngưỡng tự tin)**: Hệ thống tính toán cosine similarity của các chunks truy xuất. Nếu điểm tương đồng cao nhất dưới `0.7`, hệ thống từ chối trả lời (tránh LLM tự bịa hoặc dùng kiến thức nền) và chuyển qua Tool 1 (`contact_support`).
3. **Cơ chế Phân loại Nguồn (Source Classification)**:
   - **Nguồn chính thức (Official Web/Handbook)**: Hiển thị liên kết trực tiếp kèm nhãn uy tín.
   - **Nguồn cộng đồng (Community Facebook)**: Tự động đính kèm cảnh báo: *"Đây là chia sẻ cộng đồng, không phải nguồn chính thức. Khi khác biệt, ưu tiên thông tin chính thống từ VinUni"*.

---

## Kỹ thuật sử dụng & Stack công nghệ

### 1. Vector Database & RAG (Retrieval-Augmented Generation)
- **Local Embedding Model**: `intfloat/multilingual-e5-large` (1.024 chiều), toàn bộ quy trình encode văn bản và câu hỏi chạy local trên CPU/GPU để bảo mật dữ liệu tuyệt đối.
  - Sử dụng prefix `passage:` cho tài liệu đầu vào (document) và `query:` cho câu hỏi của người dùng (query).
- **Vector DB**: **ChromaDB** chạy ở chế độ Persistent Client, lưu trữ cục bộ tại `src/rag/chroma_db/` sử dụng khoảng cách **Cosine Similarity**.
- **Cấu trúc Chunking**: Hệ thống phân tích cú pháp Markdown dựa trên đề mục phân cấp (Mục lớn - Mục nhỏ - Mục con) để giữ trọn vẹn ngữ cảnh. Breadcrumbs đề mục được đưa trực tiếp vào vector đầu vào của mỗi chunk.

### 2. Chatbot Orchestration & Agent Tools
- **LLM Engine**: `openai/gpt-4o-mini` (hoặc các mô hình OpenAI-compatible) cấu hình qua thư viện `openai` Python SDK.
- **Prompt Engineering**: System Prompt động dựng qua template **Jinja2** (`system.j2`), hỗ trợ cả cấu trúc phản hồi trực tiếp lẫn giao thức suy luận **ReAct**.
- **Agent Tools**:
  - `attach_source_link`: Tự động đối chiếu ID chunk được LLM trích dẫn và liên kết với URL nguồn gốc từ metadata.
  - `contact_support`: Trả về thông tin liên hệ tuyển sinh VinUni (Hotline, Email, Phụ trách tuyển sinh) cùng một **câu hỏi soạn sẵn** được tóm tắt từ câu hỏi của người dùng (HAX G9 - Sửa đổi dễ dàng).
- **LRU Cache**: Tích hợp cache LRU lưu kết quả embedding cho câu hỏi lặp lại, tăng tốc độ phản hồi và giảm tải CPU.

### 3. Web Application & Frontend
- **Backend**: Python HTTP Server (`ThreadingHTTPServer` trong thư viện chuẩn `http.server`) phục vụ giao thức API gọn nhẹ, ổn định và nhanh chóng (`POST /api/chat`, `POST /api/reset`, `GET /api/health`).
- **Frontend**: Giao diện chat widget hiện đại, premium (`prototype.html`) nhúng các chip câu hỏi gợi ý nhanh, tích hợp nguồn trích dẫn, khu vực nút đánh giá feedback (👍/👎), và hỗ trợ chế độ responsive trên nhiều thiết bị.

---

## 📁 Cấu trúc Repository

```text
VGO-K3-AI-Product-Hackathon/
├── .env.example               # File cấu hình biến môi trường mẫu
├── pyproject.toml             # Quản lý dependency và metadata dự án (uv/pip)
├── uv.lock                    # File lock phiên bản dependency của uv
├── prototype.html             # Giao diện demo chính (HTML/JS/CSS thuần)
├── demo-slides.pdf            # Slide thuyết trình 6 trang về dự án
├── spec.md                    # Bản đặc tả kỹ thuật sản phẩm AI (AI Spec)
├── Team.md                    # Danh sách thành viên và vai trò
│
├── data/                      # Thư mục chứa dữ liệu tri thức của dự án
│   ├── web/                   # Dữ liệu cào (crawl) từ website VinUni
│   │   ├── _raw/              # Dữ liệu thô sau khi cào
│   │   └── _clean/            # Dữ liệu sạch định dạng Markdown (được ingest vào DB)
│   └── Data_FaceBook_ckean/   # Dữ liệu Facebook feedback cộng đồng đã được làm sạch
│
├── src/                       # Mã nguồn ứng dụng
│   ├── app.py                 # HTTP Server phục vụ giao diện và API
│   ├── demo_service.py        # Service trung gian điều phối Router, RAG và Agent Tools
│   ├── chatbot/               # Module chatbot & Prompting
│   │   ├── chatbot.py         # Client gọi LLM (OpenAI SDK/OpenRouter)
│   │   ├── config.py          # Đọc biến môi trường cấu hình model
│   │   ├── prompt.py          # Xử lý render prompt qua Jinja2
│   │   ├── prompts/           # Thư mục chứa template prompt
│   │   │   └── system.j2      # Jinja2 template cho System Prompt
│   │   ├── rag_bridge.py      # Adapter chuyển đổi kết quả từ RAG sang class Chunk
│   │   ├── react.py           # Engine hỗ trợ giao thức ReAct (Thought-Action-Observation)
│   │   └── types.py           # Định nghĩa các kiểu dữ liệu dùng trong module
│   ├── rag/                   # Module RAG & Vector DB
│   │   ├── chunking.py        # Script tiền xử lý và cắt nhỏ tài liệu Markdown
│   │   ├── chunks.json        # File JSON chứa dữ liệu chunks trung gian sau khi cắt
│   │   ├── download_model.py  # Script tải mô hình embedding local về máy
│   │   ├── embedding.py       # Tạo vector embedding bằng E5 local và lưu vào ChromaDB
│   │   └── retrieval.py       # Script truy xuất (retrieval) top-k chunks
│   ├── tools/                 # Các công cụ (tools) của Agent
│   │   ├── attach_source_link.py  # Tool lấy và gắn link nguồn từ metadata
│   │   └── contact_support.py     # Tool cung cấp thông tin liên hệ và câu hỏi soạn sẵn
│   └── crawl/                 # Script cào dữ liệu
│       └── web_crawl.py       # Crawler dữ liệu tuyển sinh sử dụng crawl4ai
│
├── eval/                      # Đánh giá chất lượng & Benchmarks
│   ├── questions.json         # Danh sách câu hỏi kiểm thử (Golden set)
│   ├── benchmark_embedding.py # Đo thời gian nạp model và truy xuất embedding local
│   ├── run_eval.py            # Chạy đánh giá chất lượng tự động trên Golden set
│   └── results/               # Kết quả benchmark
│       ├── embedding-benchmark.json
│       └── embedding-benchmark.md
│
├── tests/                     # Hệ thống test tự động (Pytest)
│   ├── chatbot/               # Unit/Integration tests cho logic chatbot offline
│   ├── e2e/                   # Test End-to-End gọi qua model thật và RAG thật
│   └── test_app.py            # Test tích hợp API endpoint của HTTP server
└── ui/                        # Chứa các tài nguyên giao diện (ảnh, icon, mascot)
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Chuẩn bị môi trường
Dự án yêu cầu Python phiên bản `>= 3.13`. Khuyên dùng công cụ `uv` để quản lý dependencies nhanh chóng.

Cài đặt dependencies:
```powershell
uv pip install -r pyproject.toml
```
*(Hoặc dùng pip truyền thống: `pip install -e .`)*

### 2. Cấu hình biến môi trường
Tạo file `.env` từ `.env.example` và điền khóa API của bạn:
```env
OPENAI_API=your_openrouter_or_openai_api_key
OPENAI_MODEL=openai/gpt-4o-mini
LOCAL_EMBEDDING_MODEL_PATH=models/intfloat-multilingual-e5-large
LOCAL_EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=8
CHROMA_DIR=src/rag/chroma_db
CHROMA_COLLECTION=ai_thuc_chien_chunks
```

### 3. Tải mô hình Embedding Local (E5-large)
Tải mô hình `intfloat/multilingual-e5-large` về thư mục `models/` (dung lượng ~2.1 GB):
```powershell
python -m src.rag.download_model
```

### 4. Build Vector Index (ChromaDB)
Tiền xử lý và chia chunk dữ liệu:
```powershell
python src/rag/chunking.py
```
Tạo embedding và lưu vào ChromaDB (thêm tham số `--recreate` để xóa DB cũ nếu có):
```powershell
python src/rag/embedding.py --recreate
```

### 5. Khởi chạy Web Server & Trải nghiệm
Khởi động HTTP server:
```powershell
python -m src.app
```
Giao diện demo sẽ chạy tại: **`http://127.0.0.1:8000`**. Bạn có thể mở trình duyệt để trò chuyện và kiểm thử trợ lý tuyển sinh.

---

## Đánh giá & Kiểm thử

### Chạy hệ thống test offline (Pytest)
Hệ thống tích hợp hơn 110 bài test tự động cho cơ chế chatbot, tool routing, và server API:
```powershell
python -m pytest -q
```

### Đo đạc hiệu năng Embedding & Retrieval
Kiểm tra hiệu năng truy xuất cục bộ và sinh báo cáo markdown:
```powershell
python -m eval.benchmark_embedding
```
Báo cáo kết quả sẽ được ghi nhận tại `eval/results/embedding-benchmark.md`.

---

## Bảo mật dữ liệu được cung cấp

Dữ liệu được sử dụng trong thư mục `data/` là thông tin tuyển sinh và phản hồi thực tế của học viên đã được ẩn danh. Nhóm cam kết tuân thủ nghiêm ngặt các quy định bảo mật:
1. Chỉ sử dụng dữ liệu trong phạm vi Hackathon cho mục đích huấn luyện RAG, xây dựng Golden set và demo prototype.
2. Không chia sẻ dữ liệu ra bên ngoài, không đăng tải lên mạng xã hội hoặc các kho lưu trữ công khai.
3. Không commit tệp tin dữ liệu thô hoặc bản ghi hội thoại gốc dài vào repo.
4. Không cố gắng khôi phục hoặc suy ngược danh tính học viên từ dữ liệu đã ẩn danh.

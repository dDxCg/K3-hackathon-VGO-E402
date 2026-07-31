# Báo cáo eval — hệ thống RAG AI Thực Chiến

Chốt 2026-07-30. Đối tượng: `admission_agent` (RAG ChromaDB + ReAct + 2 tool).

Phạm vi tài liệu này: **chỉ eval**. Test đơn vị offline (`tests/`) không nằm trong đây — chúng đã đủ dùng và đang xanh (`pytest -q`: 97 passed, 3 skipped).

---

## 1. Tài sản eval hiện có

| Thành phần | File | Quy mô | Trạng thái |
|---|---|---|---|
| Golden set | `eval/questions.json` | 45 case | ✅ dùng được |
| Bộ RAGAS lite | `eval/ragas_set.json` | 23 sample | ✅ dữ liệu xong |
| LLM judge | `eval/judge.py` + `eval/run_ragas.py` | 3 metric, 26 test | ✅ code xong, **chưa chạy thật** |
| Runner e2e | `eval/run_eval.py` | — | ⚠️ chạy được, thiếu metric |
| Kết quả | `eval/results.json` | **1 case, lỗi** | ❌ chưa từng có full run |
| Retrieval eval | *chưa tồn tại* | 0 | ❌ trống hoàn toàn |
| Báo cáo tự động | *chưa tồn tại* | 0 | ❌ trống hoàn toàn |
| Benchmark embedding | `eval/benchmark_embedding.py` | 3 metric | ✅ đã chạy |

---

## 2. Golden set — `eval/questions.json` (45 case)

| Chiều | Phân bố |
|---|---|
| Category | in_scope 19 · out_of_scope 12 · no_grounding 5 · safety 5 · conflicting 2 · source_labeling 1 · mixed_scope 1 |
| Difficulty | easy 14 · medium 17 · hard 14 |
| Type | single 30 · multi 15 |
| Nguồn | handwritten 35 · **chatlog thật 10** |
| `expect` | pass 14 · fail 6 · **unknown 25** (case mới, chưa từng chạy) |
| Gold chunk | 23 case có gold, **15 multi-hop** (≥2 chunk) · 22 case negative (gold rỗng) |
| Gate | 12 ứng viên, **chưa case nào xác nhận 3/3** |

Đáp ứng rubric `04-rubric.md` R4: ≥20 case ✅ · ≥2 case mỗi mức khó ✅ · ≥10 case chatlog ✅.

### Loại check đang dùng

| Check | Lần | Vai trò |
|---|---|---|
| `answer_none` | 29 | chặn bịa — check quan trọng nhất |
| `answer_any` | 26 | dữ kiện phải xuất hiện |
| `tools_all` | 12 | tool bắt buộc |
| `not_stopped_early` | 9 | không chạm trần `max_steps` |
| `tools_forbidden` | 6 | chặn gọi tool thừa |
| `tools_any` | 5 | ít nhất một tool |
| `answer_all` | 4 | mọi dữ kiện phải có |
| `min_steps` | 4 | phân biệt multi-step thật |

### Bốn case đắt nhất

- **N02 bảo lưu** — mâu thuẫn nguồn có thật: sổ tay chính thức nói *"chương trình không áp dụng chính sách bảo lưu"* (`chunk_781c9a7c3342d798`), Facebook nói *"có thể cho phép"* (`chunk_0d48cea16a4e7bc5`). Trả lời sai = đưa thông tin trái quy định cho người dùng.
- **C04 "tool calling là gì"** — hard negative. Corpus có nhắc "AI Agent, RAG, ReAct" trong phần nội dung đào tạo nên retrieval chắc chắn trả chunk điểm cao, nhưng đây là câu hỏi học thuật, bot không được giảng bài.
- **M08** — *"100% học viên đạt chuẩn khóa I được mời làm việc"* có thật trong corpus (`chunk_72c2a943cf6cc1e7`). Vế đầu grounded, vế sau là dự đoán cá nhân — đo khả năng tách hai vế.
- **S07 "thủ đô nước Pháp"** — bằng chứng ngưỡng 0.7 đang chết: `docs/chatbot-e2e-report.md` §5 đo được score **0.743** cho câu hoàn toàn lạc đề.

### Vì sao chatlog chỉ làm được negative set

`data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`: 2522 dòng, 585 hội thoại, 1261 tin nhắn student, **100% `conversation_mode = in_class`** — toàn sinh viên hỏi trợ giảng về slide bài giảng. Lọc từ khoá tuyển sinh ra 19 dòng, cả 19 đều là *nội dung slide* chứa chữ "đăng ký môn học".

⇒ **Không có câu hỏi tuyển sinh nào.** 10 case chatlog vì vậy là out_of_scope / no_grounding, không có case in_scope nào lấy được từ nguồn này. Giữ nguyên chính tả gốc kể cả lỗi gõ (`"...ở đaau"`) vì đó là phân bố thật người dùng gõ.

---

## 3. Bộ RAGAS lite — `eval/ragas_set.json` (23 sample)

Lọc từ `questions.json` bằng quy tắc cơ học `gold_chunk_ids != []`.

**Vì sao không dùng cả 45 case:** 22 case negative khi trả lời **đúng** thì answer là template `contact_support` — cùng một chuỗi hotline cho mọi case. Chấm `faithfulness` lên đó ra ~0 với case **đúng**, metric quay ngược đầu và kéo tụt điểm trung bình. Nhóm negative đo bằng abstention correctness.

| Trường | Nội dung |
|---|---|
| `question` | khớp từng ký tự với `questions.json` |
| `reference` | 23 câu trả lời chuẩn viết tay từ chính gold chunk |
| `gold_chunk_ids` + `gold_contexts` | text nhúng sẵn — judge không cần mở `chunks.json` |
| `gold_source_types` | `web` / `facebook` — để judge kiểm nhãn nguồn cộng đồng |

Phân bố: in_scope 19 · conflicting 2 · source_labeling 1 · mixed_scope 1. 15 multi-hop, 11 case có chunk Facebook. File 54 KB.

**Metric dự kiến:** `faithfulness`, `answer_relevancy`, `answer_correctness` — cần judge. Context precision/recall tính bằng gold, không dùng LLM.

**Cố ý không làm:** `context_recall` kiểu RAGAS gốc (nhờ LLM đối chiếu answer với reference). Bản gốc làm vòng vì thiếu ground-truth chunk; ta có gold nên tính recall chính xác và miễn phí.

**Không cài package `ragas`:** đã kiểm chứng `ragas==0.4.3` resolve được trên Python 3.13 nhưng kéo theo **92 package** (`datasets`, `langchain-core`, `langgraph`, `pandas`, `numpy`). Tự mô phỏng 3 metric.

**Lưu ý vận hành:** file tĩnh, MVP. Sửa `questions.json` thì phải sửa tay file này.

---

## 4. Gap — xếp theo mức nguy hiểm

### G1. Retrieval eval chưa tồn tại — **trống hoàn toàn**

`gold_chunk_ids` của 23 case đang không ai đọc. Không có Hit@k, Recall@k, MRR, Precision@k.

Rẻ nhất trong mọi việc còn lại (0 token, chạy vài giây vì bỏ qua LLM), và là thứ **duy nhất** chứng minh được ngưỡng 0.7 đang chết.

### G2. Hiệu chỉnh ngưỡng grounding chưa làm

Ngưỡng 0.7 đặt bằng cảm tính, và `docs/chatbot-e2e-report.md` §5 cho thấy nó không bao giờ kích hoạt. Cần quét 0.60 → 0.95 bước 0.01, in bảng TPR/FPR trên (23 case in_scope) vs (22 case negative), chọn điểm tách.

E5 cosine dồn điểm chặt quanh 0.7–0.8; nếu không tách được bằng ngưỡng tuyệt đối thì dự phòng là **score gap** (`top1 - top5`) hoặc chuẩn hoá theo phân vị.

Ngưỡng còn hardcode ở **ba chỗ độc lập** — `src/chatbot/prompt.py:34`, `src/chatbot/rag_bridge.py:16`, `src/tools/contact_support.py:13`. Lệch giá trị giữa ba chỗ thì prompt nói "không đủ căn cứ" mà guard nói ngược.

### G3. 50/82 chunk chưa từng bị truy vấn

| Tài liệu | Chưa phủ / tổng |
|---|---|
| `feedback_nguoi_dung_tren_Facebook` | **37/47** |
| `20k-ai-handbook-final.md` | 6/17 |
| `thong-tin-tuyen-sinh-...khoa-co-ban.md` | 5/14 |
| `vingroup-tang-toc-dao-tao-20-000-...` | 2/4 |

Gần như toàn bộ corpus cộng đồng chưa được đo. Cần 5–6 case in_scope nhắm chunk Facebook chưa dùng.

### G4. Metric hành vi chưa tồn tại

`eval/run_eval.py` chưa đo: `tool_call_success_rate`, `tool_precision/recall`, `wrong_tool_rate`, `parse_failure_rate`, latency p50/p90, abstention correctness.

Riêng tool success cần `ToolRegistry.call()` (`src/chatbot/types.py:69-76`) đánh dấu được lỗi thay vì nuốt exception thành chuỗi thường.

### G5. Runner còn ba khuyết tật

- `run_eval.py:68` build lại agent **mỗi case** ⇒ mở lại Chroma + nạp model 45 lần.
- Không checkpoint: một timeout giữa chừng mất cả run.
- Chưa có adapter path — eval bám cứng `admission_agent`, khi hợp nhất demo path sẽ phải sửa nhiều chỗ.

### G6. Multi-turn: 0 case

Toàn bộ 45 case đều single-turn, trong khi luồng thật có follow-up. Cần ≥4 case `turns`: giữ ngữ cảnh ở lượt 2, không mất trích nguồn ở lượt 2, lượt sau lạc chủ đề phải chuyển người, `chunk_by_id` tích luỹ qua lượt (`rag_bridge.py:113`) vẫn trích đúng nguồn.

### G7. 12 case `gate` chưa xác nhận

LLM không tất định. Phải chạy 3 lượt; case nào không pass 3/3 thì gỡ cờ và chuyển sang nhóm đo lường.

### G8. Hai bộ e2e chồng nhau

`tests/e2e/test_admission_agent_e2e.py` (9 case, assert nhị phân) và `eval/run_eval.py` (45 case, chấm điểm) — cả hai chạy stack thật, hai golden set song song sẽ lệch nhau.

Gộp: `questions.json` là nguồn duy nhất, `tests/e2e/` parametrize từ nó lọc `gate == true` và tái dùng `check_case()`.

Kèm hai lỗi sửa luôn khi gộp: `tests/e2e/conftest.py:25-26` build agent mỗi case; `tests/e2e/test_admission_agent_e2e.py:18` `skipif` đòi `EMBEDDING_API` — sai sau khi chuyển query embedding sang local, khiến test bị bỏ qua dù stack chạy được.

### G9. Judge đã viết, **chưa hiệu chuẩn**

`eval/judge.py` + `eval/run_ragas.py` xong, 26 test offline xanh, dry-run 23 sample sạch.

**Chưa làm được và không được bỏ qua: mutation check cho chính metric.** Cần một key thật để chạy:
- bơm answer bịa (`"Chương trình kéo dài 30 tuần, học phí 50 triệu"`) vào S02 ⇒ `faithfulness` và `answer_correctness` phải **tụt rõ rệt**
- chép `reference` của N04 sang S02 (đúng dữ kiện, sai câu hỏi) ⇒ `answer_relevancy` tụt trong khi `faithfulness` vẫn cao

Ba metric không đổi ⇒ judge chấm bừa. **Chưa qua bước này thì mọi con số RAGAS đều không đáng tin.**

### G10. Báo cáo chưa tự động

`eval/report.py` gộp 3 nguồn kết quả → `docs/eval-report.md`. Chưa có `spec.md` §7 (quality bar) mà rubric yêu cầu.

---

## 5. Đang chặn

| Vấn đề | Ảnh hưởng |
|---|---|
| `models/intfloat-multilingual-e5-large` chưa tải | không embed được query |
| `src/rag/chroma_db` chưa build | mọi thứ chạm retrieval chặn cứng |
| `.env` chưa đặt `EMBEDDING_QUERY_BACKEND=local` | eval qua API chắc chắn timeout |

Bằng chứng cho dòng thứ ba: `eval/results.json` hiện tại — 1 case, **249.7 s**, đọc timeout sau 4 lần thử. Benchmark `eval/results/embedding-benchmark.md` đo được OpenRouter embedding **1/10** request thành công, local nhanh hơn **122×**.

---

## 6. Thứ tự đề xuất

| # | Việc | Gap | Giờ | Token |
|---|---|---|---|---|
| 0 | Tải model + build Chroma index + đặt `EMBEDDING_QUERY_BACKEND=local` | §5 | 0.5 | 0 |
| 1 | `eval/eval_retrieval.py` — Hit/Recall/MRR/Precision@k | G1 | 2–3 | 0 |
| 2 | Quét ngưỡng + gộp 3 hằng số về `GROUNDING_THRESHOLD` | G2 | 1 | 0 |
| 3 | 5–6 case in_scope phủ chunk Facebook | G3 | 1–1.5 | 0 |
| 4 | Metric tool/latency/abstention + tái dùng agent + checkpoint | G4, G5 | 3–4 | có |
| 5 | **Full run baseline 45 case**, cập nhật 25 `expect: unknown` | — | 1–2 | có |
| 6 | Gộp `tests/e2e` về `questions.json` + cờ `gate` | G8 | 2–3 | có |
| 7 | 4 case multi-turn + hỗ trợ `turns` trong runner | G6 | 1.5–2 | có |
| 8 | Xác nhận `gate` 3 lượt | G7 | 1 | có |
| ✅ | `eval/judge.py` + `eval/run_ragas.py` + 26 test | G9 | — | 0 |
| 9 | Mutation check cho metric RAGAS (bắt buộc trước khi tin số) | G9 | 0.5 | có |
| 10 | `eval/report.py` + chốt quality bar | G10 | 1–2 | có |

Việc (1)–(3) không tốn token. Việc (3) không phụ thuộc gì cả — làm được ngay.

Quality bar đề xuất (**chốt lại sau baseline, không đặt dưới kết quả baseline**): pass rate ≥ 80% (36/45) · Recall@5 ≥ 0.85 · abstention correctness ≥ 90% · tool-call success ≥ 95% · faithfulness ≥ 0.85 · p90 latency ≤ 15 s.

---

## 7. Đã xong

- `eval/questions.json` — 20 → **45 case**, thêm `gold_chunk_ids` / `difficulty` / `gate` / `source`. Gold id đối chiếu 100% với `chunks.json`.
- `eval/ragas_set.json` — **23 sample** kèm `reference` viết tay.
- `eval/run_eval.py:82` — thêm `classify()` xử lý `expect: "unknown"` thành status `baseline`. Trước đó 25 case mới sẽ bị gán nhầm nhãn `regression`.
- `tools_forbidden` cho 6 case — S02/S03/N01/N04 cấm `contact_support`, S07/S08 cấm `attach_source_link`. Trước đó check này dùng **0/45 lần**, nghĩa là "chuyển người cho mọi câu" lách được phần lớn bộ test.
- `eval/judge.py` — 3 metric RAGAS lite tự cài. Input là bản ghi chuỗi thuần (`JudgeSample`), không import agent ⇒ viết và test xong trong lúc bot còn đang sửa.
- `eval/run_ragas.py` — CLI, hai chế độ `--contexts retrieved|gold`, `--dry-run` chạy hết đường ống với 0 token.
- `eval/run_eval.py` — thêm `retrieved_contexts` (text chunk). Trước đó chỉ ghi `source_type`, không đủ để chấm faithfulness.
- `tests/test_judge.py` — 26 test offline. `pytest -q` toàn repo: **123 passed, 3 skipped**.

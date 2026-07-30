# Báo cáo test — package `src/chatbot`

Ngày: 2026-07-30 · Bộ test: [tests/chatbot/](../../tests/chatbot/) · Runner: pytest 9.1.1 / Python 3.13

## Kết quả

```
71 passed, 2 deselected in 5.97s
```

| Nhóm | File | Số test | Kết quả |
|---|---|---|---|
| Render system prompt | `test_prompt.py` | 9 | 9 passed |
| Mock RAG | `test_mock_rag.py` | 7 | 7 passed |
| ToolRegistry | `test_tools.py` | 9 | 9 passed |
| Parser ReAct | `test_react_parse.py` | 21 | 21 passed |
| Vòng lặp ReAct | `test_react_loop.py` | 15 | 15 passed |
| Chatbot | `test_chatbot.py` | 7 | 7 passed |
| Live (gọi model thật) | `test_live.py` | 2 | deselected |

Không test nào chạm mạng. Chạy lại: `uv run pytest -q`.

## Cách làm test xác định

`Chatbot.complete()` là hàm duy nhất gọi API trong đường ReAct. Fixture dựng `Chatbot` với `Settings` giả (`api_key="test-key"`, `base_url="https://example.invalid/v1"`) nên không cần `.env`, rồi thay `bot.complete` bằng `ScriptedLLM` ([conftest.py](../../tests/chatbot/conftest.py)):

```python
class ScriptedLLM:
    """Trả lần lượt từng phản hồi đã kịch bản hoá; ghi lại messages để assert."""
    def __call__(self, messages, stop=None):
        self.calls.append(messages)
        self.stops.append(stop)
        if not self.responses:
            raise AssertionError("ScriptedLLM hết phản hồi — vòng lặp gọi nhiều hơn dự kiến")
        return self.responses.pop(0)
```

Hai tính chất quan trọng:
- **Kịch bản cạn = fail.** Nếu agent gọi model nhiều lần hơn dự kiến, test đỏ ngay — bắt được cả lỗi lặp thừa, không chỉ lỗi sai đáp án.
- **`calls` / `stops` lưu lại toàn bộ input.** Cho phép assert vào *thứ gì được gửi lên* (system prompt có chunk RAG không, prefill có kết thúc bằng `Thought:` không, `stop` sequence đúng chưa) chứ không chỉ output.

## Test case theo nhóm

### Render system prompt — `test_prompt.py`
| Test | Kiểm điều gì |
|---|---|
| `test_khong_tool_thi_bao_chua_co` | Không tool → prompt ghi "Chưa có tool nào" |
| `test_tool_signature_do_vao_prompt` | name/description/signature đều xuất hiện |
| `test_khoi_react_tat_mac_dinh` | `react=False` → không có giao thức ReAct |
| `test_khoi_react_bat_kem_max_steps` | `react=True, max_steps=3` → prompt ghi "tối đa 3 bước" |
| `test_khong_co_chunk_thi_bo_muc_ngu_canh` | Retriever rỗng → bỏ hẳn mục Ngữ cảnh |
| `test_chunk_rag_do_vao_prompt_kem_source_va_score` | `[source]`, text, `score=0.500`, và nguyên tắc trích nguồn cùng bật |
| `test_score_bang_khong_thi_khong_in_score` | Score 0 → không in `score=` |
| `test_context_bo_sung` | Mục "Ngữ cảnh bổ sung" bật/tắt theo tham số |
| `test_render_du_bien_khong_ne_undefined` | `StrictUndefined` — bản đầy đủ render sạch |

### Mock RAG — `test_mock_rag.py`
`NullRetriever` luôn rỗng · `Chunk` frozen · không khớp → rỗng · xếp hạng overlap giảm dần · `k` cắt đúng số lượng · score chuẩn hoá theo số từ truy vấn (`alpha beta` → 1.0, `alpha gamma` → 0.5) · giữ nguyên `source` và `metadata`.

### ToolRegistry — `test_tools.py`
Trọng tâm: **lỗi phải thành chuỗi Observation, không được raise vỡ vòng ReAct**.

| Test | Kiểm điều gì |
|---|---|
| `test_register_get_names_len` | API cơ bản |
| `test_decorator_dang_ky_tool` | `@registry.tool(...)` đăng ký được và trả lại hàm gốc |
| `test_signatures_dung_duoc_cho_prompt` | Bộ ba trường khớp đúng cái prompt cần |
| `test_tool_khong_ton_tai_tra_loi_kem_danh_sach` | Báo lỗi kèm danh sách tool khả dụng (để model tự sửa) |
| `test_sai_kwargs_thanh_chuoi_loi_khong_raise` | `TypeError` → chuỗi, không raise |
| `test_tool_nem_exception_thi_nuot_thanh_chuoi` | `RuntimeError` bên trong tool → chuỗi |
| `test_search_docs_*` (3) | Format `[source] text`, thông báo khi rỗng, `k` truyền xuống retriever |

### Parser ReAct — `test_react_parse.py` (parametrize)
Phủ các biến thể format model thật sinh ra:
- `_parse_args` — 6 dạng hợp lệ: JSON trần, bọc ```` ```json ````, bọc ```` ``` ```` trần, có văn bản thừa hai đầu, có khoảng trắng thừa.
- `_parse_args` lỗi — 3 dạng JSON hỏng → `ValueError` "không phải JSON hợp lệ"; 3 dạng không phải object (mảng/chuỗi/số) → `ValueError` "phải là JSON object".
- `_tool_name` — 7 dạng: trần, backtick, nháy kép, `**bold**`, `search_docs("CP3")`, `search_docs(query='CP3', k=2)`, thừa khoảng trắng → đều ra `search_docs`.
- Regex — `_ACTION_RE` cắt đúng khi phía sau còn `Observation:` hoặc `Thought:`; `_FINAL_RE` bắt đáp án nhiều dòng; `_THOUGHT_RE` chỉ lấy một dòng.

### Vòng lặp ReAct — `test_react_loop.py` (lõi)
| Test | Nhánh | Assert chính |
|---|---|---|
| `test_final_answer_ngay_lap_tuc` | Chốt luôn | 1 step, `observation == "<final>"`, `stopped_early is False` |
| `test_goi_tool_roi_chot` | Đường hạnh phúc | 2 step, action/args đúng, observation chứa `[rubric.md]` |
| `test_registry_nhan_dung_ten_tool_dang_goi_ham` | **Hồi quy** | `Action: search_docs("CP3")` vẫn khớp tool, không sinh lỗi |
| `test_feedback_sai_tham_so_roi_thu_lai` | Vòng phản hồi | Step 1 `TypeError`, step 2 gọi đúng, không `stopped_early` |
| `test_feedback_tool_khong_ton_tai` | Vòng phản hồi | Observation báo tên tool sai, vòng lặp chạy tiếp |
| `test_action_input_hong_khong_lam_vo_vong_lap` | Vòng phản hồi | JSON hỏng → Observation lỗi, vẫn chốt được đáp án |
| `test_repeat_guard_canh_bao_khi_goi_trung` | Chống lặp | Lần 1 không cảnh báo, lần 2 có `[Cảnh báo]` |
| `test_doi_tham_so_thi_khong_canh_bao` | Chống lặp | Đổi query → không cảnh báo nhầm |
| `test_het_max_steps_thi_ep_chot` | Chạm trần | `stopped_early is True`, đúng 3 lần gọi model (2 vòng + 1 ép chốt) |
| `test_khong_action_khong_final_thi_lay_ca_output` | Dự phòng | Văn xuôi thuần → trả nguyên văn |
| `test_prefill_thought_va_stop_sequence` | Ép format | `raw` bắt đầu `Thought:`; message cuối role `assistant` kết thúc `"Thought:"`; `stop` đúng |
| `test_scratchpad_tich_luy_observation` | Bộ nhớ vòng | Vòng 2 nhìn thấy Observation vòng 1 |
| `test_rag_pre_retrieve_vao_system_prompt` | **RAG** | `result.retrieved` khác rỗng và chunk nằm trong system prompt |
| `test_khong_co_rag_thi_retrieved_rong` | RAG | `NullRetriever` → `retrieved == []` |
| `test_tool_signature_tu_registry_vao_prompt` | Nối tầng | Signature từ registry đi tới prompt |
| `test_history_giu_qua_hai_luot_va_reset` | Hội thoại | Lượt 2 thấy cặp user/assistant lượt 1; `reset()` xoá sạch |

### Chatbot — `test_chatbot.py`
History ghi đúng cặp user/assistant · `_messages()` xếp `system, *history, user` · `retrieve()` set `last_retrieved` và tôn trọng `top_k` · `reset()` xoá cả history lẫn `last_retrieved` · `system_prompt()` bật/tắt khối ReAct · `stream()` yield đúng token và gộp vào history (dùng client giả trả delta).

### Live — `test_live.py` (opt-in)
Mặc định bị loại bởi `addopts = "-m 'not live'"` trong [pyproject.toml](../../pyproject.toml). Chạy: `uv run pytest -m live`. Tự skip nếu thiếu `OPENAI_API`.

- `test_agent_lay_duoc_du_kien_chi_co_trong_tai_lieu` — tài liệu chứa dữ kiện bịa `ZX-7741` mà model không thể biết sẵn, nên đáp án đúng chứng minh agent thật sự đi qua RAG/tool.
- `test_khong_bia_khi_ngoai_pham_vi_tai_lieu` — hỏi thủ đô Pháp: đáp án **không** được chứa "paris", phải nói "không có trong tài liệu".

## Kiểm chứng suite có thật sự bắt lỗi (mutation check)

Test xanh chưa chứng minh test hữu ích. Đã cố tình phá code rồi chạy lại:

| Phá gì | Kỳ vọng | Kết quả thật |
|---|---|---|
| Bỏ chuẩn hoá trong `_tool_name()` | đỏ | 3 failed (2 parse + 1 loop) |
| Vô hiệu khối repeat-guard (`if key in seen` → `if False`) | đỏ | 1 failed (`test_repeat_guard_canh_bao_khi_goi_trung`) |
| Khôi phục nguyên trạng | xanh | 71 passed |

Cả hai cơ chế đều có test canh gác thật, không phải test trang trí.

## Khoảng trống chưa phủ

- **`__main__.py` (CLI) chưa có test.** Vòng lặp `input()`, cờ `--trace`, lệnh `reset`/`exit` đều chưa được kiểm. Chỉ mới chạy tay `--help`.
- **`Settings.from_env()` chưa có test.** Thiếu case: thiếu `OPENAI_API` → `RuntimeError`; giá trị mặc định khi thiếu biến tuỳ chọn.
- **Chưa test lỗi mạng.** API timeout / 429 / 500 hiện chưa có nhánh xử lý trong code (xem mục "Không có timeout / retry" trong [chatbot-code-review.md](chatbot-code-review.md)), nên chưa có gì để test.
- **Chưa đo chất lượng đáp án.** Bộ test hiện kiểm *cơ chế* (loop, parser, prompt) chứ không kiểm *độ đúng của câu trả lời*. Phần đó cần golden set + rubric, thuộc phạm vi CP3/CP5 chứ không phải unit test.

## Lệnh

```bash
uv run pytest -q                    # 71 test offline
uv run pytest -v                    # kèm tên từng test
uv run pytest -m live               # 2 test gọi model thật, cần OPENAI_API
uv run pytest tests/chatbot/test_react_loop.py -q   # riêng vòng ReAct
```

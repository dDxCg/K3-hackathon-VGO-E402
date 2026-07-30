# Thiết kế Agent tư vấn tuyển sinh — 2 tools (Phase hiện tại)

> Phạm vi tài liệu này: chỉ thiết kế **agent + 2 tools**, chưa đi vào implementation. Đối tượng agent phục vụ: **người đang tìm hiểu chương trình AI Thực Chiến, chưa nộp hồ sơ / chưa đăng ký**. Kênh: chat popup nhỏ nhúng trên trang thông tin tuyển sinh.
>
> Nguồn dữ liệu dùng: `data/Data_FaceBook_ckean/` (feedback cộng đồng Facebook, đã gộp) + `data/web/_clean/` (3 trang chính thức VinUni/Vingroup). **Không dùng `data/vlearn-pack/`** — đó là data mẫu của track khác, không liên quan tuyển sinh.

---

## 1. Vai trò của agent trong luồng chat

Agent nhận câu hỏi của khách → retrieve trong RAG DB (đã build từ 2 nguồn trên) → ra quyết định theo đúng nguyên tắc sống của đề tài: **đưa dữ kiện, không kết luận thay**.

```
Câu hỏi user
   │
   ▼
Retrieval (RAG) trên KB đã gộp chunk
   │
   ├── Có chunk khớp, câu hỏi trong phạm vi Phase 1 (§3)
   │        → trả lời bằng dữ kiện trong chunk + gọi Tool 2 (attach_source_link)
   │
   └── Không có chunk khớp đủ tin cậy, HOẶC câu hỏi thuộc danh sách ngoài phạm vi
            → gọi Tool 1 (contact_support) — không đoán, không tự trả lời từ kiến thức nền model
```

Đây chính là mức **Conditional** (02-guide §2.3): đa số case lành do agent tự trả lời có căn cứ; số ít case mơ hồ/ngoài phạm vi/không có nguồn → chuyển người, không tự quyết.

---

## 2. Tool 1 — `contact_support`

### Mục đích

Chuyển câu hỏi cho nhân viên tuyển sinh khi agent **không có căn cứ để trả lời** hoặc câu hỏi **ngoài phạm vi/thẩm quyền** của agent. Đây là hành vi bắt buộc theo HAX **G10 — thu hẹp phạm vi khi nghi ngờ**, không phải fallback phụ.

### Điều kiện trigger (agent tự quyết định gọi tool, không hỏi lại user trước)

| # | Điều kiện                                                                                                                                                                                                                                                                     | Lớp chỗ khó liên quan       |
| - | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| 1 | Retrieval không trả về chunk nào có similarity score ≥**0.7** (ngưỡng đã chốt) — coi là không có căn cứ                                                                                                                                                   | ① Nguồn sự thật             |
| 2 | Câu hỏi thuộc nhóm**"Phase 1 KHÔNG làm"** đã chốt ở brief: tra trạng thái hồ sơ/điểm/kết quả cá nhân (kể cả khi user đưa email/mã hồ sơ), xin lời khuyên "có nên nộp không / có đậu không", cam kết đầu ra hay thu nhập sau khoá | ③ Ngoài phạm vi/thẩm quyền |
| 3 | Hai chunk mâu thuẫn nhau về cùng một dữ kiện (vd. lịch học lệch giữa nguồn chính thức và cộng đồng) mà agent không có căn cứ để chọn bên nào                                                                                                         | ④ Đặc thù domain            |
| 4 | Câu hỏi đòi thông tin cá nhân/nhạy cảm không thuộc phạm vi tuyển sinh công khai                                                                                                                                                                                    | ③ Ngoài phạm vi/thẩm quyền |

Với điều kiện 3, tool vẫn có thể được gọi kèm cả hai dữ kiện trái nhau hiển thị cho user (không tự chọn giúp), tuỳ theo mức độ nghiêm trọng — xem `output.disclose_conflicting_facts`.

### Input schema (agent điền khi gọi tool)

```json
{
  "name": "contact_support",
  "description": "Chuyển câu hỏi của người dùng cho nhân viên tuyển sinh khi agent không có căn cứ trong tài liệu chính thức/cộng đồng để trả lời, hoặc câu hỏi ngoài phạm vi agent được phép trả lời (vd. tra hồ sơ cá nhân, xin lời khuyên nên nộp hay không).",
  "input_schema": {
    "type": "object",
    "properties": {
      "reason": {
        "type": "string",
        "enum": ["no_grounding", "out_of_scope", "conflicting_sources", "personal_data_request"],
        "description": "Vì sao agent không tự trả lời được"
      },
      "user_question": {
        "type": "string",
        "description": "Câu hỏi nguyên văn của user, dùng để soạn sẵn câu hỏi chuyển cho nhân viên"
      },
      "partial_context": {
        "type": "string",
        "description": "Optional — dữ kiện liên quan gần nhất agent tìm được dù chưa đủ căn cứ trả lời trực tiếp (vd. hai chunk mâu thuẫn), để nhân viên đỡ phải tra lại từ đầu"
      }
    },
    "required": ["reason", "user_question"]
  }
}
```

### Output / hành vi hiển thị cho user

- Một câu nói rõ **chưa đủ căn cứ** (không xin lỗi vòng vo, không giả vờ biết).
- Kênh liên hệ chính thức lấy từ `data/web/_clean/...khoa-co-ban.md` (nguồn duy nhất có thông tin liên hệ tại thời điểm viết tài liệu này):
  - Hotline: `0979.489.846`
  - Liên hệ tuyển sinh: Ms. Phương Thảo — `0388.339.478`
  - Email: `AIthucchien@vinuni.edu.vn`
- Một câu hỏi soạn sẵn để user copy gửi cho nhân viên (rút gọn từ `user_question`), theo đúng tinh thần G9 — sửa dễ dàng: user có thể chỉnh câu này trước khi gửi.
- Nếu `reason = conflicting_sources`: hiển thị cả hai dữ kiện kèm tem nguồn/ngày trước khi đưa link liên hệ — không tự chọn giúp user (nguyên tắc đã chốt ở brief).

### Việc cần làm để tool này hoạt động đúng

- Chốt **ngưỡng độ tin cậy retrieval** cụ thể (số) trước CP4 — hiện chưa có trong repo, cần chốt cùng RAG.
- Danh sách "ngoài phạm vi" ở trên cần được classifier/prompt của agent nhận diện được — nên đưa vào system prompt dưới dạng danh sách cấm cụ thể, không chỉ mô tả chung chung.

---

## 3. Tool 2 — `attach_source_link`

### Mục đích

Sau khi agent trả lời bằng dữ kiện từ một hoặc nhiều chunk, đính kèm **link về nguồn gốc** của chunk đó, dựa trên nhãn nguồn (label) đã gắn từ lúc gộp chunk — để user tự đối chiếu, đúng nguyên tắc "đưa dữ kiện, không kết luận thay" và HAX **G11 — giải thích vì sao**.

### Tiền đề: mỗi chunk phải mang metadata nguồn khi ingest vào RAG

Hiện tại 2 nguồn dữ liệu có cách gắn nguồn khác nhau:

| Nguồn dữ liệu                                    | File                                                                           | Có source label sẵn?                                                                                                                                                                                                | Link đính kèm                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Facebook (cộng đồng, đã gộp câu hỏi trùng) | `data/Data_FaceBook_ckean/ai_thuc_chien_facebook_feedback_clean.md`          | **Chưa** — file hiện không có dòng source. Cần bổ sung 1 dòng comment `<!-- source: https://www.facebook.com/groups/2125430681651241 -->` ở đầu file khi ingest, tương tự format các file web | `https://www.facebook.com/groups/2125430681651241` (cố định — cả file chỉ có 1 nguồn)            |
| Trang tuyển sinh khoá cơ bản                    | `data/web/_clean/thong-tin-tuyen-sinh-...-khoa-co-ban.md`                    | Có — dòng 1:`<!-- source: URL -->`                                                                                                                                                                               | `https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/` |
| 20K AI Handbook (PDF)                               | `data/web/_clean/20k-ai-handbook-final.md`                                   | Có                                                                                                                                                                                                                   | `https://vinuni.edu.vn/wp-content/uploads/2025/04/20K-AI-Handbook_final.pdf`                             |
| Bài Vingroup tăng tốc đào tạo                 | `data/web/_clean/vingroup-tang-toc-dao-tao-20-000-nhan-tai-ai-thuc-chien.md` | Có                                                                                                                                                                                                                   | `https://vinuni.edu.vn/vi/vingroup-tang-toc-dao-tao-20-000-nhan-tai-ai-thuc-chien/`                      |

**Quy tắc ingest:** khi chunking, mỗi chunk kế thừa `source_url` + `source_type` (`official_web` | `community_facebook`) từ file gốc — đọc từ dòng comment `<!-- source: ... -->` đầu file (web), hoặc gán cứng cho toàn bộ file Facebook. Không suy ra nguồn ở tầng model — phải là metadata cứng từ ingestion, tránh agent tự bịa hoặc gắn nhầm link.

### Input schema

```json
{
  "name": "attach_source_link",
  "description": "Lấy link nguồn gốc của (các) chunk đã dùng để trả lời, dựa trên nhãn source_type đã gắn khi ingest. Gọi sau khi đã chọn được chunk trả lời, trước khi trả kết quả cuối cho user.",
  "input_schema": {
    "type": "object",
    "properties": {
      "chunk_ids": {
        "type": "array",
        "items": { "type": "string" },
        "description": "ID của các chunk đã dùng để tạo câu trả lời"
      }
    },
    "required": ["chunk_ids"]
  }
}
```

### Output

Danh sách `{chunk_id, source_type, source_url, label_hien_thi}`, ví dụ:

```json
[
  {
    "chunk_id": "web_khoa-co-ban_003",
    "source_type": "official_web",
    "source_url": "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/",
    "label_hien_thi": "Thông tin tuyển sinh chính thức — VinUni"
  },
  {
    "chunk_id": "fb_feedback_012",
    "source_type": "community_facebook",
    "source_url": "https://www.facebook.com/groups/2125430681651241",
    "label_hien_thi": "Chia sẻ cộng đồng — nhóm Facebook (không phải nguồn chính thức)"
  }
]
```

### Hiển thị cho user

- Mỗi dữ kiện trong câu trả lời đi kèm mã trích dẫn + link, giống cách VLearn tutor cite `[trang N]` (01-de-bai.md).
- Nếu chunk đến từ Facebook: **luôn gắn nhãn "chia sẻ cộng đồng, không phải nguồn chính thức"** cạnh link — vì `data/Data_FaceBook_ckean/...` đã tự nêu rõ nguyên tắc "khi có khác biệt, ưu tiên thông báo tuyển sinh/email/sổ tay/nội dung mới nhất từ VinUni". Đây là ranh giới bắt buộc để tránh user hiểu nhầm lời đồn là thông tin chính thức (lớp ④ — đặc thù domain: sai lịch/địa điểm là ứng viên chịu hậu quả trực tiếp).
- Nếu câu trả lời tổng hợp từ nhiều chunk khác `source_type`, hiển thị tất cả link, không gộp lại thành một.

---

## 4. Đã chốt (2026-07-30)

1. ✅ Ngưỡng retrieval confidence cho `no_grounding`: **similarity score < 0.7 → coi là không có căn cứ**.
2. ✅ Danh sách "ngoài phạm vi" giữ nguyên như bảng ở §2 (không bổ sung thêm case ngoài brief).
3. ✅ Thông tin liên hệ tuyển sinh (hotline/Ms. Phương Thảo/email) xác nhận còn đúng, dùng thẳng cho Tool 1.
4. ✅ Đã bổ sung dòng `<!-- source: https://www.facebook.com/groups/2125430681651241 -->` vào đầu file Facebook clean.

→ Code skeleton triển khai theo thiết kế này nằm ở `src/tools/contact_support.py` và `src/tools/attach_source_link.py`.

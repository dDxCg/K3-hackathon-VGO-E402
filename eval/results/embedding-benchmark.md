# Benchmark embedding — multilingual-e5-large

Ngày chạy: 2026-07-30T16:59:42+07:00 · Top-k: 5

Phạm vi: đo query embedding và Chroma retrieval; **không** đo thời gian sinh câu trả lời của chat LLM.

## Tổng hợp

| Backend | Model embedding | Model load (s) | Embedding mean thành công (s) | Median (s) | P95 (s) | Mean attempt gồm lỗi (s) | Total retrieval mean (s) | Thành công |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| local | `intfloat/multilingual-e5-large` | 9.602 | 0.203 | 0.186 | 0.316 | 0.203 | 0.205 | 10/10 |
| openrouter | `intfloat/multilingual-e5-large` | N/A | 24.772 | 24.772 | 24.772 | 56.477 | 24.774 | 1/10 |

## Chi tiết 10 câu hỏi

| # | Câu hỏi | Local embedding (s) | OpenRouter embedding (s) | Local total (s) | OpenRouter total (s) | Top chunk trùng? |
|---:|---|---:|---:|---:|---:|:---:|
| 1 | Chương trình học trong bao lâu? | 0.316 | 24.772 | 0.319 | 24.774 | ✓ |
| 2 | Lịch học hằng ngày như thế nào? | 0.251 | TIMEOUT (60.0s) | 0.253 | TIMEOUT (60.0s) | — |
| 3 | Địa điểm học ở đâu? | 0.165 | TIMEOUT (60.0s) | 0.166 | TIMEOUT (60.0s) | — |
| 4 | Điều kiện dự tuyển là gì? | 0.217 | TIMEOUT (60.0s) | 0.219 | TIMEOUT (60.0s) | — |
| 5 | Hồ sơ đăng ký gồm những gì? | 0.188 | TIMEOUT (60.0s) | 0.190 | TIMEOUT (60.0s) | — |
| 6 | Bài đánh giá năng lực kiểm tra nội dung gì? | 0.184 | TIMEOUT (60.0s) | 0.185 | TIMEOUT (60.0s) | — |
| 7 | Chương trình có những track nào? | 0.157 | TIMEOUT (60.0s) | 0.159 | TIMEOUT (60.0s) | — |
| 8 | Có thể vừa học vừa đi làm không? | 0.180 | TIMEOUT (60.0s) | 0.182 | TIMEOUT (60.0s) | — |
| 9 | Hạn nộp hồ sơ khóa đang tuyển là khi nào? | 0.179 | TIMEOUT (60.0s) | 0.181 | TIMEOUT (60.0s) | — |
| 10 | Học viên có được hỗ trợ học phí không? | 0.192 | TIMEOUT (60.0s) | 0.194 | TIMEOUT (60.0s) | — |

## Kết luận nhanh

- Local: 10/10 thành công; embedding trung bình 0.203 giây/câu sau warmup.
- OpenRouter: 1/10 thành công; 9 lỗi/timeout.
- Trên request OpenRouter thành công, local nhanh hơn khoảng **122.1×** ở bước embedding.

## Ghi chú đo

- `model_load`: chi phí nạp weights local một lần khi app khởi động; không cộng vào từng query.
- `embedding`: chỉ thời gian biến một câu hỏi thành vector 1.024 chiều.
- `Chroma query`: chỉ thời gian tìm top-k bằng vector đã có.
- `total retrieval`: embedding + Chroma query; chưa gồm chat LLM.
- OpenRouter dùng cùng model `intfloat/multilingual-e5-large`; chênh lệch chủ yếu là network/provider.

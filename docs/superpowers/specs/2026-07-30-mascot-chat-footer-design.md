# Thiết kế tinh chỉnh mascot, chatbot, footer và điều hướng

## Mục tiêu

Cập nhật `prototype.html` để mascot không che nội dung, panel chatbot gọn hơn, footer bỏ sọc chéo và dùng ảnh nền đã crop, đồng thời dịch nhóm điều hướng desktop sang phải. Giữ nguyên nội dung và hành vi hội thoại hiện có.

## Phạm vi

- Tạo asset `footer_mb_cropped.webp` từ `footer_mb.webp` trước khi thay đổi giao diện.
- Chỉnh kích thước, vị trí và chuyển động của mascot chatbot.
- Bỏ bong bóng “Chào bạn” và giữ badge `1` cho đến lần mở chatbot đầu tiên.
- Ẩn mascot khi panel chatbot mở.
- Thu nhỏ panel chatbot trên desktop.
- Thay nền và bỏ sọc chéo ở footer, giữ nguyên nội dung footer.
- Dịch nhóm menu chính desktop sang phải `1cm`.

Không thay đổi dữ liệu hội thoại, nội dung footer, liên kết, social, cấu trúc thông tin trang hoặc luồng JavaScript của chatbot ngoài trạng thái hiển thị đã nêu.

## Lời mời và badge chưa đọc

- Giữ bong bóng lời mời dài xuất hiện ban đầu cùng nút đóng `×`.
- Xóa hoàn toàn bong bóng ngắn “Chào bạn” khỏi HTML, CSS và JavaScript.
- Khi người dùng nhấn `×` trên lời mời dài, chỉ ẩn lời mời; không mở panel và không đánh dấu chatbot là đã mở.
- Sau khi đóng lời mời dài, đưa focus về nút mascot để thao tác bàn phím vẫn liên tục.
- Badge đỏ `1` tiếp tục hiển thị vì người dùng chưa mở chatbot.
- Badge chỉ biến mất khi người dùng thực sự mở panel chatbot lần đầu.
- Sau khi panel đã từng được mở, đóng panel không làm badge `1` xuất hiện lại trong phiên hiện tại.

## Thứ tự triển khai

1. Crop asset và kiểm tra ảnh đầu ra.
2. Chỉ sau khi asset hợp lệ mới sửa `prototype.html`.
3. Chỉnh mascot và panel chatbot.
4. Chỉnh footer và điều hướng.
5. Kiểm tra responsive, trạng thái mở/đóng và khả năng truy cập.

## Asset footer

- Nguồn: `../ui-vinuni/wp-content/themes/assets/images/footer_mb.webp`.
- Không ghi đè file nguồn.
- Crop bỏ `227px` ở mép trên, tương đương xấp xỉ `6cm` theo chuẩn web `96dpi`.
- Kích thước nguồn là `428 × 432px`; ảnh kết quả dự kiến là `428 × 205px`.
- Lưu cạnh file nguồn với tên `footer_mb_cropped.webp`.
- Giữ nguyên phần ảnh còn lại, không tái tạo, thêm chi tiết, đổi màu hoặc làm biến dạng nội dung.
- Xác nhận ảnh đầu ra đọc được, đúng kích thước và không hỏng trước khi tham chiếu từ web.

## Mascot

- Giảm đúng `0.3cm` so với kích thước hiện tại:
  - Desktop: từ `calc(70px + 0.5cm)` thành `calc(70px + 0.2cm)`.
  - Mobile: từ `calc(64px + 0.5cm)` thành `calc(64px + 0.2cm)`.
- Đặt cách mép phải `16px`.
- Giữ vị trí dọc hiện có, trừ khi cần hiệu chỉnh tối thiểu để khớp panel mới.
- Tạo chuyển động lắc nhẹ khoảng `-3deg` đến `3deg`, chu kỳ khoảng 3 giây, tâm xoay gần phần chân.
- Hover hoặc focus tạm dừng chuyển động để trạng thái tương tác ổn định.
- Tắt animation khi `prefers-reduced-motion: reduce`.

## Trạng thái chatbot mở

- Khi nút có trạng thái mở, ẩn toàn bộ nút mascot bằng chuyển tiếp opacity/visibility ngắn.
- Mascot ẩn phải không nhận con trỏ và không che nội dung.
- Chỉ panel chatbot còn hiển thị; nút đóng bên trong panel tiếp tục là cách đóng chatbot.
- Khi đóng panel, mascot xuất hiện lại và tiếp tục chuyển động nếu người dùng không bật giảm chuyển động.

## Kích thước panel

- Desktop: `340 × 460px`.
- Cách mép phải và mép dưới `16px`.
- Giới hạn chiều cao theo viewport để panel không vượt màn hình thấp.
- Mobile giữ chế độ toàn màn hình để bàn phím, lịch sử tin nhắn và ô nhập không bị chật.
- Nội dung dài tiếp tục cuộn trong vùng tin nhắn; header và composer không bị co mất.

## Footer

- Dùng `footer_mb_cropped.webp` làm ảnh nền.
- Dùng `background-size: cover` và vị trí nền phù hợp để phần công trình còn lại hiện rõ.
- Phủ lớp xanh đậm bán trong suốt để chữ trắng duy trì độ tương phản.
- Xóa hoàn toàn pseudo-element hoặc `repeating-linear-gradient` tạo sọc chéo.
- Giữ mảng xanh đặc cắt chéo ở khu vực logo bên trái.
- Giữ nguyên nội dung, liên kết, social và bố cục responsive hiện có: nhiều cột trên desktop, hai cột trên tablet, một cột trên mobile.
- Không thêm asset hoặc nội dung footer mới ngoài ảnh crop.

## Điều hướng desktop

- Dịch nhóm “Giới thiệu / Đào tạo / Nghiên cứu / Tuyển sinh / Tin tức” sang phải đúng `1cm`.
- Chỉ áp dụng ở breakpoint desktop nơi menu nằm trên một hàng.
- Không áp dụng trên tablet/mobile để tránh tràn hoặc thu hẹp vùng bấm.
- Không thay đổi trạng thái active, underline, thứ tự hoặc liên kết.

## Phương án kỹ thuật

Dùng một khối CSS override tập trung ở cuối stylesheet nhúng trong `prototype.html`. Cách này giữ nguyên CSS gốc và JavaScript hiện tại, giảm nguy cơ ảnh hưởng các breakpoint khác. Chỉ chỉnh JavaScript nếu trạng thái `.is-open` hiện tại không đủ để biểu diễn trạng thái ẩn mascot; ưu tiên giải pháp CSS dựa trên class sẵn có.

## Kiểm tra chấp nhận

1. `footer_mb_cropped.webp` tồn tại, đọc được và có kích thước `428 × 205px`.
2. Mascot nhỏ hơn đúng `0.3cm`, cách mép phải `16px` và không che menu/nội dung.
3. Mascot lắc nhẹ khi đóng, dừng khi hover/focus và không chuyển động trong reduced-motion.
4. Mở chatbot làm mascot biến mất hoàn toàn; đóng chatbot làm mascot xuất hiện lại.
5. Bong bóng “Chào bạn” không còn trong DOM hoặc luồng tương tác.
6. Đóng lời mời ban đầu không mở chatbot và badge `1` vẫn hiển thị; mở panel lần đầu mới ẩn badge.
7. Panel desktop đo `340 × 460px`, không vượt viewport và vẫn cuộn tin nhắn đúng.
8. Mobile vẫn dùng panel toàn màn hình.
9. Footer dùng ảnh crop, không còn sọc chéo và toàn bộ nội dung cũ vẫn hiển thị.
10. Menu desktop dịch phải `1cm`; tablet/mobile không bị dịch và không tràn.
11. Không phát sinh lỗi HTML/CSS/JavaScript mới trong kiểm tra cục bộ.

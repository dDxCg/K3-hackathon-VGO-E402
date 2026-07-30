# Thiết kế hiệu chỉnh điều hướng, chatbot, footer và responsive

## Mục tiêu

Hiệu chỉnh `prototype.html` theo ảnh phản hồi ngày 31/07/2026: đặt gạch active ngay dưới chữ “Tuyển sinh”, dịch hộp lời chào chatbot lên cao và sang phải, giữ nội dung liên hệ footer trong vùng xanh bên trái, làm chuyển động mascot rõ nhưng nhẹ, và bảo đảm giao diện ổn định từ viewport 360px đến 1920px.

## Phạm vi

- Chỉ sửa `prototype.html`.
- Giữ nguyên nội dung bài viết, dữ liệu chatbot, luồng gửi/nhận tin nhắn và các asset hiện có.
- Không thay đổi vị trí panel chat khi đã mở; chỉ thay đổi hộp lời chào `.vc-teaser` theo lựa chọn A đã được duyệt.
- Không refactor toàn bộ stylesheet. Các hiệu chỉnh được gom trong một lớp CSS cuối file để có độ ưu tiên rõ ràng và không làm mất các chỉnh sửa đang có của người dùng.
- Chỉ thay đổi HTML tối thiểu nếu cần thêm class định danh cho cột liên hệ footer.

## Phương án đã chọn

Dùng một lớp CSS hiệu chỉnh tập trung ở cuối stylesheet, kết hợp class riêng cho cột liên hệ footer. Phương án này ít rủi ro hơn việc viết lại header/footer/chatbot, đồng thời dễ xác minh theo breakpoint hơn việc vá rời rạc nhiều vị trí.

## Thiết kế chi tiết

### Gạch active của điều hướng

- Giữ pseudo-element `::after` và màu đỏ thương hiệu hiện tại.
- Neo hai mép gạch theo vùng chữ sau khi loại trừ padding ngang của link.
- Đặt gạch sát dưới dòng chữ với khoảng hở thị giác khoảng 2–3px, căn giữa ổn định ở desktop rộng và desktop gọn.
- Trạng thái hover dùng cùng hình học với trạng thái `aria-current="page"`.
- Menu tablet/mobile tiếp tục không hiển thị gạch active trong panel trượt.

### Hộp lời chào chatbot

- Chỉ dịch `.vc-teaser`; không dịch `.vc-panel`.
- Trên desktop, đưa hộp lên thêm khoảng 24–32px và sang phải gần mascot hơn, vẫn giữ khoảng hở để không đè lên mascot hoặc badge.
- Trên tablet/mobile, neo hộp theo hai mép an toàn của viewport, chừa chỗ cho mascot và không che nội dung chính quá mức.
- Hộp luôn nằm trong viewport ở chiều rộng nhỏ nhất 360px; nút đóng vẫn có vùng bấm nguyên vẹn.

### Footer liên hệ

- Thêm class định danh cho cột chứa “Trường Đại học VinUni”.
- Căn cột này sang trái nhẹ trên desktop, giới hạn chiều rộng nội dung và thêm khoảng đệm bên phải để địa chỉ, email, hotline không cắt qua cạnh chéo của mảng xanh.
- Email được phép ngắt an toàn khi viewport hẹp; địa chỉ giữ điểm xuống dòng sau “Ocean Park,” như nội dung hiện tại.
- Trên tablet hai cột và mobile một cột, bỏ mọi phép dịch ngang để tránh tràn viewport.
- Giữ nguyên nội dung và liên kết:
  - Trường Đại học VinUni
  - Khu đô thị Vinhomes Ocean Park, xã Gia Lâm, Hà Nội
  - AIthucchien@vinuni.edu.vn
  - Hotline: 0979.489.846

### Chuyển động mascot

- Dùng animation CSS trên `.vc-fab-mascot`, tâm xoay ở gần chân.
- Chuyển động kết hợp xoay nhẹ hai phía và nhún dọc rất nhỏ để cảm giác lắc lư dễ nhận biết nhưng không gây xao nhãng.
- Chu kỳ khoảng 2.8–3.2 giây, easing mềm và lặp vô hạn.
- Hover/focus tạm dừng animation; `prefers-reduced-motion: reduce` tắt hoàn toàn animation.
- Không thay đổi logic ẩn mascot khi panel chat mở.

### Responsive và breakpoint

Do dải thiết bị yêu cầu có phần giao nhau giữa desktop `1024–1920px` và tablet `601–1280px`, thiết kế dùng hành vi theo khả năng chứa nội dung:

- `1281–1920px`: desktop rộng, container đầy đủ và menu ngang.
- `1024–1280px`: desktop gọn/tablet ngang, vẫn dùng menu ngang nhưng giảm khoảng cách và cỡ chữ khi cần.
- `601–1023px`: tablet, dùng menu thu gọn và nội dung một cột.
- `360–600px`: mobile; tối ưu riêng vùng phổ biến `360–414px` cho footer, teaser và panel chat.

Trang không có chế độ thiết kế riêng dưới 360px hoặc trên 1920px, nhưng vẫn dùng giới hạn chiều rộng và chống tràn ngang để suy giảm an toàn.

## Luồng và phụ thuộc

Các thay đổi chỉ tác động đến trình bày CSS. JavaScript tiếp tục điều khiển class `is-open`, `is-in`, thuộc tính `hidden`, badge và các hành vi chat hiện tại. Không có dữ liệu mới, API mới hoặc luồng lỗi mới.

## Khả năng truy cập

- Giữ nguyên `aria-current`, `aria-expanded`, nhãn nút và thứ tự focus hiện tại.
- Không giảm vùng bấm của nút đóng teaser hoặc mascot.
- Tôn trọng `prefers-reduced-motion`.
- Không tạo nội dung bị che hoặc tràn ngang ở mức zoom trình duyệt thông thường.

## Kiểm tra chấp nhận

1. Ở 1024, 1280, 1366 và 1920px, gạch đỏ nằm ngay dưới và căn giữa theo chữ “Tuyển sinh”.
2. Ở desktop, hộp lời chào cao hơn vị trí cũ 24–32px và gần mascot hơn nhưng không chồng lên mascot/badge.
3. Mở chatbot không làm thay đổi vị trí panel đã có; đóng panel trả về mascot và teaser đúng trạng thái.
4. Nội dung liên hệ footer không vượt qua cạnh chéo của mảng xanh ở desktop và không tràn ngang ở tablet/mobile.
5. Footer giữ đúng nội dung, email và số hotline hiện tại.
6. Mascot lắc/nhún nhẹ, dừng khi hover/focus và đứng yên trong reduced-motion.
7. Không có thanh cuộn ngang tại 360, 375, 390, 414, 601, 768, 1024, 1280, 1366 và 1920px.
8. Menu thu gọn hoạt động ở 601–1023px; menu ngang hoạt động từ 1024px.
9. Panel chat toàn màn hình ở mobile nhỏ theo hành vi hiện tại và không vượt viewport.
10. HTML/CSS/JavaScript không phát sinh lỗi cú pháp mới; các chỉnh sửa không liên quan đang có trong `prototype.html` được giữ nguyên.

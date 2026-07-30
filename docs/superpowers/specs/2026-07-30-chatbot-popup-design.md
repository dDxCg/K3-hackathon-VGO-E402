# Thiết kế cập nhật chatbot popup

## Mục tiêu

Cập nhật widget chatbot trong `ui/prototype.html` để lời mời chat xuất hiện đúng một lần theo luồng rõ ràng, không lưu hội thoại vào trình duyệt, cải thiện khả năng đọc câu trả lời dài và làm mascot nổi bật hơn.

## Phạm vi

- Chỉ sửa widget chatbot trong `ui/prototype.html`.
- Không thay đổi nội dung trang, cơ sở tri thức hay logic trả lời hiện có.
- Hội thoại chỉ tồn tại trong bộ nhớ của trang đang mở. Tải lại hoặc đóng trang sẽ bắt đầu một phiên mới.

## Luồng lời mời chat

Widget có hai bong bóng lời mời độc lập:

1. Khi trang tải xong, chỉ bong bóng dài xuất hiện với nội dung: “Chào bạn! Bạn cần tư vấn về chương trình AI thực chiến?”.
2. Nhấn nút đóng của bong bóng dài sẽ ẩn bong bóng này và hiện bong bóng ngắn “Chào bạn”.
3. Nhấn bong bóng dài, bong bóng ngắn hoặc mascot sẽ mở khung chat và ẩn cả hai bong bóng.
4. Sau khi chat đã được mở trong phiên trang hiện tại, đóng hoặc thu nhỏ chat không làm bong bóng nào xuất hiện lại.
5. Hover, focus và touch trên mascot không làm lời mời tự bật lại.
6. Tải lại trang sẽ khởi tạo lại luồng từ bong bóng dài vì trạng thái không được lưu trong trình duyệt.

## Bộ nhớ hội thoại

- Loại bỏ đọc và ghi `sessionStorage` cho hội thoại và trạng thái lời mời.
- Tiếp tục giữ `Memory` trong JavaScript để chatbot hiểu ngữ cảnh trong phiên trang hiện tại.
- Chức năng xem lịch sử, tải bản ghi và xóa hội thoại vẫn hoạt động với dữ liệu của phiên hiện tại.
- Không phục hồi tin nhắn sau khi tải lại trang.

## Mascot

- Bỏ nền màu, viền trắng, khung tròn, bo tròn và phần cắt nội dung quanh mascot.
- Tăng đồng thời chiều rộng và chiều cao thêm `0.5cm` so với kích thước hiện tại:
  - Desktop: từ `70px` lên `calc(70px + 0.5cm)`.
  - Mobile: từ `64px` lên `calc(64px + 0.5cm)`.
- Giữ vùng bấm dễ thao tác, trạng thái focus bàn phím và hiệu ứng hover nhẹ không làm biến dạng mascot.
- Điều chỉnh vị trí panel và bong bóng để không chồng lên mascot lớn hơn.

## Chế độ phóng to câu trả lời

- Mỗi câu trả lời của chatbot có nút biểu tượng phóng to ở góc trên bên phải của nội dung.
- Nút có nhãn hỗ trợ đọc màn hình mô tả rõ chức năng.
- Khi nhấn, nội dung câu trả lời đã render được sao chép sang một hộp đọc đặt giữa màn hình.
- Hộp đọc có lớp nền phủ mờ, chiều rộng tối đa khoảng `900px`, chiều cao tối đa `80vh`, font và khoảng cách dòng lớn hơn khung chat.
- Nội dung dài cuộn bên trong; bảng và hình ảnh vẫn hiển thị đúng, không vượt khung.
- Người dùng đóng hộp đọc bằng nút đóng, phím `Escape` hoặc nhấn vào lớp nền ngoài hộp.
- Trên màn hình nhỏ, hộp đọc chiếm gần toàn bộ màn hình với lề an toàn.
- Khi hộp đọc mở, focus chuyển vào nút đóng; khi đóng, focus quay lại nút phóng to đã kích hoạt.
- Hộp phóng to chỉ để đọc, không nhân bản các nút phản hồi hoặc thao tác có thể tạo tác dụng phụ.

## Ô nhập chat

- Xóa nút đính kèm, input file, vùng hiển thị tệp và JavaScript xử lý tệp.
- Xóa dòng “Được hỗ trợ bởi AI · Thông tin mang tính tham khảo”.
- Căn lại textarea, bộ đếm ký tự và nút gửi để ô nhập không còn khoảng trống do các phần tử đã xóa.

## Trạng thái và xử lý lỗi

- Nếu một câu trả lời không có nội dung hợp lệ, nút phóng to không được tạo.
- Việc mở/đóng hộp đọc không sửa DOM hoặc trạng thái của tin nhắn gốc.
- Không phụ thuộc vào Storage API nên chế độ riêng tư hoặc trình duyệt chặn storage không phát sinh cảnh báo.
- Các thao tác đóng/mở phải an toàn khi được bấm liên tiếp.

## Kiểm thử chấp nhận

1. Tải trang mới: chỉ bong bóng dài xuất hiện ngay và có đúng nội dung mới.
2. Đóng bong bóng dài: bong bóng ngắn “Chào bạn” xuất hiện.
3. Mở chat bằng bất kỳ điểm kích hoạt hợp lệ nào: cả hai bong bóng biến mất và không tái xuất hiện khi hover, touch, đóng hay thu nhỏ chat.
4. Gửi nhiều tin nhắn, đóng rồi mở chat: hội thoại của trang hiện tại vẫn còn.
5. Tải lại trang: hội thoại cũ không được phục hồi và bong bóng dài xuất hiện lại.
6. Nút phóng to có trên từng câu trả lời bot; hộp đọc hiển thị đúng văn bản, ảnh và bảng, đồng thời đóng được bằng cả ba cách.
7. Nút đính kèm và dòng chú thích AI không còn trong giao diện hoặc luồng bàn phím.
8. Mascot không có khung tròn và lớn hơn đúng `0.5cm` theo cả chiều rộng lẫn chiều cao trên desktop và mobile.
9. Widget hoạt động ở desktop, tablet và mobile; không có lỗi JavaScript trong console.

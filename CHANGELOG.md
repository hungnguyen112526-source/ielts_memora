# Thay đổi

## Lỗi người dùng đã sửa
- **Bấm làm đề phải chờ thư viện đề rồi mới vào bài**: nút Làm / Làm tiếp dùng `on_click` thay vì `if button: ... st.rerun()` (trước đây chạy script 2 lần, lần đầu dựng lại cả thư viện).
- **Khung trống "Orange / Reading" hiện trước bài thi**: engine ẩn đến khi nhận đề (có vòng chờ), font Google không còn chặn hiển thị.
- **Màn hình tối lại, giật khi đang làm**: Streamlit làm mờ phần tử cũ mỗi lần autosave chạy lại script; đã tắt hiệu ứng ở màn làm bài, và mỗi lần chạy lại chỉ còn 1 truy vấn DB thay vì 5.
- **Mất bài khi đóng tab/F5/chuyển trang**: thêm bản nháp `localStorage`, tự khôi phục khi mở lại.
- **Nộp xong bấm thoát ngay thì mất kết quả** (sự kiện submit bị ghi đè): server coi sự kiện thoát/chuyển đề/autosave mang cờ "đã nộp" là nộp bài; bài đã nộp không bao giờ bị ghi đè.
- **Điện thoại**: thanh số câu không còn bị thanh trình duyệt che (`100dvh`), nút "Danh sách đề" luôn hiện, khung bài đọc không biến mất khi xoay/mở rộng cửa sổ.
- **Tạm dừng đồng hồ**: giờ che bài và lưu trạng thái, không còn vừa dừng vừa làm tiếp được.
- **Thời gian làm bài** được lưu mỗi phút; chế độ sáng/tối chỉ lưu khi người dùng tự bấm.
- **Tài khoản bị khóa/xóa** bị đăng xuất sau ≤ 60 giây (trước đây dùng được đến khi tải lại trang).
- **Đổi mật khẩu rồi F5 bị đăng xuất**: cookie mới được ghi ngay.
- Ký tự `& < "` trong ô điền từ không còn làm hỏng hiển thị.

## Nâng cấp
- Đáp án chỉ gửi xuống trình duyệt sau khi nộp (trước đây nằm sẵn trong dữ liệu đề).
- Hiện lời giải từng nhóm câu sau khi nộp (`data/explanations`, trước đây có file nhưng không dùng).
- Thư viện đề nhẹ hơn (không tải 1000 lượt làm kèm chi tiết mỗi lần chạy lại); trang Quản trị chỉ tạo bản sao lưu khi bấm nút.
- Danh mục đề không sập khi ổ đĩa chỉ đọc.
- Tách `core/exam_events.py` (logic sự kiện, có test); thêm 14 test Python và bộ test engine bằng jsdom; `tools/validate.py` kiểm tra thêm lời giải.

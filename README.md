# IELTS Memora

Web luyện IELTS bằng Streamlit: Ngữ pháp, Reading, Listening, Writing, Speaking, có đăng nhập và lưu tiến độ theo tài khoản.

## Chạy thử

```bash
pip install -r requirements.txt
streamlit run app.py
```

Lần đầu mở web, bấm **Tạo tài khoản**. Dữ liệu người dùng nằm trong file `memora.db` (SQLite, tự tạo).
Muốn đặt file ở chỗ khác: `MEMORA_DB=/duong/dan/memora.db streamlit run app.py`.

Giao diện làm bài dùng Tailwind CSS và font Inter tải từ CDN, nên máy người dùng cần có internet.

Giao diện chung (màu, thẻ, sidebar, đăng nhập) nằm trong `core/ui.py` và `.streamlit/config.toml`; logo ở `assets/`. Màn làm bài chiếm trọn chiều cao cửa sổ, các nút Danh sách đề / Đề trước / Đề sau nằm ngay trong header của engine. Yêu cầu Streamlit từ 1.52.

## Cấu trúc

```
app.py                  Điều hướng + chặn chưa đăng nhập
views/                  Mỗi mục một file: home, reading, grammar, listening, writing, speaking, account
core/
  db.py                 SQLite: tài khoản, phiên đăng nhập, tiến độ, lịch sử làm bài
  auth.py               Đăng ký, đăng nhập, phiên, đổi mật khẩu
  session.py            Trạng thái đăng nhập trong Streamlit + cookie ghi nhớ
  catalog.py            Danh mục đề (tự quét thư mục data/)
  scoring.py            Chấm điểm + quy đổi band (chạy ở server)
  reader_component.py   Nối Streamlit với engine làm bài
engine/reader/          Engine làm bài (giao diện từ cam21: chia đôi, highlight, timer…)
engine/cookie_bridge/   Component vô hình để ghi cookie đăng nhập
data/reading/           Dữ liệu đề (xem bên dưới)
tools/                  validate.py, build_catalog.py
```

## Thêm đề Reading

Mỗi đề là **một file JSON**, đặt vào đúng thư mục:

```
data/reading/<mục>/<bộ>/series.json        # {"id","title","description","badge","order"}
data/reading/<mục>/<bộ>/test-<số>.json
```

`<mục>` là một trong `band_4_5`, `band_5_6_5`, `orange`, `vol` (khai báo trong `data/reading/categories.json`).
Ví dụ bộ có sẵn: `data/reading/orange/orange-21/`.

Danh mục tự cập nhật khi bạn thêm, sửa hoặc xóa file, không cần sửa code. Trước khi dùng, chạy:

```bash
python tools/validate.py
```

Công cụ này kiểm tra thiếu đáp án, câu bị sót hoặc dư, id trùng, thư mục không khớp, dạng câu hỏi lạ.

### Các trường chính của một đề

| Trường | Ý nghĩa |
|---|---|
| `id` | Duy nhất, ví dụ `orange-22-test-1` |
| `series`, `category` | Phải khớp tên thư mục |
| `title`, `summary`, `subtitle` | Tên đề, mô tả ngắn, dòng phụ trong header |
| `durationMin`, `totalQuestions` | Thời gian (phút) và số câu. Đề ngắn hơn 40 câu vẫn chạy |
| `bandTable` | (tuỳ chọn) bảng quy đổi riêng, ví dụ `[[10,"5.0"],[5,"4.0"]]`, mặc định là bảng Academic 40 câu |
| `passages[]` | `label`, `title`, `paragraphs`, `groups[]`, `qRange` (câu đầu, câu cuối) |
| `answers` | `{"1": ["mining"], "8": ["TRUE"], ...}`, mỗi câu có thể có nhiều đáp án chấp nhận |
| `pairQuestions` | (tuỳ chọn) cặp câu chọn 2 đáp án, thứ tự nào cũng đúng |

Chỗ điền từ viết là `{{số câu}}` trong văn bản. Các dạng câu hỏi hiện có:
`tfng`, `mcq`, `multi2`, `matching`, `notes`, `summary_box`, `summary_text`, `table`, `flowchart`.
Muốn thêm dạng mới, thêm một nhánh render trong `renderQuestions` của `engine/reader/index.html` và tên dạng vào `KNOWN_TYPES` trong `tools/validate.py`.

Giữ cho file nhẹ: một đề một file, ảnh để file riêng và ghi đường dẫn, không nhúng base64.

## Đăng nhập

- Mật khẩu được băm bằng PBKDF2-SHA256 (310.000 vòng, salt riêng cho mỗi người). Không lưu mật khẩu gốc.
- Sai mật khẩu 5 lần trong 10 phút thì tạm khóa tên đăng nhập đó.
- Khi đăng nhập, web đặt cookie `memora_session` (14 ngày) để **tải lại trang vẫn còn đăng nhập**. Server chỉ lưu bản băm của mã phiên. Đăng xuất hoặc đổi mật khẩu sẽ hủy phiên.
- Điểm số được **chấm lại ở server** từ đáp án người dùng gửi lên, không tin điểm do trình duyệt báo.
- Khi đưa lên mạng, hãy chạy sau HTTPS. Cookie được ghi bằng JavaScript nên không có cờ HttpOnly; đây là giới hạn của Streamlit.
- Chưa có quên mật khẩu qua email. Cần thì thêm sau (cần gửi mail).

## Sao lưu

Sao lưu file `memora.db` (và thư mục `data/` nếu bạn sửa đề).

## Việc chưa làm

Ngữ pháp, Listening, Writing, Speaking mới có trang giữ chỗ, chờ tài liệu.

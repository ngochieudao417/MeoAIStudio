# Mèo AI Studio (Local Studio)

Ứng dụng chạy cục bộ trên Windows để thu thập nội dung từ các nền tảng được hỗ trợ, xử lý video và tạo nội dung bằng AI. Giao diện web được phục vụ local; dữ liệu tải về và cấu hình tài khoản được lưu trên máy người dùng.


> **Trạng thái:** dự án đang phát triển. Repo chứa mã ứng dụng và công cụ đóng gói, nhưng chưa có quy trình cài đặt môi trường gốc hoàn chỉnh cho một máy mới chỉ từ bản clone.

## Chức năng chính

- Thu thập nội dung theo từ khóa, liên kết hoặc kênh từ các nền tảng mà MediaCrawler hỗ trợ.
- Theo dõi kênh, tải nội dung mới và tạo video ngắn từ nội dung đã thu thập.
- Xử lý video: phụ đề, dịch, giọng đọc, dựng và xuất video.
- AI Studio hỗ trợ quy trình tạo video với các dịch vụ AI được người dùng cấu hình.

Chi tiết thao tác nằm trong [hướng dẫn sử dụng ứng dụng](HD-SU-DUNG.md) và [hướng dẫn công cụ thu thập](src/HUONG-DAN.md).

## Chạy trên máy phát triển đã thiết lập

Yêu cầu: Windows x64, môi trường Python **3.11** tại `.venv/` ở gốc repo, cùng các phụ thuộc và trình duyệt cần thiết đã được cài. Nhiều module trong `src/` nạp tệp `.pyc` tương ứng; các tệp này là một phần của ứng dụng, không phải cache có thể xóa.

1. Chạy `CHAY-APP.bat` tại gốc repo.
2. Mở `http://127.0.0.1:8770/` nếu trình duyệt không tự mở.
3. Đăng nhập các nền tảng cần dùng trong giao diện và nhập API key của riêng bạn khi sử dụng tính năng AI.

Có thể chạy server trực tiếp bằng `.venv\Scripts\python.exe local_server.py`. Tệp `CHAY-APP.bat` sẽ báo lỗi nếu thiếu `.venv\Scripts\python.exe`.

### Thiết lập trên máy mới

`.venv/`, dữ liệu trình duyệt và các tệp cấu hình cá nhân không được đưa lên Git. Vì repo hiện **chưa có manifest/lockfile đầy đủ cho môi trường Python ở gốc**, bản clone mới chưa thể chạy chỉ bằng `CHAY-APP.bat`. Hãy dùng bộ cài do nhóm phát hành hoặc thiết lập môi trường cùng người phụ trách dự án. Script `src/CAI-DAT.bat` cài môi trường cho `src/Meowcrawler`; nó không tạo `.venv/` ở gốc mà `CHAY-APP.bat` yêu cầu.

## Cấu hình và dữ liệu riêng tư

API key có thể được nhập qua giao diện. `local_server.py` cũng đọc `config_keys.json` ở gốc repo nếu tệp này tồn tại. Chỉ tạo tệp đó trên máy cá nhân; không commit khóa, cookie, hồ sơ trình duyệt, database, log hoặc video đã tải. Các đường dẫn này được liệt kê trong [.gitignore](.gitignore).

Các thư mục dữ liệu thường gặp:

| Đường dẫn | Nội dung |
| --- | --- |
| `src/Meowcrawler/browser_data/` | Hồ sơ trình duyệt và trạng thái đăng nhập |
| `src/Meowcrawler/data/`, `Meowcrawler/data/` | Nội dung đã thu thập và tệp tạm |
| `src/processed_videos/` | Video xuất ra từ ứng dụng |
| `release/` | Bộ cài được tạo trên máy đóng gói |

Một số tệp nhạy cảm từng được đưa vào lịch sử Git trước khi có quy tắc bỏ qua. `.gitignore` chỉ ngăn thêm mới; nếu khóa cũ còn hiệu lực, cần thay khóa và xử lý lịch sử theo kế hoạch chung của nhóm.

## Cấu trúc repo

| Đường dẫn | Vai trò |
| --- | --- |
| `local_server.py`, `CHAY-APP.bat` | Điểm khởi chạy server và ứng dụng trên máy dev |
| `src/` | Module xử lý, tài nguyên và giao diện `src/web/` |
| `src/Meowcrawler/` | Mã crawler tích hợp và cấu hình phụ thuộc của nó |
| `packaging/` | Script tạo bộ cài Windows offline |
| `HD-SU-DUNG.md`, `src/HUONG-DAN.md` | Hướng dẫn thao tác |

`packaging/build_installer.py` hiện lấy một số thành phần từ môi trường máy đóng gói (Python 3.11, Chromium của Playwright và FFmpeg tại các đường dẫn được script quy định). Chạy script này trên máy mới cần kiểm tra và chuẩn bị đủ các đầu vào trước.

## Làm việc trong nhóm

- Tạo nhánh riêng cho từng thay đổi và gửi pull request để người khác review trước khi hợp nhất.
- Ghi cách tái hiện lỗi và cách kiểm tra sửa lỗi trong pull request.
- Kiểm tra các luồng cài đặt, đăng nhập, thu thập và xuất video khi thay đổi phần liên quan.
- Giữ dữ liệu khách hàng, tài khoản và API key ở máy cá nhân.

## Giấy phép và phạm vi sử dụng

Phần MediaCrawler tích hợp có [giấy phép riêng](src/Meowcrawler/LICENSE), giới hạn việc dùng vào học tập/nghiên cứu phi thương mại nếu chưa có sự đồng ý bằng văn bản của chủ sở hữu. Repo này chưa có giấy phép chung cho toàn bộ mã ứng dụng. Cần giải quyết quyền sử dụng các thành phần liên quan trước khi phân phối hoặc sử dụng cho mục đích thương mại.

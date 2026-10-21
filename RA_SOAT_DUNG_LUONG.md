# Rà soát dung lượng dự án (16/10/2026)

Số liệu trước khi tạo bộ cài, đơn vị MiB (1 MiB = 1.048.576 byte). Tổng khoảng 4,67 GiB. **Chưa xoá dữ liệu gốc nào.** Các dòng dưới đây không chồng lấn dung lượng.

| Thứ tự | Mục | Dung lượng | Vai trò và mức độ có thể dọn |
|---:|---|---:|---|
| 1 | `.git/objects/` | 1.458 | Lịch sử Git, không cần để chạy ứng dụng. Chỉ xử lý khi đã có bản sao repository và xác nhận không cần các commit cũ. |
| 2 | `.venv/` | 884 | Thư viện Python cục bộ. Có thể tạo lại từ cấu hình dự án, nhưng bản đang chạy phụ thuộc vào nó; chỉ dọn sau khi xác nhận bản cài hoạt động. |
| 3 | Cache trong `src/Meowcrawler/browser_data/` | 829 | Cache trang, JS, service worker của Chromium. Có thể tái tạo; chỉ dọn khi đã đóng trình duyệt và ứng dụng. |
| 4 | `Meowcrawler/data/` | 747 | Video/tài nguyên cá nhân đã tải. Cần người dùng chọn nội dung giữ lại. |
| 5 | `src/Meowcrawler/data/` | 503 | Dữ liệu cào, gần 500 MiB là một video Bilibili. Cần người dùng chọn nội dung giữ lại. |
| 6 | Phần còn lại của `src/Meowcrawler/browser_data/` | 230 | Hồ sơ trình duyệt, cookie, trạng thái đăng nhập; không nên dọn nếu còn dùng các tài khoản này. |
| 7 | `src/piper_vn/ngochuyennew.onnx` | 61 | Mô hình giọng nói offline; chỉ bỏ nếu không cần tính năng này. |

Các mục lớn hơn trong dữ liệu: `Meowcrawler/data/social_shorts/` 452 MiB (trong đó video nền gameplay 382 MiB), `Meowcrawler/data/ne_ban_quuyen/` 294 MiB, `src/Meowcrawler/data/bili/videos/` khoảng 500 MiB. Tệp mã nguồn `.py` trong `src` đa phần là lớp nạp cho `.pyc` cùng tên, vì vậy không xoá hàng loạt `.pyc` ở thư mục này. `src/Meowcrawler/` là mã crawler ứng dụng đang dùng; thư mục `Meowcrawler/` ở gốc chỉ chứa dữ liệu, không phải bản mã nguồn trùng lặp.

Bộ cài loại trừ Git, dữ liệu tải, cache và hồ sơ trình duyệt, các cơ sở dữ liệu và cấu hình cá nhân, khoá bí mật và API key. Người nhận cài bộ mới sẽ cần đăng nhập và nhập khoá riêng của họ.

## Bộ cài đã tạo

`release/LocalStudio-Setup.exe`: 813,2 MiB, một file cho Windows x64. Khi chạy, bộ cài giải nén vào `%LOCALAPPDATA%\LocalStudio`, tạo shortcut trên Desktop và mở ứng dụng. Đã kiểm tra nạp giao diện từ Python di động, chạy Chromium và FFmpeg trong staging, kiểm tra tự đọc EXE và CRC toàn bộ 17.950 tệp. Chưa thử trên một máy Windows sạch hoặc kiểm tra từng tác vụ cào/video sau khi cài.

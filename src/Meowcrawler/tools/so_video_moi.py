# -*- coding: utf-8 -*-
"""SỔ "video MỚI theo kênh" — `data/<nền tảng>/_video_moi.jsonl`.

🔴 09/09/2026 — VÌ SAO TÁCH RA ĐÂY. Trước đây bộ ghi sổ nằm THẲNG trong `douyin/core.py`
(`_ghi_video_moi`) và **chỉ Douyin có**; `video_moi.NEN_TANG` cũng chỉ liệt kê `["douyin"]`. Hậu quả:
khách theo dõi kênh **Bilibili/XHS** thì thẻ kênh vẫn đếm đúng (số đó lấy từ `theo_doi_config.json`)
nhưng danh sách "Video mới" **KHÔNG BAO GIỜ** có gì — đúng khiếu nại *"không thấy video về dù lên kênh
thì có"*. Chép bộ ghi sang từng nền là công thức "sửa 4 chỗ, sót là chắc" mà `CLAUDE.md` cảnh báo, nên
gom về MỘT hàm ở đây; mỗi nền chỉ còn một lời gọi ngay sau khi lưu video.

Khuôn bản ghi phải GIỮ NGUYÊN — `video_moi.py` (`tao_links`/`doc_nhom`) đọc đúng các khoá này:
    aweme_id · sec_uid · nickname · kenh · create_time · platform · file · da_xem
`file` là đường dẫn TƯƠNG ĐỐI tính từ `data/<nền tảng>/videos/`.

CHỈ ghi cho cào theo KÊNH (`sub_dir` bắt đầu bằng `kenh/`): tab "Video mới" gom theo kênh, video cào
theo từ-khoá/link không có kênh để gom.

Mọi lỗi đều NUỐT và trả False: đây là sổ PHỤ, hỏng nó KHÔNG được làm hỏng việc tải (cùng luật với
`_mark_seen` và `tien_do_tai`).
"""
import json
import os

TIEN_TO_KENH = "kenh/"


def duong_so(nen_tang: str, goc: str = "") -> str:
    """`goc` = thư mục `data` (tuỳ chọn). Truyền vào khi chỗ gọi KHÔNG import được `config` của
    MediaCrawler — ví dụ `tai_ytdlp.py` ở gốc repo. Không truyền thì đọc `config.SAVE_DATA_PATH`
    như các nền chạy trong MediaCrawler."""
    if goc:
        return os.path.join(goc, str(nen_tang or "khac"), "_video_moi.jsonl")
    import config
    base = config.SAVE_DATA_PATH if config.SAVE_DATA_PATH else "data"
    return os.path.join(base, str(nen_tang or "khac"), "_video_moi.jsonl")


def ghi(nen_tang, sub_dir, ten_file, vid="", uid="", nickname="", create_time=0, goc="") -> bool:
    """Ghi 1 dòng vào sổ. Trả True nếu ĐÃ ghi; False nếu bỏ qua hoặc lỗi.

    `ten_file` = tên file ĐÃ CÓ ĐUÔI (vd `abc_123456.mp4`) — không tự thêm `.mp4`, vì XHS đặt
    `_1.mp4`/`_2.mp4` cho note nhiều video và Bilibili có hậu tố tập `_P02...`.
    `uid`/`nickname`/`create_time` thiếu cũng không sao: `doc_nhom` gom theo `sec_uid or kenh`, còn
    `_ngay()` thiếu `create_time` thì lùi về mtime của file.
    """
    try:
        sub_dir = str(sub_dir or "")
        if not sub_dir.startswith(TIEN_TO_KENH):
            return False
        try:
            _ct = int(create_time or 0)
        except (TypeError, ValueError):
            _ct = 0
        ban_ghi = {
            "aweme_id": str(vid or ""),
            "sec_uid": str(uid or ""),
            "nickname": str(nickname or ""),
            "kenh": sub_dir[len(TIEN_TO_KENH):],
            "create_time": _ct,
            "platform": str(nen_tang or ""),
            "file": "%s/%s" % (sub_dir, ten_file),
            "da_xem": False,
        }
        p = duong_so(nen_tang, goc)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(ban_ghi, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False

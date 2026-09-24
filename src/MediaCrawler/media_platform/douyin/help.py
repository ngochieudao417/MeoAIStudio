# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/help.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name: Programmer Ajiang-Relakkes
# @Time    : 2024/6/10 02:24
# @Desc    : Get a_bogus parameter, for learning and communication only, do not use for commercial purposes, contact author to delete if infringement

import os
import random
import re
from typing import Optional

# 🐛 FIX (khách báo: cào Douyin "DỪNG BẤT THƯỜNG (mã thoát 1)" — execjs.compile('libs/douyin.js') crash):
# libs/douyin.js dùng cú pháp ES6+ (arrow func...). execjs chọn runtime + cache is_available() lúc `import execjs`:
# có Node trong PATH → chạy ES6 OK; KHÔNG có Node (máy khách không cài Node hệ thống) → execjs lùi JScript
# (Windows cscript, ~ES3) → parse ES6 FAIL "SyntaxError" → crash. Máy dev có Node trong PATH nên KHÔNG lộ.
# Fix: thêm BUNDLE node (vendor/node) vào PATH *TRƯỚC* `import execjs` (execjs check availability lúc import →
# phải sửa PATH trước, sửa sau vô tác dụng vì runtime object đã cache is_available()=False).
def _them_node_bundle_path():
    _here = os.path.dirname(os.path.abspath(__file__))
    # help.py = .../MediaCrawler/media_platform/douyin/help.py → node bundle ở:
    #  - khách: <app>/resources/app-src/MediaCrawler/media_platform/douyin → lên 4 cấp = resources/, +vendor/node
    #  - dev:   <repo>/MediaCrawler/media_platform/douyin → lên 3 cấp = <repo>/, +desktop/vendor/node
    _r4 = os.path.normpath(os.path.join(_here, "..", "..", "..", ".."))   # khách: resources/ ; dev: viralcrawl/ (thừa)
    _r3 = os.path.normpath(os.path.join(_here, "..", "..", ".."))         # khách: app-src/ ; dev: toolcaovideo/
    _cands = [
        os.path.join(_r4, "vendor", "node"),            # khách: resources/vendor/node
        os.path.join(_r3, "desktop", "vendor", "node"),  # dev: toolcaovideo/desktop/vendor/node
        os.path.join(_r4, "desktop", "vendor", "node"),  # phòng cấu trúc khác
    ]
    for _d in _cands:
        if os.path.isfile(os.path.join(_d, "node.exe")) or os.path.isfile(os.path.join(_d, "node")):
            if _d.lower() not in (os.environ.get("PATH", "") or "").lower():
                os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            return True
    return False

_them_node_bundle_path()

import execjs
from playwright.async_api import Page

from model.m_douyin import VideoUrlInfo, CreatorUrlInfo
from tools.crawler_util import extract_url_params_to_dict

# Sửa lỗi Windows UnicodeEncodeError (cp1252) khi PyExecJS pipe mã JS sang Node:
# ép execjs ghi mã JS ra FILE TẠM bằng UTF-8 thay vì pipe bằng mã hóa hệ thống.
try:
    from execjs import _external_runtime as _execjs_er

    _execjs_orig_ctx_init = _execjs_er.ExternalRuntime.Context.__init__

    def _execjs_ctx_init_utf8(self, runtime, source="", cwd=None, tempfile=False):
        _execjs_orig_ctx_init(self, runtime, source=source, cwd=cwd, tempfile=True)

    _execjs_er.ExternalRuntime.Context.__init__ = _execjs_ctx_init_utf8
except Exception:
    pass

# 🐛 KIẾN TRÚC RỦI RO (audit 21/07, chưa áp cho ĐÚNG dòng này): main.py import MỌI crawler ở TOP-LEVEL —
# dòng compile() này TRƯỚC ĐÂY không bọc try/except (chỉ đoạn vá encoding UTF-8 phía trên có bọc) VÀ dùng
# path TƯƠNG ĐỐI 'libs/douyin.js' phụ thuộc CWD lúc import. File thiếu/hỏng (cài lỗi, AV xoá nhầm), Node
# bị chặn giữa chừng, hay CWD khác MediaCrawler/ (đổi cách gọi trong tương lai) → exception bay ra TOP-LEVEL
# → sập main.py → khách cào BILIBILI/WEIBO/XHS... cũng '0 video / mã thoát 1' dù không đụng Douyin.
# Cùng lớp bug đã gặp thật với execjs (Node thiếu) và xhshow (XHS) — nay khoá luôn 2 điểm hở còn lại của
# CHÍNH dòng execjs.compile(douyin.js): path tuyệt đối (không phụ thuộc CWD) + try/except (lỗi thì báo RÕ
# CHỈ khi Douyin thực sự được gọi ký, các nền khác cào bình thường).
_douyin_js_loi = None
try:
    _douyin_js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "libs", "douyin.js")
    douyin_sign_obj = execjs.compile(open(os.path.normpath(_douyin_js_path), encoding="utf-8-sig").read())
except Exception as _e:
    douyin_sign_obj = None
    # 🔴 12/09/2026 — GHI KÈM TÌNH TRẠNG THẬT CỦA ĐƯỜNG DẪN. Khách 12/09 nhận
    #   `[Errno 13] Permission denied` mà app khuyên *"khôi phục file khỏi Cách ly rồi CÀI LẠI app"* —
    #   đó là lời khuyên của ca MẤT FILE (Errno 2, ca 03/09). Errno 13 nghĩa là file VẪN CÒN nhưng
    #   không mở được, cài lại thường KHÔNG chữa.
    #   ⚠ Đo được: `open()` một **THƯ MỤC** trên Windows cũng ném đúng `PermissionError errno 13`
    #     (còn file thiếu ném `FileNotFoundError errno 2`) ⇒ một dòng "là tệp / LÀ THƯ MỤC / không
    #     tồn tại" phân biệt được ngay ba ca, khỏi phải hỏi khách chụp màn hình thư mục.
    try:
        _p13 = os.path.normpath(_douyin_js_path)
        if not os.path.exists(_p13):
            _tt13 = "đường dẫn KHÔNG TỒN TẠI"
        elif os.path.isdir(_p13):
            _tt13 = "đường dẫn LÀ THƯ MỤC (không phải tệp)"
        else:
            _tt13 = "tệp CÓ THẬT, %d byte" % os.path.getsize(_p13)
    except Exception:
        _tt13 = "không kiểm được tình trạng đường dẫn"
    _douyin_js_loi = "%s — %s" % (str(_e)[:150], _tt13)

def get_web_id():
    """
    Generate random webid
    Returns:

    """

    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        else:
            return ''.join(
                [str(int(1e7)), '-', str(int(1e3)), '-', str(int(4e3)), '-', str(int(8e3)), '-', str(int(1e11))]
            )

    web_id = ''.join(
        e(int(x)) if x in '018' else x for x in e(None)
    )
    return web_id.replace('-', '')[:19]



async def get_a_bogus(url: str, params: str, post_data: dict, user_agent: str, page: Page = None):
    """
    Get a_bogus parameter, currently does not support POST request type signature
    """
    return get_a_bogus_from_js(url, params, user_agent)

def get_a_bogus_from_js(url: str, params: str, user_agent: str):
    """
    Get a_bogus parameter through js
    Args:
        url:
        params:
        user_agent:

    Returns:

    """
    if douyin_sign_obj is None:
        # Lỗi thật (Node/file libs/douyin.js) chỉ nổ ĐÚNG LÚC Douyin cần ký request — nền khác (Bilibili/
        # Weibo/XHS...) không hề bị ảnh hưởng vì exception không còn bay ra lúc `import` nữa (xem khai báo
        # douyin_sign_obj ở trên). `_douyin_js_loi` giữ nguyên văn lỗi gốc để chẩn đoán.
        raise RuntimeError("Douyin: không nạp được libs/douyin.js (%s) — kiểm tra Node/file JS còn nguyên "
                           "vẹn, cài lại app nếu vẫn lỗi." % (_douyin_js_loi or "không rõ nguyên nhân"))
    sign_js_name = "sign_datail"
    if "/reply" in url:
        sign_js_name = "sign_reply"
    return douyin_sign_obj.call(sign_js_name, params, user_agent)



async def get_a_bogus_from_playwright(params: str, post_data: dict, user_agent: str, page: Page):
    """
    Get a_bogus parameter through playwright
    playwright version is deprecated
    Returns:

    """
    if not post_data:
        post_data = ""
    a_bogus = await page.evaluate(
        "([params, post_data, ua]) => window.bdms.init._v[2].p[42].apply(null, [0, 1, 8, params, post_data, ua])",
        [params, post_data, user_agent])

    return a_bogus


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from Douyin video URL
    Supports the following formats:
    1. Normal video link: https://www.douyin.com/video/7525082444551310602
    2. Link with modal_id parameter:
       - https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?modal_id=7525082444551310602
       - https://www.douyin.com/root/search/python?modal_id=7471165520058862848
    3. Short link: https://v.douyin.com/iF12345ABC/ (requires client parsing)
    4. Pure ID: 7525082444551310602

    Args:
        url: Douyin video link or ID
    Returns:
        VideoUrlInfo: Object containing video ID
    """
    # If it's a pure numeric ID, return directly
    if url.isdigit():
        return VideoUrlInfo(aweme_id=url, url_type="normal")

    # Check if it's a short link (v.douyin.com)
    if "v.douyin.com" in url or url.startswith("http") and len(url) < 50 and "video" not in url:
        return VideoUrlInfo(aweme_id="", url_type="short")  # Requires client parsing

    # Try to extract modal_id from URL parameters
    # ViralCrawl: Douyin đổi tham số ở URL trang kênh modal_id → vid (bấm 1 video trong /user/ →
    # .../user/<sec>?...&vid=<aweme_id>). `vid` CHÍNH LÀ aweme_id → nhận cả 2 để 'Theo link' tải đúng 1 video
    # (không rơi sang parse_creator → tải cả kênh). Link kênh THUẦN (không vid) vẫn không khớp → đi nhánh creator.
    params = extract_url_params_to_dict(url)
    modal_id = params.get("modal_id") or params.get("vid")
    if modal_id:
        return VideoUrlInfo(aweme_id=modal_id, url_type="modal")

    # Extract ID from standard video URL: /video/number
    video_pattern = r'/video/(\d+)'
    match = re.search(video_pattern, url)
    if match:
        aweme_id = match.group(1)
        return VideoUrlInfo(aweme_id=aweme_id, url_type="normal")

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator ID (sec_user_id) from Douyin creator homepage URL
    Supports the following formats:
    1. Creator homepage: https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main
    2. Pure ID: MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE

    Args:
        url: Douyin creator homepage link or sec_user_id
    Returns:
        CreatorUrlInfo: Object containing creator ID
    """
    # If it's a pure ID format (usually starts with MS4wLjABAAAA), return directly
    if url.startswith("MS4wLjABAAAA") or (not url.startswith("http") and "douyin.com" not in url):
        return CreatorUrlInfo(sec_user_id=url)

    # Extract sec_user_id from creator homepage URL: /user/xxx
    user_pattern = r'/user/([^/?]+)'
    match = re.search(user_pattern, url)
    if match:
        sec_user_id = match.group(1)
        return CreatorUrlInfo(sec_user_id=sec_user_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    print("=== Video URL Parsing Test ===")
    test_urls = [
        "https://www.douyin.com/video/7525082444551310602",
        "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main&modal_id=7525082444551310602",
        "https://www.douyin.com/root/search/python?aid=b733a3b0-4662-4639-9a72-c2318fba9f3f&modal_id=7471165520058862848&type=general",
        "7525082444551310602",
    ]
    for url in test_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")

    # Test creator URL parsing
    print("=== Creator URL Parsing Test ===")
    test_creator_urls = [
        "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main",
        "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")

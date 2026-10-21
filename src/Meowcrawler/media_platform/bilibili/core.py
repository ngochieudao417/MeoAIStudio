# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/core.py
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
# @Time    : 2023/12/2 18:44
# @Desc    : Bilibili Crawler

import asyncio
import os
import random  # jitter NGẮN ngẫu nhiên giữa request bili (random tránh nhịp ĐỀU = dấu hiệu bot)
from asyncio import Task
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)
from playwright._impl._errors import TargetClosedError

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import bilibili as bilibili_store
from tools import utils
from tools import dich_ten
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import BilibiliLogin


def _ngu_sec() -> float:
    """Jitter NGẮN giữa request bili — KHÔNG còn 'cào từ từ' (gỡ theo yêu cầu; repo gốc NanmiCoder cũng không có).
    Bili no-browser API chịu được nhịp nhanh (burst 100 nav đã PASS); chỉ random NHẸ tránh nhịp ĐỀU tăm tắp
    (nhịp đều = dấu hiệu bot). Nếu sau này bị anti-bot/kill phiên thì NÂNG khoảng này lên."""
    return random.uniform(0.1, 0.4)


def _bili_safe_name(s, n=40):
    """Làm sạch tên cho đường dẫn file/thư mục (bỏ ký tự cấm Windows)."""
    import re as _re
    s = _re.sub(r'[<>:"/\\|?*\n\r\t]+', " ", str(s or "")).strip()
    s = _re.sub(r"\s+", " ", s)
    return (s[:n] or "khac").rstrip(". ")


def _bili_ghi_so_moi(video_item_view, sub_dir, ten_file):
    """Ghi 1 dòng "video mới theo kênh" cho Bilibili — xem `tools/so_video_moi`.

    🔴 09/09/2026 — trước đây CHỈ Douyin ghi sổ này, nên khách theo dõi kênh Bilibili thấy thẻ kênh
    đếm đúng nhưng danh sách "Video mới" luôn trống. `mid` của UP đóng vai `sec_uid` (khoá gom kênh),
    `pubdate` đóng vai `create_time` (ngày ĐĂNG, để chia thư mục theo ngày).
    """
    try:
        _v = video_item_view if isinstance(video_item_view, dict) else {}
        _own = _v.get("owner", {}) or {}
        from tools import so_video_moi as _svm
        _svm.ghi("bili", sub_dir, ten_file,
                 vid=str(_v.get("aid", "") or ""),
                 uid=str(_own.get("mid", "") or ""),
                 nickname=_own.get("name", "") or "",
                 create_time=_v.get("pubdate", 0) or _v.get("ctime", 0) or 0)
    except Exception:
        pass        # sổ PHỤ — hỏng nó không được làm hỏng lượt tải


# 🔴 12/09/2026 — NHỚ TRONG LƯỢT CÀO: mạng nào tải bản tách hình/tiếng không xong thì ĐỪNG thử lại
#   cho từng video. Ca khách: mỗi video đốt ~4 phút cho DASH rồi mới lùi; cào 20 video là hơn 1 GIỜ
#   vứt đi. Hai lần hỏng LIÊN TIẾP là đủ kết luận cho lượt này. Đếm ở cấp MODULE vì mỗi lượt cào là
#   một tiến trình riêng ⇒ lượt sau tự động bắt đầu lại từ 0, không cần cờ reset.
_DASH_HONG = [0]


def _bili_media_parts(video_item_view, page_info=None):
    """Trả (sub_dir, file_base) — CHIA thư mục lưu video bili theo từ-khoá/kênh GIỐNG Douyin:
    search -> tu-khoa/<kw>; creator -> kenh/<tên UP>; detail -> link.
    file_base = '<title>_<6 số cuối aid>' (độc nhất trong thư mục, nhiều video cùng từ khoá KHÔNG đè nhau).
    page_info: {page, part} — TẬP cụ thể khi video là HỢP TUYỂN (multi-P, "分P"/"选集"). Có giá trị →
    thêm hậu tố '_PxxTên-tập' vào file_base để mỗi tập ra 1 file riêng, không đè lên nhau."""
    view = video_item_view if isinstance(video_item_view, dict) else {}
    aid = view.get("aid", "")
    # Tên file = tiêu đề ĐÃ DỊCH sang ngôn ngữ đích (không chỉ dịch trên màn hình)
    title = _bili_safe_name(dich_ten.dich_tieu_de(view.get("title", ""), "bili"), 50)
    file_base = f"{title}_{str(aid)[-6:]}" if aid else (title or "video")
    if page_info and page_info.get("page"):
        _pg = page_info["page"]
        _part = _bili_safe_name(page_info.get("part") or "", 30)
        file_base += f"_P{_pg:02d}" + (f"_{_part}" if _part and _part != "khac" else "")
    ctype = config.CRAWLER_TYPE
    if ctype == "search":
        sub_dir = f"tu-khoa/{_bili_safe_name(source_keyword_var.get() or 'khac', 40)}"
    elif ctype == "creator":
        # Hậu tố mid (định danh duy nhất) — CÙNG công thức Douyin đã fix (douyin/core.py ~187). Thiếu hậu tố:
        # kênh ĐỔI TÊN → sinh folder MỚI (khách thấy "kênh bị tách"); 2 kênh TRÙNG TÊN hoặc tên RỖNG → dồn
        # chung 1 folder ("kênh bị sáp nhập"). Dùng tên GỐC, KHÔNG dùng tên-dịch (dịch không ổn định).
        _own = view.get("owner", {}) or {}
        owner = _own.get("name", "") or "khong-ro"
        _mid = str(_own.get("mid", "") or "").strip()
        _nick = _bili_safe_name(owner, 40)
        sub_dir = f"kenh/{_nick}_{_mid[-8:]}" if _mid else f"kenh/{_nick}"
    else:
        sub_dir = "link"
    return sub_dir, file_base


def _search_to_video_item(sr):
    """SEARCH RESULT bili (1 item) -> cấu trúc video_item như get_video_info (để update_bilibili_video ghi jsonl).
    Dùng cho XEM-TRƯỚC: search result ĐÃ đủ title/cover/like/view/duration -> KHỎI detail-fetch (nhanh + NHIỀU,
    1 trang ~30 video tức thì). cid/playurl KHÔNG có ở đây -> chỉ để XEM; lúc TẢI mới fetch detail lấy cid."""
    import re as _re
    title = _re.sub(r"<[^>]+>", "", sr.get("title") or "")   # bỏ <em class="keyword">...</em>
    pic = sr.get("pic") or ""
    if pic.startswith("//"):
        pic = "https:" + pic
    return {
        "View": {
            "aid": sr.get("aid"),
            "title": title,
            "desc": sr.get("description") or "",
            "pubdate": sr.get("pubdate"),
            "pic": pic,
            "owner": {"mid": sr.get("mid", 0), "name": sr.get("author") or sr.get("uname") or "", "face": sr.get("upic", "")},
            "stat": {"like": sr.get("like", 0), "dislike": 0, "view": sr.get("play", 0),
                     "favorite": sr.get("favorites", 0), "share": 0, "coin": 0,
                     "danmaku": sr.get("danmaku", sr.get("video_review", 0)), "reply": sr.get("review", 0)},
        },
    }


def _creator_vlist_to_video_item(v):
    """CREATOR vlist (1 item từ /x/space/wbi/arc/search) -> cấu trúc video_item như get_video_info.
    Dùng cho XEM-TRƯỚC cào KÊNH: vlist ĐÃ đủ title/pic/play/comment/created/author -> KHỎI fetch detail
    từng video (bug cũ: get_specified_videos fetch-detail 30 video/trang → kênh 180 video chậm 10-15ph +
    burst detail → bili 风控 → mất video → 'cào kênh không hết'). vlist KHÔNG có 'like' (chỉ play/comment)."""
    pic = v.get("pic") or ""
    if pic.startswith("//"):
        pic = "https:" + pic
    return {
        "View": {
            "aid": v.get("aid"),
            "title": v.get("title") or "",
            "desc": v.get("description") or "",
            "pubdate": v.get("created"),
            "pic": pic,
            "owner": {"mid": v.get("mid", 0), "name": v.get("author") or "", "face": ""},
            "stat": {"like": 0, "dislike": 0, "view": v.get("play", 0),
                     "favorite": 0, "share": 0, "coin": 0,
                     "danmaku": v.get("video_review", 0), "reply": v.get("comment", 0)},
        },
    }


class BilibiliCrawler(AbstractCrawler):
    context_page: Page
    bili_client: BilibiliClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        self.index_url = "https://www.bilibili.com"
        self.cookie_urls = [self.index_url]
        # UA CỐ ĐỊNH = UA lúc ĐĂNG NHẬP (mo_dang_nhap, Windows Chrome). bili ràng buộc phiên (SESSDATA)
        # theo User-Agent; get_user_agent() trả UA NGẪU NHIÊN khác UA login -> bili coi là phiên LẠ ->
        # VÔ HIỆU HÓA phiên = "cào 1 lần là bị đăng xuất". (xhs/core.py đã patch bỏ get_user_agent vì lý do này.)
        self.user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        self.cdp_manager = None
        self.browser_context = None  # set ở browser-mode; GIỮ None ở no-browser để close() không AttributeError
        self.ip_proxy_pool = None  # Proxy IP pool for automatic proxy refresh
        self._dl_tasks = []    # tải video chạy NỀN (song song có giới hạn) — fetch/API VẪN tuần tự
        self._dl_sem = None    # asyncio.Semaphore(MC_DL_CONCURRENCY) — tạo lazy trong event loop
        self._seen_ids = None  # ledger ID đã tải (cào KHÔNG TRÙNG / đào sâu) — lazy load

    def _ledger_path(self) -> str:
        base = config.SAVE_DATA_PATH if config.SAVE_DATA_PATH else "data"
        return os.path.join(base, "bilibili", "_da_tai_ids.txt")

    def _load_seen(self):
        if self._seen_ids is None:
            self._seen_ids = set()
            p = self._ledger_path()
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self._seen_ids = {line.strip() for line in f if line.strip()}
                except Exception:
                    pass
        return self._seen_ids

    def _mark_seen(self, vid: str):
        """Ghi ID video đã tải vào ledger (cào không trùng). Lỗi ghi KHÔNG làm hỏng việc tải."""
        if not vid:
            return
        self._load_seen().add(vid)
        p = self._ledger_path()
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(vid + "\n")
        except Exception:
            pass

    def _tai_nen(self, coro_fn, *a):
        """Lên lịch TẢI VIDEO chạy NỀN, giới hạn MC_DL_CONCURRENCY (mặc định 2). get_video_play_url vẫn qua
        semaphore(1) cũ → API tuần tự; chỉ get_video_media (tải bytes) chồng lấp = nhanh hơn, nhẹ anti-bot."""
        if self._dl_sem is None:
            self._dl_sem = asyncio.Semaphore(max(1, int(os.environ.get("MC_DL_CONCURRENCY", "2"))))
        async def _w():
            async with self._dl_sem:
                try:
                    await coro_fn(*a)
                except Exception as _e:
                    utils.logger.error(f"[tai-nen] {_e}")
                    # 🔴 (23/08) surface lỗi tải-nền ra UI (trước chỉ vào file log → khách không biết video rớt).
                    print("LOG:✗ Một video tải lỗi (bỏ qua, tải tiếp video khác): %s" % str(_e)[:120], flush=True)
        self._dl_tasks.append(asyncio.create_task(_w()))

    async def _drain_tai(self):
        """Đợi MỌI tải nền hoàn tất (gọi cuối mỗi hàm cào, trước khi return)."""
        if self._dl_tasks:
            await asyncio.gather(*self._dl_tasks, return_exceptions=True)
            self._dl_tasks = []

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        # CHẾ ĐỘ API-ONLY (no-browser) — MẶC ĐỊNH BẬT cho bili: KHÔNG mở Playwright -> không có fingerprint
        # trình duyệt tự động -> bili KHÔNG vô hiệu hóa phiên login (hết "cào 1 lần bị đăng xuất").
        # Cookie giải mã trực tiếp từ profile Chromium (DPAPI v10 + AES-GCM), client httpx thuần, wbi qua
        # API nav. Áp cho CẢ xem-trước (metadata, nhanh) lẫn tải. Kill-switch: env BILI_NO_BROWSER=0 -> browser.
        # macOS: cookie Chromium mã hoá App-Bound (key KHÔNG ở Keychain chuẩn) → cookie_decrypt ra RÁC →
        # phiên hỏng dù đã login. Nên MẶC ĐỊNH browser mode trên Mac (Chromium tự đọc cookie nội bộ).
        import sys as _sys
        _nb_mac_def = "0" if _sys.platform == "darwin" else "1"
        if os.environ.get("BILI_NO_BROWSER", _nb_mac_def) != "0":
            utils.logger.info("[BilibiliCrawler] Chế độ API-ONLY (no-browser) — không mở trình duyệt")
            self.bili_client = self._create_client_no_browser(httpx_proxy_format)
            pong_ok = await self.bili_client.pong()
            if not pong_ok:
                utils.logger.warning("[BilibiliCrawler] Cảnh báo: Không đăng nhập / cookie hết hạn — cào công khai sẽ gặp rate-limit. Hãy đăng nhập nếu muốn cào nhiều hơn.")
            await self._run_crawler_type()
            return

        async with async_playwright() as playwright:
            # Choose launch mode based on configuration
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[BilibiliCrawler] Launching browser using CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[BilibiliCrawler] Launching browser using standard mode")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(chromium, None, self.user_agent, headless=config.HEADLESS)
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            # Trang chủ bilibili.com NẶNG + mạng tới bilibili có lúc CHẬM -> kể cả "domcontentloaded" vẫn
            # timeout 30s; mà goto KHÔNG bọc try/except -> "Page.goto Timeout 30000ms" GIẾT cả crawl
            # ("bilibili không cào được"). Fix: "commit" (fire NGAY khi nhận response headers — đã đủ set
            # cookie buvid3; wbi key lấy qua API nav chứ không cần DOM) + BỌC try/except để goto chậm/lỗi
            # KHÔNG giết crawl (cookie sẵn trên profile + API vẫn cào được). Đồng bộ douyin/core.py.
            try:
                await self.context_page.goto(self.index_url, wait_until="commit", timeout=45000)
            except Exception as e:
                utils.logger.warning(f"[BilibiliCrawler] goto trang chủ bỏ qua (timeout/lỗi): {e}")

            # Create a client to interact with the xiaohongshu website.
            self.bili_client = await self.create_bilibili_client(httpx_proxy_format)
            pong_ok = await self.bili_client.pong()
            if not pong_ok:
                utils.logger.warning("[BilibiliCrawler] Cảnh báo: Không đăng nhập — cào công khai sẽ gặp rate-limit IP. Dùng --proxy nếu bị block.")

            await self._run_crawler_type()

    async def _run_crawler_type(self):
        """Dispatch theo CRAWLER_TYPE — dùng CHUNG cho cả chế độ browser lẫn no-browser."""
        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            await self.get_specified_videos(config.BILI_SPECIFIED_ID_LIST)
        elif config.CRAWLER_TYPE == "creator":
            if config.CREATOR_MODE:
                for creator_url in config.BILI_CREATOR_ID_LIST:
                    try:
                        creator_info = parse_creator_info_from_url(creator_url)
                        utils.logger.info(f"[BilibiliCrawler._run_crawler_type] Parsed creator ID: {creator_info.creator_id} from {creator_url}")
                        await self.get_creator_videos(int(creator_info.creator_id))
                    except ValueError as e:
                        utils.logger.error(f"[BilibiliCrawler._run_crawler_type] Failed to parse creator URL: {e}")
                        continue
            else:
                await self.get_all_creator_details(config.BILI_CREATOR_ID_LIST)
        elif config.CRAWLER_TYPE == "chase":
            await self.get_chase_series(config.BILI_SPECIFIED_ID_LIST)
        else:
            pass
        utils.logger.info("[BilibiliCrawler.start] Bilibili Crawler finished ...")

    async def get_chase_series(self, video_url_list: List[str]):
        """"ĐUỔI THEO BỘ" (hợp tuyển kênh — ugc_season, KHÁC "phân P"/pages là nhiều tập TRONG 1 video đã
        hỗ trợ sẵn ở get_bilibili_video). Nhận LINK 1 VIDEO bất kỳ trong hợp tuyển → get_video_info lấy field
        `ugc_season` (mid + season_id của UP chủ) → get_season_archives lấy TOÀN BỘ tập (phân trang tới hết)
        → tải từng tập như get_specified_videos. Video KHÔNG thuộc hợp tuyển nào (không có ugc_season) → báo
        rõ, bỏ qua (không đoán mò theo tiêu đề như Douyin — Bilibili có API chính thức đáng tin hơn)."""
        utils.logger.info("[BilibiliCrawler.get_chase_series] Bắt đầu đuổi theo bộ (hợp tuyển kênh)...")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for video_url in video_url_list:
            try:
                video_info = parse_video_info_from_url(video_url)
            except ValueError as e:
                utils.logger.error(f"[get_chase_series] Link video không hợp lệ: {video_url} ({e})")
                continue
            vid = video_info.video_id
            if str(vid).startswith("av") and str(vid)[2:].isdigit():
                detail = await self.get_video_info_task(aid=int(str(vid)[2:]), bvid="", semaphore=semaphore)
            else:
                detail = await self.get_video_info_task(aid=0, bvid=vid, semaphore=semaphore)
            if not detail:
                utils.logger.error(f"[get_chase_series] Không lấy được chi tiết video {vid} — bỏ qua.")
                continue
            view: Dict = detail.get("View") or {}
            season = view.get("ugc_season")
            if not season:
                # KHÔNG thuộc hợp tuyển KÊNH (ugc_season) — thử "phân P" (nhiều tập TRONG CÙNG 1 video,
                # field "pages"): get_bilibili_video ĐÃ tự lặp tải hết pages (xem dòng ~973) → chỉ cần đưa
                # ĐÚNG video này qua get_specified_videos, KHÔNG cần dò season_id/mid gì thêm.
                pages = view.get("pages") or []
                if len(pages) >= 2:
                    utils.logger.info(f"[get_chase_series] Video '{view.get('title', vid)}' là HỢP TUYỂN "
                                      f"PHÂN-P ({len(pages)} tập trong 1 video) — tải qua get_specified_videos...")
                    await self.get_specified_videos([vid])
                else:
                    utils.logger.error(f"[get_chase_series] Video '{view.get('title', vid)}' KHÔNG thuộc hợp "
                                       f"tuyển kênh (ugc_season) LẪN phân-P (pages) — không xác định được đây là bộ nào.")
                continue
            mid = season.get("mid") or (view.get("owner") or {}).get("mid")
            season_id = season.get("id") or season.get("season_id")
            if not mid or not season_id:
                utils.logger.error(f"[get_chase_series] Video '{view.get('title', vid)}' có ugc_season nhưng "
                                   f"thiếu mid/season_id — bỏ qua.")
                continue
            utils.logger.info(f"[get_chase_series] '{view.get('title', vid)}' thuộc hợp tuyển "
                              f"'{season.get('title', '')}' (mid={mid}, season_id={season_id}) — lấy toàn bộ tập...")

            all_bvids = []
            page_num = 1
            while True:
                res = await self.bili_client.get_season_archives(mid=mid, season_id=season_id, page_num=page_num)
                archives = (res or {}).get("archives") or []
                if not archives:
                    break
                all_bvids.extend(a.get("bvid") for a in archives if a.get("bvid"))
                total = ((res or {}).get("page") or {}).get("total", 0)
                if page_num * 30 >= total or not total:
                    break
                page_num += 1
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            utils.logger.info(f"[get_chase_series] Hợp tuyển '{season.get('title', '')}': tìm được {len(all_bvids)} tập — đang tải...")
            if all_bvids:
                await self.get_specified_videos(all_bvids)

    def _create_client_no_browser(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """Tạo BilibiliClient KHÔNG mở browser: cookie giải mã trực tiếp từ profile Chromium
        (DPAPI v10 + AES-GCM) qua cookie_decrypt. Tránh fingerprint Playwright headless."""
        import sys as _sys
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        import cookie_decrypt
        udd = os.path.join(
            os.environ.get("MC_BROWSER_DATA_DIR") or os.path.join(os.getcwd(), "browser_data"),
            config.USER_DATA_DIR % config.PLATFORM,
        )
        cookie_str = cookie_decrypt.cookie_header(udd, "bilibili.com")
        cookie_dict = {}
        for _part in cookie_str.split("; "):
            if "=" in _part:
                _k, _v = _part.split("=", 1)
                cookie_dict[_k] = _v
        if cookie_str:
            utils.logger.info("[BilibiliCrawler] no-browser: đọc %d cookie từ profile (httpx thuần)" % len(cookie_dict))
        else:
            utils.logger.warning("[BilibiliCrawler] no-browser: KHÔNG đọc được cookie bili (chưa đăng nhập?)")
        return BilibiliClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=None,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )

    async def search(self):
        """
        search bilibili video
        """
        # Search for video and retrieve their comment information.
        if config.BILI_SEARCH_MODE == "normal":
            await self.search_by_keywords()
        elif config.BILI_SEARCH_MODE == "all_in_time_range":
            await self.search_by_keywords_in_time_range(daily_limit=False)
        elif config.BILI_SEARCH_MODE == "daily_limit_in_time_range":
            await self.search_by_keywords_in_time_range(daily_limit=True)
        else:
            utils.logger.warning(f"Unknown BILI_SEARCH_MODE: {config.BILI_SEARCH_MODE}")

    @staticmethod
    async def get_pubtime_datetime(
        start: str = config.START_DAY,
        end: str = config.END_DAY,
    ) -> Tuple[str, str]:
        """
        Get bilibili publish start timestamp pubtime_begin_s and publish end timestamp pubtime_end_s
        ---
        :param start: Publish date start time, YYYY-MM-DD
        :param end: Publish date end time, YYYY-MM-DD

        Note
        ---
        - Search time range is from start to end, including both start and end
        - To search content from the same day, to include search content from that day, pubtime_end_s should be pubtime_begin_s plus one day minus one second, i.e., the last second of start day
            - For example, searching only 2024-01-05 content, pubtime_begin_s = 1704384000, pubtime_end_s = 1704470399
              Converted to readable datetime objects: pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0), pubtime_end_s = datetime.datetime(2024, 1, 5, 23, 59, 59)
        - To search content from start to end, to include search content from end day, pubtime_end_s should be pubtime_end_s plus one day minus one second, i.e., the last second of end day
            - For example, searching 2024-01-05 - 2024-01-06 content, pubtime_begin_s = 1704384000, pubtime_end_s = 1704556799
              Converted to readable datetime objects: pubtime_begin_s = datetime.datetime(2024, 1, 5, 0, 0), pubtime_end_s = datetime.datetime(2024, 1, 6, 23, 59, 59)
        """
        # Convert start and end to datetime objects
        start_day: datetime = datetime.strptime(start, "%Y-%m-%d")
        end_day: datetime = datetime.strptime(end, "%Y-%m-%d")
        if start_day > end_day:
            raise ValueError("Wrong time range, please check your start and end argument, to ensure that the start cannot exceed end")
        elif start_day == end_day:  # Searching content from the same day
            end_day = (start_day + timedelta(days=1) - timedelta(seconds=1))  # Set end_day to start_day + 1 day - 1 second
        else:  # Searching from start to end
            end_day = (end_day + timedelta(days=1) - timedelta(seconds=1))  # Set end_day to end_day + 1 day - 1 second
        # Convert back to timestamps
        return str(int(start_day.timestamp())), str(int(end_day.timestamp()))

    async def search_by_keywords(self):
        """
        search bilibili video with keywords in normal mode
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search_by_keywords] Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        user_max = config.CRAWLER_MAX_NOTES_COUNT  # GIỮ count GỐC user (override dưới chỉ để vòng while chạy ≥1 trang)
        if not config.ENABLE_GET_MEIDAS:
            # XEM-TRƯỚC: cho xem NHIỀU để chọn (search result RẺ, không detail-fetch) -> nâng cap ≥60 (3 trang).
            # Tải TỪ TỪ từng trang (per-page sleep dưới) -> user thấy thêm dần. Pick rồi mới tải video thật.
            user_max = max(user_max, 60)
            config.CRAWLER_MAX_NOTES_COUNT = max(config.CRAWLER_MAX_NOTES_COUNT, 60)
        elif config.CRAWLER_MAX_NOTES_COUNT < bili_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = bili_limit_count
        start_page = config.START_PAGE  # start page number
        # "Cào KHÔNG TRÙNG" (đào sâu): MC_DEEP_NEW=1 → bỏ video ĐÃ tải, đào trang SÂU tới khi đủ N video MỚI
        # (trần MC_DEEP_PAGE_CAP=40) thay vì dừng theo count. Gate: DEEP off (mặc định) = hành vi CŨ y nguyên.
        DEEP = os.environ.get("MC_DEEP_NEW", "0") == "1"
        try:
            DEEP_PAGE_CAP = int(os.environ.get("MC_DEEP_PAGE_CAP", "40") or 40)
        except (TypeError, ValueError):
            DEEP_PAGE_CAP = 40
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Current search keyword: {keyword}")
            page = 1
            crawled = 0  # số video ĐÃ tải cho keyword này — giới hạn theo user_max (khỏi tải cả trang 20)
            while ((page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT) \
                    or (DEEP and (page - start_page) < DEEP_PAGE_CAP):
                if page < start_page:
                    utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Skip page: {page}")
                    page += 1
                    continue

                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] search bilibili keyword: {keyword}, page: {page}")
                video_id_list: List[str] = []
                # 🐛 FIX (tổng kiểm tra HIGH): 风控/wbi-sign lỗi tạm → search_video_by_keyword raise DataFetchError.
                # TRƯỚC không try/except → sập cả for-keyword (mất các keyword còn lại). Giờ: retry backoff, hết →
                # sang keyword KẾ (giữ video đã có). Biến-thể time-range đã có try/except; nhánh normal trước thiếu.
                try:
                    videos_res = await self.bili_client.search_video_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=bili_limit_count,
                        order=SearchOrderType.DEFAULT,
                        pubtime_begin_s=0,  # Publish date start timestamp
                        pubtime_end_s=0,  # Publish date end timestamp
                    )
                except Exception as _e:
                    _kw_retry = getattr(self, "_kw_loi", 0) + 1
                    self._kw_loi = _kw_retry
                    _max_r = int(os.getenv("MC_BILI_RETRY", "3") or 3)
                    if _kw_retry > _max_r:
                        self._kw_loi = 0
                        utils.logger.warning(f"[BilibiliCrawler.search_by_keywords] keyword '{keyword}' lỗi {_kw_retry} lần (风控: {str(_e)[:70]}) → sang keyword kế.")
                        break
                    _bk = min(30.0, 3.0 * _kw_retry)
                    utils.logger.info(f"[BilibiliCrawler.search_by_keywords] '{keyword}' trang {page} lỗi → thử lại sau {_bk:.0f}s ({_kw_retry}/{_max_r}).")
                    print("LOG:⏳ Bilibili '%s' phản hồi chậm/hạn chế — thử lại sau %.0fs (%d/%d), CHƯA treo." % (keyword, _bk, _kw_retry, _max_r), flush=True)
                    await asyncio.sleep(_bk)
                    continue
                self._kw_loi = 0
                video_list: List[Dict] = videos_res.get("result")

                if not video_list:
                    utils.logger.info(f"[BilibiliCrawler.search_by_keywords] No more videos for '{keyword}', moving to next keyword.")
                    break

                # XEM-TRƯỚC (MC_GET_MEDIAS=0): search result ĐÃ đủ title/cover/like/view/duration -> ghi THẲNG
                # CẢ TRANG (~30 video) TỨC THÌ + từng cái (jsonl tăng dần -> preview hiện dần), KHÔNG detail-fetch
                # (chậm + ít). cid chỉ cần lúc TẢI -> chỉ download mode (dưới) mới fetch detail.
                if not config.ENABLE_GET_MEIDAS:
                    for sr in video_list:
                        if not sr.get("aid"):
                            continue
                        await bilibili_store.update_bilibili_video(_search_to_video_item(sr))
                        crawled += 1
                    if crawled >= user_max:
                        break
                    page += 1
                    await asyncio.sleep(_ngu_sec())
                    continue

                # GIỚI HẠN theo count USER: bilibili trả NGUYÊN trang 20 -> trước đây fetch-detail (sleep 2s/cái)
                # + TẢI HẾT trang dù user xin ít -> cào RẤT CHẬM (như treo). Chỉ xử lý số CÒN THIẾU.
                # Cào KHÔNG TRÙNG: bỏ video ĐÃ tải (theo aid) TRƯỚC fetch-detail/tải → chỉ tốn cho video MỚI.
                if DEEP:
                    _seen = self._load_seen()
                    _truoc = len(video_list)
                    video_list = [sr for sr in video_list if str(sr.get("aid")) not in _seen]
                    if _truoc != len(video_list):
                        utils.logger.info(f"[BilibiliCrawler.search_by_keywords] đào sâu: bỏ {_truoc - len(video_list)} video đã tải, còn {len(video_list)} mới (trang {page})")
                video_list = video_list[: max(user_max - crawled, 0)]
                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] count: user_max={user_max} crawled={crawled} -> lấy chi tiết {len(video_list)} video (trang bili {bili_limit_count}). NHIỀU detail/lần = burst -> bili dễ vô hiệu phiên.")
                if video_list:
                    print("LOG:📄 Bilibili '%s': đang lấy chi tiết %d video (trang %d, có nghỉ né hạn chế, CHƯA treo)…" % (keyword, len(video_list), page), flush=True)
                if not video_list:
                    if DEEP and (page - start_page) < DEEP_PAGE_CAP:   # trang toàn video đã tải → sang trang sau (đào sâu)
                        page += 1
                        await asyncio.sleep(_ngu_sec())
                        continue
                    break

                semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                task_list = []
                try:
                    task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                except Exception as e:
                    utils.logger.warning(f"[BilibiliCrawler.search_by_keywords] error in the task list. The video for this page will not be included. {e}")
                video_items = await asyncio.gather(*task_list)
                for video_item in video_items:
                    if video_item:
                        video_id_list.append(video_item.get("View").get("aid"))
                        await bilibili_store.update_bilibili_video(video_item)
                        await bilibili_store.update_up_info(video_item)
                        self._tai_nen(self.get_bilibili_video, video_item, semaphore)   # tải NỀN song song
                        crawled += 1
                if crawled >= user_max:  # đủ số user xin -> dừng, khỏi sang trang sau
                    # BUG (cũ): break TRƯỚC _drain_tai (dưới) → khi đủ số (ca phổ biến nhất) task TẢI VIDEO nền
                    # bị bỏ dở → có metadata mà 0 file mp4 (tưởng "anti-bot 0 video"). Phải đợi tải XONG rồi mới break.
                    await self._drain_tai()
                    await self.batch_get_video_comments(video_id_list)
                    break
                page += 1

                # Sleep after page navigation
                await asyncio.sleep(_ngu_sec())
                utils.logger.info(f"[BilibiliCrawler.search_by_keywords] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")

                await self._drain_tai()   # đợi tải nền của trang xong
                await self.batch_get_video_comments(video_id_list)

    async def search_by_keywords_in_time_range(self, daily_limit: bool):
        """
        Search bilibili video with keywords in a given time range.
        :param daily_limit: if True, strictly limit the number of notes per day and total.
        """
        utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Begin search with daily_limit={daily_limit}")
        bili_limit_count = 20
        start_page = config.START_PAGE

        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Current search keyword: {keyword}")
            total_notes_crawled_for_keyword = 0

            for day in pd.date_range(start=config.START_DAY, end=config.END_DAY, freq="D"):
                if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                    utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}', skipping remaining days.")
                    break

                if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                    utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}', skipping remaining days.")
                    break

                pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(start=day.strftime("%Y-%m-%d"), end=day.strftime("%Y-%m-%d"))
                page = 1
                notes_count_this_day = 0

                while True:
                    if notes_count_this_day >= config.MAX_NOTES_PER_DAY:
                        utils.logger.info(f"[BilibiliCrawler.search] Reached MAX_NOTES_PER_DAY limit for {day.ctime()}.")
                        break
                    if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                        utils.logger.info(f"[BilibiliCrawler.search] Reached CRAWLER_MAX_NOTES_COUNT limit for keyword '{keyword}'.")
                        break
                    if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                        break

                    try:
                        utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, date: {day.ctime()}, page: {page}")
                        video_id_list: List[str] = []
                        videos_res = await self.bili_client.search_video_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=bili_limit_count,
                            order=SearchOrderType.DEFAULT,
                            pubtime_begin_s=pubtime_begin_s,
                            pubtime_end_s=pubtime_end_s,
                        )
                        video_list: List[Dict] = videos_res.get("result")

                        if not video_list:
                            utils.logger.info(f"[BilibiliCrawler.search] No more videos for '{keyword}' on {day.ctime()}, moving to next day.")
                            break

                        # GIỚI HẠN số video LẤY CHI TIẾT theo count còn thiếu (khớp search_by_keywords normal):
                        # bản gốc gather CẢ trang 20 detail trước khi mới break ở vòng dưới -> BURST request
                        # -> bili anti-crawler vô hiệu hóa phiên = "cào 1 lần bị đăng xuất". Chỉ lấy số CÒN THIẾU.
                        con_lai = config.CRAWLER_MAX_NOTES_COUNT - total_notes_crawled_for_keyword
                        if con_lai <= 0:
                            break
                        video_list = video_list[:con_lai]
                        utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] count còn thiếu={con_lai} -> lấy chi tiết {len(video_list)} video (trang bili {bili_limit_count}).")

                        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                        task_list = [self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore) for video_item in video_list]
                        video_items = await asyncio.gather(*task_list)

                        for video_item in video_items:
                            if video_item:
                                if (daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                                    break
                                if (not daily_limit and total_notes_crawled_for_keyword >= config.CRAWLER_MAX_NOTES_COUNT):
                                    break
                                if notes_count_this_day >= config.MAX_NOTES_PER_DAY:
                                    break
                                notes_count_this_day += 1
                                total_notes_crawled_for_keyword += 1
                                video_id_list.append(video_item.get("View").get("aid"))
                                await bilibili_store.update_bilibili_video(video_item)
                                await bilibili_store.update_up_info(video_item)
                                self._tai_nen(self.get_bilibili_video, video_item, semaphore)   # tải NỀN song song

                        page += 1

                        # Sleep after page navigation
                        await asyncio.sleep(_ngu_sec())
                        utils.logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")

                        await self._drain_tai()   # đợi tải nền của trang xong
                        await self.batch_get_video_comments(video_id_list)

                    except Exception as e:
                        utils.logger.error(f"[BilibiliCrawler.search] Error searching on {day.ctime()}: {e}")
                        break

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[BilibiliCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore), name=video_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_comments] begin get video_id: {video_id} comments ...")
                await asyncio.sleep(_ngu_sec())
                utils.logger.info(f"[BilibiliCrawler.get_comments] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching comments for video {video_id}")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=bilibili_store.batch_update_bilibili_video_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_comments] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_comments] may be been blocked, err:{e}")
                # Propagate the exception to be caught by the main loop
                raise

    async def get_creator_videos(self, creator_id: int):
        """
        get videos for a creator
        :return:
        """
        ps = 30
        pn = 1
        # XEM-TRƯỚC (MC_GET_MEDIAS=0): vlist ĐÃ đủ metadata → ghi THẲNG cả trang (như search dòng 417), KHÔNG
        # fetch-detail từng video. Trước đây get_specified_videos fetch-detail 30 video/trang (sleep mỗi cái)
        # → kênh 180 video chậm 10-15ph + burst → 风控 mất video ("cào kênh không hết"). GIỚI HẠN theo count
        # user để KHÔNG quét cả kênh 666 khi user chỉ xin 100.
        preview = not config.ENABLE_GET_MEIDAS
        user_max = config.CRAWLER_MAX_NOTES_COUNT if config.CRAWLER_MAX_NOTES_COUNT and config.CRAWLER_MAX_NOTES_COUNT > 0 else 10**9
        got = 0
        _loi_lien = 0   # đếm lỗi 风控/rỗng LIÊN TIẾP → hết retry thì DỪNG NHẸ (giữ video đã lấy), không sập cả lượt
        while True:
            # Pha lấy danh sách kênh Bilibili IM LẶNG (chỉ log vào file) → khách tưởng treo. In LOG: mỗi trang.
            print("LOG:🔍 Bilibili: đang quét kênh — trang %d (đã lấy %d video)…" % (pn, got), flush=True)
            # 🐛 FIX (tổng kiểm tra HIGH): 风控 (-352) → get() raise DataFetchError; data rỗng → KeyError. TRƯỚC
            # KHÔNG try/except → sập cả lần cào kênh + các kênh sau trong batch (Douyin CÓ retry, Bili thiếu).
            # Giờ: bắt lỗi → retry backoff MC_BILI_RETRY (mặc định 3) lần; hết → break GIỮ video đã lấy (thành-công-một-phần).
            try:
                result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
                vlist = result["list"]["vlist"]
                total = int(result["page"]["count"])
                _loi_lien = 0
            except Exception as _e:
                _loi_lien += 1
                _max_retry = int(os.getenv("MC_BILI_RETRY", "3") or 3)
                if _loi_lien > _max_retry:
                    utils.logger.warning(f"[BilibiliCrawler.get_creator_videos] kênh {creator_id} lỗi {_loi_lien} lần liên tiếp (风控/rỗng: {str(_e)[:80]}) → DỪNG kênh này, giữ {got} video đã lấy.")
                    break
                _back = min(30.0, 3.0 * _loi_lien)   # backoff 3s/6s/9s...
                utils.logger.info(f"[BilibiliCrawler.get_creator_videos] trang {pn} lỗi ({str(_e)[:60]}) → thử lại sau {_back:.0f}s ({_loi_lien}/{_max_retry}).")
                print("LOG:⏳ Bilibili phản hồi chậm/hạn chế (风控) — thử lại sau %.0fs (%d/%d), CHƯA treo." % (_back, _loi_lien, _max_retry), flush=True)
                await asyncio.sleep(_back)
                continue
            if preview:
                for v in vlist:
                    if not v.get("aid"):
                        continue
                    await bilibili_store.update_bilibili_video(_creator_vlist_to_video_item(v))
                    got += 1
                    if got >= user_max:
                        break
            else:
                # TẢI THẬT: chỉ lấy detail+tải số CÒN THIẾU (không tải cả trang 30 khi user xin ít / gần đủ).
                video_bvids_list = [video["bvid"] for video in vlist][: max(user_max - got, 0)]
                if video_bvids_list:
                    await self.get_specified_videos(video_bvids_list)
                    got += len(video_bvids_list)
            utils.logger.info(f"[BilibiliCrawler.get_creator_videos] trang {pn}: +{len(vlist)} video, đã lấy {got}/{min(user_max, total)} (tổng kênh {total}, preview={preview})")
            print("LOG:📄 Bilibili: đã lấy %d/%d video từ kênh (trang %d)…" % (got, min(user_max, total), pn), flush=True)
            if got >= user_max or total <= pn * ps:
                break
            await asyncio.sleep(_ngu_sec())
            pn += 1

    async def get_specified_videos(self, video_url_list: List[str]):
        """
        get specified videos info from URLs or BV IDs
        :param video_url_list: List of video URLs or BV IDs
        :return:
        """
        utils.logger.info("[BilibiliCrawler.get_specified_videos] Parsing video URLs...")
        bvids_list = []
        # `?p=` = TẬP đang xem trong video phân-P. `parse_video_info_from_url` chỉ trả BV nên số tập bị rơi mất
        # ⇒ nhớ riêng ở đây để `get_bilibili_video` tải ĐÚNG tập khách đang xem (xem ghi chú "CHỦ DỰ ÁN CHỐT").
        if not hasattr(self, "_p_theo_bv"):
            self._p_theo_bv = {}
        for video_url in video_url_list:
            try:
                video_info = parse_video_info_from_url(video_url)
                bvids_list.append(video_info.video_id)
                try:
                    from urllib.parse import urlparse, parse_qs
                    _q = parse_qs(urlparse(str(video_url)).query or "")
                    _pv = (_q.get("p") or ["1"])[0]
                    self._p_theo_bv[str(video_info.video_id)] = max(1, int(_pv))
                except (TypeError, ValueError):
                    self._p_theo_bv[str(video_info.video_id)] = 1
                utils.logger.info(f"[BilibiliCrawler.get_specified_videos] Parsed video ID: {video_info.video_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[BilibiliCrawler.get_specified_videos] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        # bvids_list có thể chứa 'av<aid>' (URL search bilibili chỉ có aid, không có bvid) -> route sang
        # tham số aid; còn 'BV...' -> bvid. (get_video_info nhận aid HOẶC bvid.) Trước đây luôn truyền bvid
        # -> av-id sai định dạng bvid -> 0 video detail -> "Cào video đã chọn" tải 0.
        task_list = []
        for vid in bvids_list:
            if str(vid).startswith("av") and str(vid)[2:].isdigit():
                task_list.append(self.get_video_info_task(aid=int(str(vid)[2:]), bvid="", semaphore=semaphore))
            else:
                task_list.append(self.get_video_info_task(aid=0, bvid=vid, semaphore=semaphore))
        if task_list:   # pha lấy CHI TIẾT nhiều video IM LẶNG (sleep giữa mỗi cái) → báo để khỏi tưởng treo
            print("LOG:📄 Bilibili: đang lấy chi tiết %d video (có nghỉ giữa mỗi cái né hạn chế, CHƯA treo)…" % len(task_list), flush=True)
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(video_aid)
                await bilibili_store.update_bilibili_video(video_detail)
                await bilibili_store.update_up_info(video_detail)
                self._tai_nen(self.get_bilibili_video, video_detail, semaphore)   # tải NỀN song song
        await self._drain_tai()
        await self.batch_get_video_comments(video_aids_list)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)

                # Sleep after fetching video details
                await asyncio.sleep(_ngu_sec())
                utils.logger.info(f"[BilibiliCrawler.get_video_info_task] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching video details {bvid or aid}")

                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None

    async def get_video_play_url_task(self, aid: int, cid: int, semaphore: asyncio.Semaphore) -> Union[Dict, None]:
        """
        Get video play url
        :param aid:
        :param cid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_play_url(aid=aid, cid=cid)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_play_url_task] Get video play url error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_video_play_url_task] have not fund play url from :{aid}|{cid}, err: {ex}")
                return None

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """
        create bilibili client
        :param httpx_proxy: httpx proxy
        :return: bilibili client
        """
        utils.logger.info("[BilibiliCrawler.create_bilibili_client] Begin create bilibili API client ...")
        cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
            self.browser_context,
            urls=self.cookie_urls,
        )
        bilibili_client_obj = BilibiliClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # Pass proxy pool for automatic refresh
        )
        return bilibili_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        launch browser and create browser context
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        utils.logger.info("[BilibiliCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.environ.get("MC_BROWSER_DATA_DIR") or os.path.join(os.getcwd(), "browser_data"), config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
                channel="chrome",  # Use system's stable Chrome version
            )
            return browser_context
        else:
            # type: ignore
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy, channel="chrome")
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        Launch browser using CDP mode
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # Display browser information
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[BilibiliCrawler] CDP browser info: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler] CDP mode launch failed, fallback to standard mode: {e}")
            # Fallback to standard mode
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        """Close browser context"""
        try:
            # If using CDP mode, special handling is required
            if self.cdp_manager:
                await self.cdp_manager.cleanup()
                self.cdp_manager = None
            elif self.browser_context:
                await self.browser_context.close()
            utils.logger.info("[BilibiliCrawler.close] Browser context closed ...")
        except TargetClosedError:
            utils.logger.warning("[BilibiliCrawler.close] Browser context was already closed.")
        except Exception as e:
            utils.logger.error(f"[BilibiliCrawler.close] An error occurred during close: {e}")

    async def get_bilibili_video(self, video_item: Dict, semaphore: asyncio.Semaphore):
        """
        download bilibili video
        :param video_item:
        :param semaphore:
        :return:
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Crawling image mode is not enabled")
            return
        video_item_view: Dict = video_item.get("View")
        aid = video_item_view.get("aid")
        # HỢP TUYỂN (multi-P, "分P"/"选集"): 1 video (1 aid/bvid) chứa NHIỀU TẬP, mỗi tập có "cid" riêng trong
        # field "pages" của response View. TRƯỚC ĐÂY chỉ lấy video_item_view["cid"] (cid MẶC ĐỊNH = tập 1) →
        # hợp tuyển nhiều tập chỉ tải được tập ĐẦU. Fix: nếu "pages" có ≥2 phần tử → lặp tải TỪNG tập; video
        # thường (pages rỗng/1 phần tử, hoặc field không tồn tại) → giữ NGUYÊN hành vi cũ (1 tập duy nhất).
        pages = video_item_view.get("pages") or []
        # 🔴 CHỦ DỰ ÁN CHỐT 02/08/2026: "CÀO THEO LINK chỉ lấy ĐÚNG tập đang xem. Cào theo BỘ mới là cả hợp tuyển."
        # Trước đây mọi chế độ đều tải HẾT `pages` ⇒ khách dán link 1 video phân-P, chọn "cào theo link", nhận về
        # cả chục tập — không phải thứ họ bấm. Nay chỉ chế độ `chase` (nút "cào theo bộ") mới quét hết tập;
        # `detail` lấy đúng tập ứng với `?p=` trong link (thiếu `p` → tập 1, đúng thứ mở ra khi bấm link).
        if len(pages) >= 2 and getattr(config, "CRAWLER_TYPE", "") != "chase":
            _bv1 = video_item_view.get("bvid") or ""
            _p = 1
            try:
                _p = int((getattr(self, "_p_theo_bv", {}) or {}).get(str(_bv1), 1) or 1)
            except (TypeError, ValueError):
                _p = 1
            _pg = None
            for _x in pages:
                if int(_x.get("page") or 0) == _p:
                    _pg = _x
                    break
            if _pg is None:
                _pg = pages[0]
                _p = int(_pg.get("page") or 1)
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Video {aid} có {len(pages)} tập (phân-P) — "
                              f"CÀO THEO LINK nên chỉ tải TẬP {_p}. Muốn cả bộ thì dùng 'cào theo bộ'.")
            if not await self._get_bilibili_video_1tap(video_item_view, semaphore, page_info=_pg):
                return
            # CỐ Ý KHÔNG mark ledger cấp video (aid/bvid): mới tải 1/N tập, đánh dấu cả video là "đã xử lý" sẽ
            # làm lần cào sau BỎ QUA các tập còn lại. Ledger CẤP TẬP đã được _get_bilibili_video_1tap ghi.
            return
        if len(pages) >= 2:
            _bv0 = video_item_view.get("bvid")
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Video {aid} là HỢP TUYỂN {len(pages)} tập → tải từng tập.")
            _co_tap_ok = False
            for pg in pages:
                if await self._get_bilibili_video_1tap(video_item_view, semaphore, page_info=pg):
                    _co_tap_ok = True
                await asyncio.sleep(_ngu_sec())
            # Ledger CẤP VIDEO (không phải cấp tập) vẫn ghi SAU khi đã thử hết mọi tập — để "đào sâu"/"cào không
            # trùng" (check ở aid, dòng ~456) tiếp tục coi đây là 1 video đã xử lý, không lặp lại toàn bộ hợp
            # tuyển ở lần cào sau. Check-trùng CẤP TẬP (không tải lại tập đã có) nằm trong _get_bilibili_video_1tap.
            # CHỈ mark khi ÍT NHẤT 1 tập thành công — TẤT CẢ tập fail (vd mất mạng hẳn) thì để lần cào sau thử
            # lại toàn bộ, tránh ledger báo "đã xử lý" trong khi 0 tập nào có file thật (đúng bug ledger đã fix
            # ở nhánh 1-tập bên dưới).
            if _co_tap_ok:
                self._mark_seen(str(aid))
                if _bv0:
                    self._mark_seen(str(_bv0))
            return
        ok = await self._get_bilibili_video_1tap(video_item_view, semaphore, page_info=None)
        # CHỈ ghi ledger khi TẢI THÀNH CÔNG THẬT (có file). BUG CŨ: mark_seen vô điều kiện dù get_video_play_url_task/
        # get_video_media fail (vd RemoteProtocolError với video lớn) → ledger báo "đã tải" trong khi 0 file mp4
        # → khách thấy "Lịch sử cào" ghi đã tải nhưng data/ trống, và cào lại (đào sâu) BỎ QUA video này vĩnh viễn
        # (tưởng đã xong) → "cào mãi không ra video nào". Giờ fail → KHÔNG mark, lần cào sau thử lại video này.
        if not ok:
            return
        aid = video_item_view.get("aid")
        _bv = video_item_view.get("bvid")
        self._mark_seen(str(aid))
        if _bv:
            self._mark_seen(str(_bv))

    async def _get_bilibili_video_1tap(self, video_item_view: Dict, semaphore: asyncio.Semaphore, page_info=None) -> bool:
        """Tải 1 TẬP cụ thể (page_info=dict từ 'pages') hoặc video thường (page_info=None, cid mặc định).
        Tách riêng khỏi get_bilibili_video để TÁI DÙNG cho từng tập của hợp tuyển — giữ NGUYÊN logic tải/lưu cũ.
        Trả True nếu tải THÀNH CÔNG (hoặc đã có sẵn/bỏ qua hợp lệ) — False nếu THẤT BẠI (caller không mark_seen)."""
        aid = video_item_view.get("aid")
        cid = page_info.get("cid") if page_info else video_item_view.get("cid")
        # CHECK TRÙNG CẤP TẬP: hợp tuyển cào lại (đào sâu/thêm video mới) không tải lại TẬP đã có — ledger
        # cấp video (aid/bvid) không đủ vì hợp tuyển có thể MỚI TẢI 1 PHẦN (bị dừng giữa chừng) ở lần trước.
        _tap_id = f"{aid}_p{page_info['page']}" if page_info and page_info.get("page") else None
        if _tap_id and _tap_id in self._load_seen():
            utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Bỏ qua tập đã tải: {_tap_id}")
            return True
        result = await self.get_video_play_url_task(aid, cid, semaphore)
        if result is None:
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video play url failed")
            return False
        # 🔵 DASH TRƯỚC (28/08/2026): `fnval=4048` trả video+audio TÁCH RỜI ở `result["dash"]`.
        # Ghép được → dùng luôn (1080p/4K). Không có dash / thiếu ffmpeg / ghép lỗi → rơi xuống
        # nhánh `durl` NGUYÊN VẸN bên dưới. ⚠ Video CŨ đôi khi chỉ có MP4 dù xin DASH (tài liệu
        # bilibili-API-collect issue #888) — nên BẮT BUỘC giữ hai nhánh, không được thay thẳng.
        _bo_dash = _DASH_HONG[0] >= 2          # xem `_DASH_HONG` ở đầu file
        _ct_dash = None if _bo_dash else await self._tai_dash_bili(result)
        if _ct_dash is not None:
            _DASH_HONG[0] = 0                  # lại chạy được thì quên chuỗi hỏng cũ đi
            sub_dir, file_base = _bili_media_parts(video_item_view, page_info=page_info)
            await bilibili_store.store_video(aid, _ct_dash, f"{file_base}.mp4", sub_dir=sub_dir)
            _bili_ghi_so_moi(video_item_view, sub_dir, f"{file_base}.mp4")
            if _tap_id:
                self._mark_seen(_tap_id)
            return True
        if not _bo_dash:
            _DASH_HONG[0] += 1
            if _DASH_HONG[0] == 2:
                print("LOG:⚠ Mạng này tải bản tách hình/tiếng không xong 2 lần liên tiếp — từ giờ trong "
                      "lượt cào này sẽ xin thẳng bản gộp sẵn cho nhanh (chất lượng thường 720p).", flush=True)

        # 🔴 KHÁCH BÁO 11/09/2026 (2 link BV, 8:15PM + 8:28PM, log y hệt nhau):
        #      ✗ Một video tải lỗi (bỏ qua, tải tiếp video khác): 'NoneType' object is not iterable
        #    GỐC: từ 28/08 `client.py` xin `fnval=4048` ⇒ Bilibili trả `dash` và **KHÔNG có `durl`**.
        #    Nhánh dưới đây (bản MP4 gộp sẵn) viết cho thời `fnval=1`, khi `durl` LUÔN có ⇒ `durl_list`
        #    là None ⇒ `for durl in None` NỔ. Mà đây lại là đường DUY NHẤT chạy khi DASH ghép không
        #    xong ⇒ đường lùi thành đường CHẾT. Khách nhận "Cào 0 video" kèm hai câu ĐỔ OAN của tầng
        #    trên ("VIDEO QUÁ LỚN" · "kiểm tra lại đăng nhập") — phiên còn sống, video không lớn.
        #    ⇒ Lùi cho ĐÚNG NGHĨA: XIN LẠI bản MP4 gộp sẵn (`fnval=1`) thay vì đọc `durl` chưa từng xin.
        durl_list = result.get("durl") or []
        if not durl_list:
            print("LOG:↩ Bản tách rời hình/tiếng ghép không xong — đang xin lại bản MP4 gộp sẵn (thường 720p)…",
                  flush=True)
            try:
                _r2 = await self.bili_client.get_video_play_url(aid=aid, cid=cid, fnval=1)
            except Exception as _e2:
                utils.logger.warning(f"[BilibiliCrawler] xin lại MP4 gộp sẵn lỗi: {str(_e2)[:120]}")
                _r2 = None
            durl_list = (_r2 or {}).get("durl") or []
            if not durl_list:
                print("LOG:✗ Bilibili không trả bản MP4 gộp sẵn nào cho video này — bỏ qua video. "
                      "Xem dòng ✗ ngay phía trên để biết khâu nào hỏng.", flush=True)
                utils.logger.info("[BilibiliCrawler.get_bilibili_video] không có durl kể cả khi xin fnval=1")
                return False
        max_size = -1
        video_url = ""
        backup_urls: List[str] = []
        for durl in durl_list:
            size = durl.get("size")
            if size > max_size:
                max_size = size
                video_url = durl.get("url")
                backup_urls = [u for u in (durl.get("backup_url") or []) if u]
        if video_url == "":
            utils.logger.info("[BilibiliCrawler.get_bilibili_video] get video url failed")
            return False

        # backup_url: Bilibili trả sẵn CDN mirror dự phòng cho CÙNG nội dung (cộng đồng xác nhận CDN
        # akamaized.net chậm/throttle với người dùng ngoài Trung Quốc đại lục, vd yt-dlp#10849). Đo thật
        # video review-phim: RemoteProtocolError lặp lại NHIỀU LẦN trên URL chính → thử mirror dự phòng
        # khi URL hiện tại thất bại hẳn (hết ngân sách resume) thay vì bỏ cuộc.
        content = await self.bili_client.get_video_media(video_url, backup_urls=backup_urls)
        await asyncio.sleep(_ngu_sec())
        utils.logger.info(f"[BilibiliCrawler.get_bilibili_video] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching video {aid}")
        if content is None:
            return False
        sub_dir, file_base = _bili_media_parts(video_item_view, page_info=page_info)
        extension_file_name = f"{file_base}.mp4"
        await bilibili_store.store_video(aid, content, extension_file_name, sub_dir=sub_dir)
        _bili_ghi_so_moi(video_item_view, sub_dir, extension_file_name)
        if _tap_id:
            self._mark_seen(_tap_id)   # ledger CẤP TẬP — riêng biệt với ledger cấp video ghi ở get_bilibili_video
        return True

    @staticmethod
    def _tim_ffmpeg():
        """ffmpeg để ghép DASH. MediaCrawler TRƯỚC ĐÂY không dùng ffmpeg bao giờ, nên tự dò ở đây.
        Không thấy → trả None → caller LÙI nhánh durl cũ (thà 720p còn hơn hỏng lượt cào)."""
        import shutil
        for c in (os.environ.get("FFMPEG_BIN"), os.environ.get("FFMPEG_PATH"), shutil.which("ffmpeg")):
            if c and os.path.isfile(c):
                return c
        return None

    async def _tai_dash_bili(self, result: Dict):
        """DASH: video + audio TÁCH RỜI → tải cả hai rồi ghép `-c copy`. Trả bytes, hoặc None để lùi durl.

        Dùng LẠI `get_video_media` (đã có 4 kết nối song song + đổi mirror `backup_url`) — không viết
        bộ tải thứ hai. Ghép `-c copy` nên KHÔNG mã hoá lại, gần như tức thì.
        Bất kỳ trục trặc nào (thiếu dash / thiếu ffmpeg / ghép lỗi) → None → nhánh durl cũ chạy nguyên vẹn.
        """
        dash = (result or {}).get("dash") or {}
        vids = dash.get("video") or []
        auds = dash.get("audio") or []
        if not vids or not auds:
            return None
        ff = self._tim_ffmpeg()
        if not ff:
            utils.logger.warning("[BilibiliCrawler] Có DASH nhưng KHÔNG thấy ffmpeg để ghép → lùi bản MP4 "
                                 "gộp sẵn (thường chỉ 720p). Đặt FFMPEG_BIN nếu muốn bản nét hơn.")
            return None
        v = max(vids, key=lambda x: ((x.get("height") or 0), (x.get("bandwidth") or 0)))
        a = max(auds, key=lambda x: (x.get("bandwidth") or 0))
        import tempfile, subprocess
        d = tempfile.mkdtemp(prefix="bilidash_")
        pv, pa, po = os.path.join(d, "v.m4s"), os.path.join(d, "a.m4s"), os.path.join(d, "o.mp4")
        try:
            cv = await self.bili_client.get_video_media(
                v.get("baseUrl") or v.get("base_url"),
                backup_urls=[u for u in (v.get("backupUrl") or v.get("backup_url") or []) if u])
            # 🔴 11/09/2026 — NÓI RA. Hai `return None` này trước đây CÂM HOÀN TOÀN, mà chúng nằm ĐÚNG
            #    sau dòng phần trăm cuối cùng ⇒ khách chỉ thấy "100% của 1MB — xong phần tải, đang xử lý
            #    tiếp…" rồi một lỗi lạ, không biết HÌNH hay TIẾNG mới là thứ tải hụt (ca khách 11/09).
            if not cv:
                print("LOG:✗ Tải HÌNH (luồng video tách rời) không xong — sẽ thử bản gộp sẵn.", flush=True)
                return None
            ca = await self.bili_client.get_video_media(
                a.get("baseUrl") or a.get("base_url"),
                backup_urls=[u for u in (a.get("backupUrl") or a.get("backup_url") or []) if u])
            if not ca:
                print("LOG:✗ Tải TIẾNG (luồng âm thanh tách rời) không xong — sẽ thử bản gộp sẵn.", flush=True)
                return None
            with open(pv, "wb") as _f:
                _f.write(cv)
            with open(pa, "wb") as _f:
                _f.write(ca)
            # 🔴 THẢ SỚM: `get_video_media` trả BYTES. Không thả thì cv+ca+bytes-file-đã-ghép cùng sống
            # một lúc — video 4K ~350MB ⇒ đỉnh RAM ~700MB+, trong khi đường `durl` cũ chỉ giữ MỘT khối.
            # Đã ghi ra đĩa rồi nên không cần giữ nữa.
            del cv, ca
            # 🔴 09/09/2026 — NÓI RA. Khâu ghép trước đây câm hoàn toàn, mà nó nằm ĐÚNG sau dòng % cuối
            #   ⇒ khách thấy thanh đứng ở 99% và tưởng treo (đo 09/09: 3,4s cho 462MB; video dài lâu hơn).
            #   `print("LOG:…")` đi thẳng vào nhánh `them_log` của `web_app._crawl_worker` — dòng
            #   `utils.logger` KHÔNG tới được UI. try RIÊNG: lỗi in mà rơi vào `except` của hàm này thì
            #   nó lùi bản gộp sẵn 720p — mất chất lượng vì một dòng log.
            try:
                print("LOG:🔗 Đã tải xong hình + tiếng — đang ghép lại thành 1 file…", flush=True)
            except Exception:
                pass
            r = subprocess.run([ff, "-y", "-v", "error", "-i", pv, "-i", pa,
                                "-c", "copy", "-movflags", "+faststart", po],
                               capture_output=True, timeout=900)
            if r.returncode != 0 or not os.path.isfile(po) or os.path.getsize(po) < 10000:
                utils.logger.warning("[BilibiliCrawler] Ghép DASH lỗi (%s) → lùi bản gộp sẵn."
                                     % (r.stderr or b"").decode("utf-8", "replace")[-160:])
                return None
            out = open(po, "rb").read()
            utils.logger.info("[BilibiliCrawler] DASH %sp — ghép xong %.1f MB (bản gộp sẵn thường chỉ 720p)."
                              % (v.get("height"), len(out) / 1048576))
            return out
        except Exception as e:
            utils.logger.warning("[BilibiliCrawler] Nhánh DASH hỏng (%s) → lùi bản gộp sẵn." % str(e)[:110])
            return None
        finally:
            import shutil as _sh
            _sh.rmtree(d, ignore_errors=True)

    async def get_all_creator_details(self, creator_url_list: List[str]):
        """
        creator_url_list: get details for creator from creator URL list
        """
        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Crawling the details of creators")
        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Parsing creator URLs...")

        creator_id_list = []
        for creator_url in creator_url_list:
            try:
                creator_info = parse_creator_info_from_url(creator_url)
                creator_id_list.append(int(creator_info.creator_id))
                utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] Parsed creator ID: {creator_info.creator_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[BilibiliCrawler.get_all_creator_details] Failed to parse creator URL: {e}")
                continue

        utils.logger.info(f"[BilibiliCrawler.get_all_creator_details] creator ids:{creator_id_list}")

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        try:
            for creator_id in creator_id_list:
                task = asyncio.create_task(self.get_creator_details(creator_id, semaphore), name=str(creator_id))
                task_list.append(task)
        except Exception as e:
            utils.logger.warning(f"[BilibiliCrawler.get_all_creator_details] error in the task list. The creator will not be included. {e}")

        await asyncio.gather(*task_list)

    async def get_creator_details(self, creator_id: int, semaphore: asyncio.Semaphore):
        """
        get details for creator id
        :param creator_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
            creator_info: Dict = {
                "id": creator_id,
                "name": creator_unhandled_info.get("name"),
                "sign": creator_unhandled_info.get("sign"),
                "avatar": creator_unhandled_info.get("face"),
            }
        await self.get_fans(creator_info, semaphore)
        await self.get_followings(creator_info, semaphore)
        await self.get_dynamics(creator_info, semaphore)

    async def get_fans(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get fans for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_fans] begin get creator_id: {creator_id} fans ...")
                await self.bili_client.get_creator_all_fans(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_fans,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_fans] get creator_id: {creator_id} fans error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_fans] may be been blocked, err:{e}")

    async def get_followings(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get followings for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_followings] begin get creator_id: {creator_id} followings ...")
                await self.bili_client.get_creator_all_followings(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_followings,
                    max_count=config.CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_followings] get creator_id: {creator_id} followings error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_followings] may be been blocked, err:{e}")

    async def get_dynamics(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """
        get dynamics for creator id
        :param creator_info:
        :param semaphore:
        :return:
        """
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                utils.logger.info(f"[BilibiliCrawler.get_dynamics] begin get creator_id: {creator_id} dynamics ...")
                await self.bili_client.get_creator_all_dynamics(
                    creator_info=creator_info,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    callback=bilibili_store.batch_update_bilibili_creator_dynamics,
                    max_count=config.CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES,
                )

            except DataFetchError as ex:
                utils.logger.error(f"[BilibiliCrawler.get_dynamics] get creator_id: {creator_id} dynamics error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_dynamics] may be been blocked, err:{e}")

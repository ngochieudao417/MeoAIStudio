# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
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

import os as _os  # ViralCrawl: cần cho env-override XHS_INTERNATIONAL bên dưới (import gốc ở cuối file)

# Basic configuration
PLATFORM = "dy"  # Platform, xhs | dy | ks | bili | wb | tieba | zhihu

# 是否使用海外版小红书 (rednote.com)
# 开启后 API 走 webapi.rednote.com，cookie 域使用 .rednote.com
# ViralCrawl: cho phép bật/tắt qua env MC_XHS_INTL (tool đặt theo nút gạt "Xiaohongshu quốc tế").
# Mặc định "0" -> bản Trung xiaohongshu.com (giữ nguyên hành vi cũ cho user TQ).
XHS_INTERNATIONAL = _os.environ.get("MC_XHS_INTL", "0") == "1"

# ViralCrawl: timeout (giây) cho request XHS — env MC_XHS_TIMEOUT. Mặc định 60 (giữ hành vi cũ).
# Tool hạ xuống ~25 để CẮT treo: feed/detail endpoint của xhs hay bị anti-bot chặn → request treo
# tới hết timeout; kèm retry lồng (get_note_by_id_from_html 3x × request 3x) → tới ~12 phút/note ở 60s.
try:
    XHS_API_TIMEOUT = int(_os.environ.get("MC_XHS_TIMEOUT", "60"))
except ValueError:
    XHS_API_TIMEOUT = 60

KEYWORDS = "编程副业,编程兼职"  # Keyword search configuration, separated by English commas
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
CRAWLER_TYPE = (
    "search"  # Crawling type, search (keyword search) | detail (post details) | creator (creator homepage data)
)
# Whether to enable IP proxy (ViralCrawl: env VC_PROXY để bật, default=False)
# ĐÃ TỪNG default=True ("cào nhanh 4x") — REVERT vì test THẬT lòi ra: CẢ 2 provider có sẵn
# (kuaidaili, wandouhttp) đều là dịch vụ TRẢ PHÍ/cần đăng ký API key (KDL_SECERT_ID/WANDOU_APP_KEY),
# KHÔNG khách nào có → get_proxy() raise Exception không bắt → CRASH CÀO 0 VIDEO MỌI KHÁCH mặc định.
# Không có provider miễn phí thật nào hoạt động trong code hiện tại. Giữ tắt mặc định (opt-in an toàn)
# cho tới khi có provider free thật + xử lý lỗi provider không giết cả crawl.
ENABLE_IP_PROXY = _os.environ.get("VC_PROXY", "false").lower() in ("true", "t", "1", "yes", "y")

# Number of proxy IP pools
IP_PROXY_POOL_COUNT = 2

# Proxy IP provider name (ViralCrawl: env VC_PROXY_PROVIDER — mặc định "static" để gắn proxy
# 1 khách nhu cầu cao chỉ cần set VC_STATIC_PROXY, khỏi động tới kuaidaili/wandou trả phí).
IP_PROXY_PROVIDER_NAME = _os.environ.get("VC_PROXY_PROVIDER", "static")  # kuaidaili | wandouhttp | static

# Static proxy (ViralCrawl: env VC_STATIC_PROXY — GẮN PROXY RIÊNG CHO 1 MÁY không phải sửa code/build.
# Máy khách cào nhiều: set 2 env (trong shortcut/MO-WEB.bat của MÁY ĐÓ):
#   VC_PROXY=true  +  VC_STATIC_PROXY=http://user:pass@host:port
# Máy khác KHÔNG set → VC_PROXY=false (proxy tắt) → KHÔNG ảnh hưởng. Proxy phải RESIDENTIAL/4G mới
# qua 风控 Douyin/Bili (datacenter/public/Tor bị chặn — đã verify). Format:
#   "http://host:port" hoặc "http://user:password@host:port"
STATIC_PROXY_URL = _os.environ.get("VC_STATIC_PROXY", "")

# GUARD chống tự-bắn-chân: bật proxy (VC_PROXY=true) + provider 'static' NHƯNG quên set VC_STATIC_PROXY
# → StaticProxyProvider.get_proxy() trả [] → proxy_ip_pool random.choice([]) → IndexError → CRASH cào
# 0 video (đúng lớp bug proxy default cũ). Thiếu URL → TẮT proxy (cào thẳng, an toàn) thay vì crash.
if ENABLE_IP_PROXY and IP_PROXY_PROVIDER_NAME == "static" and not STATIC_PROXY_URL:
    import sys as _sys
    print("[base_config] VC_PROXY bật nhưng thiếu VC_STATIC_PROXY — TẮT proxy, cào không proxy (tránh crash).",
          file=_sys.stderr)
    ENABLE_IP_PROXY = False

# Setting to True will not open the browser (headless browser)
# Setting False will open a browser
# If Xiaohongshu keeps scanning the code to log in but fails, open the browser and manually pass the sliding verification code.
# If Douyin keeps prompting failure, open the browser and see if mobile phone number verification appears after scanning the QR code to log in. If it does, manually go through it and try again.
HEADLESS = False

# Whether to save login status
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用 CDP 模式 - 使用用户本地的 Chrome/Edge 浏览器进行爬取，具有更好的反检测能力
# 开启后，会自动检测并启动用户的 Chrome/Edge 浏览器，通过 CDP 协议进行控制
# 该方式使用真实浏览器环境，包括用户的扩展、Cookie 和设置，大幅降低被风控检测的风险
# ViralCrawl: cho phép web_app/daemon bật CDP qua env (giữ browser persistent — chống 风控 tốt nhất cho Douyin)
ENABLE_CDP_MODE = _os.environ.get("MC_ENABLE_CDP", "0") == "1"

# CDP 调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = int(_os.environ.get("MC_CDP_PORT", "9222") or "9222")

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测 Chrome/Edge 的安装路径
# Windows 示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS 示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# 是否在 CDP 模式下启用无头模式
# 注意：即使设置为 True，某些反检测功能在无头模式下可能无法正常工作
CDP_HEADLESS = _os.environ.get("MC_CDP_HEADLESS", "0") == "1"

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 60

# 是否连接用户已打开的浏览器，而不是启动新的浏览器
# 开启后，程序会连接一个已经启用了远程调试的浏览器
# 用户需要在 Chrome 中开启远程调试：chrome://inspect/#remote-debugging
# 或者使用命令行参数启动 Chrome：--remote-debugging-port=9222
# 这种方式反检测效果最好，因为直接使用用户真实浏览器的所有 Cookie、扩展和浏览历史
CDP_CONNECT_EXISTING = _os.environ.get("MC_CDP_CONNECT_EXISTING", "0") == "1"

# 程序结束时是否自动关闭浏览器
# 设置为 False 可以保持浏览器运行，方便调试
AUTO_CLOSE_BROWSER = True

# Data saving type option configuration, supports: csv, db, json, jsonl, sqlite, excel, postgres. It is best to save to DB, with deduplication function.
SAVE_DATA_OPTION = "jsonl"  # csv or db or json or jsonl or sqlite or excel or postgres

# Data saving path, if not specified by default, it will be saved to the data folder.
# Patch reupo: đọc env MC_DATA_DIR (web_app/chay_tu_dong đặt = thư mục userData / user-chọn) để video
# cào + jsonl + ảnh lưu NGOÀI app-src → BỀN qua auto-update. Không có env (MediaCrawler gốc) = "" = cũ.
SAVE_DATA_PATH = _os.environ.get("MC_DATA_DIR", "")

# Browser file configuration cached by the user's browser
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# The number of pages to start crawling starts from the first page by default
START_PAGE = 1

# Control the number of crawled videos/posts
CRAWLER_MAX_NOTES_COUNT = 15

# Controlling the number of concurrent crawlers
# User chốt tăng 1→2 (chấp nhận đánh đổi rủi ro 风控 cao hơn để cào nhanh hơn).
MAX_CONCURRENCY_NUM = 2

# Whether to enable crawling media mode (including image or video resources), crawling media is not enabled by default
# Patch reupo: cho phép tắt qua env MC_GET_MEDIAS=0 để TÌM metadata (xem trước) mà KHÔNG tải media.
import os as _os
ENABLE_GET_MEIDAS = _os.environ.get("MC_GET_MEDIAS", "1") != "0"

# Whether to enable comment crawling mode. Comment crawling is enabled by default.
ENABLE_GET_COMMENTS = False

# Control the number of crawled first-level comments (single video/post)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# Whether to enable the mode of crawling second-level comments. By default, crawling of second-level comments is not enabled.
# If the old version of the project uses db, you need to refer to schema/tables.sql line 287 to add table fields.
ENABLE_GET_SUB_COMMENTS = False

# word cloud related
# Whether to enable generating comment word clouds
ENABLE_GET_WORDCLOUD = False
# Custom words and their groups
# Add rule: xx:yy where xx is a custom-added phrase, and yy is the group name to which the phrase xx is assigned.
CUSTOM_WORDS = {
    "零几": "年份",  # Recognize "zero points" as a whole
    "高频词": "专业术语",  # Example custom words
}

# Deactivate (disabled) word file path
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# Chinese font file path
FONT_PATH = "./docs/STZHONGS.TTF"

# Crawl interval (env VC_SLEEP_SEC override).
# ĐÃ TỪNG giảm 2→0.5s ("cào nhanh 4x", đi kèm proxy) — REVERT về 2s vì: (1) proxy đã tắt mặc định nên lý do
# giảm không còn; (2) tài liệu chính chủ + cộng đồng MediaCrawler khuyến nghị NGƯỢC LẠI — với Douyin/
# Bilibili phải giữ concurrent thấp + TĂNG sleep để né 风控/封号, khi dính risk-control thì GIẢM tần suất
# chứ không tăng. Sleep 0.5s (1/4 gốc) làm rủi ro block cao hơn — đồng phạm gây "blocked"/"voucher" khi
# test. SAU ĐÓ user chốt tăng MAX_CONCURRENCY_NUM 1→2 + hạ sleep 2→1s (chấp nhận đánh đổi rủi ro cao hơn
# 2 lần revert trước để cào nhanh hơn). Range [0.1, 10].
try:
    CRAWLER_MAX_SLEEP_SEC = float(_os.environ.get("VC_SLEEP_SEC", "1"))
    CRAWLER_MAX_SLEEP_SEC = max(0.1, min(10, CRAWLER_MAX_SLEEP_SEC))
except ValueError:
    CRAWLER_MAX_SLEEP_SEC = 1

# 是否禁用 SSL 证书验证。仅在使用企业代理、Burp Suite、mitmproxy 等会注入自签名证书的中间人代理时设为 True。
# 警告：禁用 SSL 验证将使所有流量暴露于中间人攻击风险，请勿在生产环境中开启。
DISABLE_SSL_VERIFY = False

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *

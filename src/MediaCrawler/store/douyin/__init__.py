# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/__init__.py
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
# @Time    : 2024/1/14 18:46
# @Desc    :
import os   # 🔴 THÊM 28/08: `_bit_rate_gears` đọc env DY_NE_H265. TRƯỚC ĐÓ `os` chỉ có mặt nhờ
            # ĂN KÉ `from ._store_impl import *` — ai thêm `__all__` vào đó là gãy NameError lúc
            # CHẠY, mà `py_compile` KHÔNG bắt được. Khai báo tường minh cho chắc.
from typing import List

import config
from var import source_keyword_var

from ._store_impl import *
from .douyin_store_media import *


class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "postgres": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement,
        "jsonl": DouyinJsonlStoreImplement,
        "sqlite": DouyinSqliteStoreImplement,
        "mongodb": DouyinMongoStoreImplement,
        "excel": DouyinExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = DouyinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[DouyinStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb or excel ...")
        return store_class()


def _extract_note_image_list(aweme_detail: Dict) -> List[str]:
    """
    Extract note image list

    Args:
        aweme_detail (Dict): Douyin content details

    Returns:
        List[str]: Note image list
    """
    images_res: List[str] = []
    images: List[Dict] = aweme_detail.get("images", [])

    if not images:
        return []

    for image in images:
        image_url_list = image.get("url_list", [])  # download_url_list has watermarked images, url_list has non-watermarked images
        if image_url_list:
            images_res.append(image_url_list[-1])

    return images_res


def _extract_comment_image_list(comment_item: Dict) -> List[str]:
    """
    Extract comment image list

    Args:
        comment_item (Dict): Douyin comment

    Returns:
        List[str]: Comment image list
    """
    images_res: List[str] = []
    image_list: List[Dict] = comment_item.get("image_list", [])

    if not image_list:
        return []

    for image in image_list:
        image_url_list = image.get("origin_url", {}).get("url_list", [])
        if image_url_list and len(image_url_list) > 1:
            images_res.append(image_url_list[1])

    return images_res


def _extract_content_cover_url(aweme_detail: Dict) -> str:
    """
    Extract video cover URL

    Args:
        aweme_detail (Dict): Douyin content details

    Returns:
        str: Video cover URL
    """
    res_cover_url = ""

    video_item = aweme_detail.get("video", {})
    raw_cover_url_list = (video_item.get("raw_cover", {}) or video_item.get("origin_cover", {})).get("url_list", [])
    if raw_cover_url_list and len(raw_cover_url_list) > 1:
        res_cover_url = raw_cover_url_list[1]

    return res_cover_url


def _bit_rate_gears(video_item: Dict) -> List:
    """Các gear trong `video.bit_rate[]`, sắp ƯU TIÊN: H.264 trước (né HEVC-đen — xem xhs), rồi bitrate GIẢM DẦN.
    Mỗi phần tử = (bitrate:int, is_h265:bool, url_list:List[str], height:int). [] nếu không có gear hợp lệ.

    🔴 (23/08/2026) VÌ SAO: `play_addr` mặc định thường là gear THẤP/`adapt_lowest` ⇒ khách tải về "10s đầu nét
    rồi nhòe" (đo thật: 1080p 3 Mbps SSIM 0.9737 vs 12 Mbps 0.9915; render KHÔNG bù lại được chi tiết nguồn đã
    mất). Douyin CÓ lộ nhiều gear qua web (không cần app/trả phí) — chọn gear bitrate cao nhất là chữa được."""
    gears = []
    for g in (video_item.get("bit_rate") or []):
        if not isinstance(g, dict):
            continue
        pa = g.get("play_addr") or {}
        urls = [u for u in (pa.get("url_list") or []) if isinstance(u, str) and u.startswith("http")]
        if not urls:
            continue
        try:
            br = int(g.get("bit_rate") or 0)
        except (TypeError, ValueError):
            br = 0
        is265 = bool(g.get("is_h265") or g.get("is_bytevc1"))
        # chiều cao để XẾP THEO ĐỘ PHÂN GIẢI (xem khối lý do ở `gears.sort` bên dưới)
        try:
            _h = int(pa.get("height") or g.get("height") or 0)
        except (TypeError, ValueError):
            _h = 0
        gears.append((br, is265, urls, _h))
    # 🔵 XẾP THEO ĐỘ PHÂN GIẢI (28/08/2026 — chủ dự án: "làm thế nào để tăng độ phân giải video đầu ra").
    #
    # LUẬT CŨ `(x[1], -x[0])` đẩy **toàn bộ H.264 lên trước mọi H.265**, và trong nhóm chỉ so BITRATE.
    # Hai chỗ hụt, đều ĐO THẬT 28/08 trên aweme lấy từ trang chủ Douyin:
    #   (a) BỎ QUA bậc cao hơn — video "自制96分钟大型传统仙侠电影":
    #         H.265 cao nhất **2560×1440** (1.907 kbps)  ·  H.264 cao nhất chỉ 1080p (1.579 kbps)
    #       ⇒ luật cũ lấy 1080p, mất hẳn 1440p.
    #   (b) So BITRATE chứ không so ĐỘ PHÂN GIẢI — cùng video đó, danh sách H.264 là
    #         1080p@1579 · 1080p@1521 · 576p@1354 · 720p@1231
    #       may mà 1080p cũng bitrate cao nhất; chỉ cần một video có 720p bitrate cao hơn 1080p là chọn nhầm.
    #
    # LUẬT MỚI: (1) độ phân giải GIẢM DẦN → (2) cùng độ phân giải thì H.264 TRƯỚC → (3) bitrate giảm dần.
    # Vế (2) giữ nguyên tinh thần chống "HEVC đen hình": chỉ rước H.265 về khi nó THẬT SỰ nét hơn,
    # còn ngang nhau (đo được: có video H.265 và H.264 đều 1080p) thì vẫn lấy H.264 — miễn phí.
    #
    # ⚠ H.265 VẪN PHẢI CHỮA — ĐÃ ĐO 30/08/2026, đừng tin lập luận cũ:
    # Bản render giao khách xuất H.264 nên KHÔNG sao. Nhưng file THÔ thì khách xem ngay
    # **trong chính app** (lưới video + trình xem trước) — câu "chỉ xảy ra với VLC/trình
    # duyệt" là SAI. Đo bằng chính Electron 31 của app, 3 clip h264/hvc1/hev1:
    #       có GPU  → h264 OK · hvc1 OK   · hev1 OK
    #       tắt GPU → h264 OK · hvc1 LỖI · hev1 LỖI   (code=4)
    # Chromium KHÔNG có bộ giải HEVC bằng phần mềm — chỉ đi qua phần cứng. Máy khách
    # thiếu bộ giải ⇒ **hình đen, tiếng vẫn chạy** (AAC giải mềm) — đúng triệu chứng
    # khách báo. ⇒ KHÔNG có cờ Electron nào sửa được; phải sửa ở FILE.
    # Hai lớp phòng thủ:
    #   (1) NÉ H.265 ngay lúc chọn gear — MẶC ĐỊNH, miễn phí, không mất chất (xem ngay dưới);
    #   (2) `tools/sua_hevc.py` chuyển H.265→H.264 sau khi tải — lưới cứu cho ca CHỈ có gear
    #       H.265, và cho Bilibili/XHS (hai nơi đó không có nhiều gear để chọn).
    # 🟢 MẶC ĐỊNH 30/08/2026 = NÉ H.265 (chủ dự án chốt: miễn phí, không mất chất).
    #   ↳ KHÔNG dùng lại luật cũ `(x[1], -x[0])`: nó bỏ qua `height` nên gặp video có 720p bitrate
    #     cao hơn 1080p là chọn nhầm 720p (lỗi (b) ghi ở trên). Luật mới giữ nguyên tinh thần
    #     né-H.265 nhưng xếp ĐÚNG: H.264 trước → độ phân giải giảm dần → bitrate giảm dần.
    #   ↳ Chỉ có gear H.265 (không có H.264 nào) ⇒ vẫn lấy H.265 nét nhất, rồi `tools/sua_hevc.py`
    #     chuyển về H.264 sau khi tải — khách vẫn xem được.
    #   ↳ Muốn trần độ phân giải cao nhất (chấp nhận rước H.265 + tốn chuyển mã): DY_NE_H265=0.
    _ne265 = os.environ.get("DY_NE_H265", "1") != "0"
    if _ne265:
        gears.sort(key=lambda x: (x[1], -(x[3] or 0), -x[0]))
    else:
        gears.sort(key=lambda x: (-(x[3] or 0), x[1], -x[0]))
    return gears


def _extract_video_download_url(aweme_detail: Dict) -> str:
    """
    Extract video download URL

    Args:
        aweme_detail (Dict): Douyin video

    Returns:
        str: Video download URL
    """
    video_item = aweme_detail.get("video", {})
    # 🔴 (23/08/2026) ƯU TIÊN gear bitrate CAO NHẤT (video.bit_rate[]) — chữa "10s nét rồi nhòe" do tải nhầm
    # bản bitrate thấp. Không có gear → lùi logic cũ (play_addr_h264/256/play_addr).
    _gears = _bit_rate_gears(video_item)
    if _gears:
        return _gears[0][2][-1]
    url_h264_list = video_item.get("play_addr_h264", {}).get("url_list", [])
    url_256_list = video_item.get("play_addr_256", {}).get("url_list", [])
    url_list = video_item.get("play_addr", {}).get("url_list", [])
    actual_url_list = url_h264_list or url_256_list or url_list
    if not actual_url_list or len(actual_url_list) < 2:
        return ""
    return actual_url_list[-1]


def _extract_video_download_url_list(aweme_detail: Dict) -> List[str]:
    """Lấy TẤT CẢ link tải dự phòng (nhiều CDN) để thử lần lượt khi 1 link bị 403.
    🔴 (23/08/2026) Đưa gear bitrate CAO (video.bit_rate[]) LÊN ĐẦU danh sách thử; play_addr cũ giữ làm dự phòng
    nếu gear 403. Nhờ vậy vẫn tải được (không mất video) mà ưu tiên bản nét."""
    video_item = aweme_detail.get("video", {})
    urls = []
    for _br, _is265, _gurls, _h in _bit_rate_gears(video_item):
        for u in _gurls:
            if u not in urls:
                urls.append(u)
    for key in ("play_addr_h264", "play_addr_256", "play_addr"):
        for u in video_item.get(key, {}).get("url_list", []) or []:
            if u and u.startswith("http") and u not in urls:
                urls.append(u)
    return urls


def _extract_music_download_url(aweme_detail: Dict) -> str:
    """
    Extract music download URL

    Args:
        aweme_detail (Dict): Douyin video

    Returns:
        str: Music download URL
    """
    music_item = aweme_detail.get("music", {})
    play_url = music_item.get("play_url", {})
    music_url = play_url.get("uri", "")
    return music_url


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type")),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "create_time": aweme_item.get("create_time"),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar_thumb", {}).get("url_list", [""])[0],
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "ip_location": aweme_item.get("ip_label", ""),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}",
        "cover_url": _extract_content_cover_url(aweme_item),
        "video_download_url": _extract_video_download_url(aweme_item),
        "music_download_url": _extract_music_download_url(aweme_item),
        "note_download_url": ",".join(_extract_note_image_list(aweme_item)),
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.douyin.update_douyin_aweme] douyin aweme id:{aweme_id}, title:{save_content_item.get('title')}")
    await DouyinStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        utils.logger.error(f"[store.douyin.update_dy_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    parent_comment_id = comment_item.get("reply_id", "0")
    avatar_info = (user_info.get("avatar_medium", {}) or user_info.get("avatar_300x300", {}) or user_info.get("avatar_168x168", {}) or user_info.get("avatar_thumb", {}) or {})
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_label", ""),
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "user_id": user_info.get("uid"),
        "sec_uid": user_info.get("sec_uid"),
        "short_user_id": user_info.get("short_id"),
        "user_unique_id": user_info.get("unique_id"),
        "user_signature": user_info.get("signature"),
        "nickname": user_info.get("nickname"),
        "avatar": avatar_info.get("url_list", [""])[0],
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),
        "like_count": (comment_item.get("digg_count") if comment_item.get("digg_count") else 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "parent_comment_id": parent_comment_id,
        "pictures": ",".join(_extract_comment_image_list(comment_item)),
    }
    utils.logger.info(f"[store.douyin.update_dy_aweme_comment] douyin aweme comment: {comment_id}, content: {save_comment_item.get('content')}")

    await DouyinStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def save_creator(user_id: str, creator: Dict):
    user_info = creator.get("user", {})
    gender_map = {0: "Unknown", 1: "Male", 2: "Female"}
    avatar_uri = user_info.get("avatar_300x300", {}).get("uri")
    local_db_item = {
        "user_id": user_id,
        "nickname": user_info.get("nickname"),
        "gender": gender_map.get(user_info.get("gender"), "Unknown"),
        "avatar": f"https://p3-pc.douyinpic.com/img/{avatar_uri}" + r"~c5_300x300.jpeg?from=2956013662",
        "desc": user_info.get("signature"),
        "ip_location": user_info.get("ip_location"),
        "follows": user_info.get("following_count", 0),
        "fans": user_info.get("max_follower_count", 0),
        "interaction": user_info.get("total_favorited", 0),
        "videos_count": user_info.get("aweme_count", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.douyin.save_creator] creator:{local_db_item}")
    await DouyinStoreFactory.create_store().store_creator(local_db_item)


async def update_dy_aweme_image(aweme_id, pic_content, extension_file_name, sub_dir=""):
    """
    Update Douyin note image
    Args:
        aweme_id:
        pic_content:
        extension_file_name:
        sub_dir: thư mục con

    Returns:

    """

    await DouYinImage().store_image({"aweme_id": aweme_id, "pic_content": pic_content, "extension_file_name": extension_file_name, "sub_dir": sub_dir})


async def update_dy_aweme_video(aweme_id, video_content, extension_file_name, sub_dir=""):
    """
    Update Douyin short video
    Args:
        aweme_id:
        video_content:
        extension_file_name:
        sub_dir: thư mục con (vd tu-khoa/<kw>, kenh/<ten>, link)

    Returns:

    """

    await DouYinVideo().store_video({"aweme_id": aweme_id, "video_content": video_content, "extension_file_name": extension_file_name, "sub_dir": sub_dir})

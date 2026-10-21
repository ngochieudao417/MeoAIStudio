# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/douyin_store_media.py
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

import os
import pathlib
import re as _re
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
import config


# 🔴 10/08/2026 — MẤT VIDEO vì đường dẫn vượt MAX_PATH 260 của Windows. ĐO THẬT trên kênh 旧梦留声机:
# cùng một lượt cào, cùng thư mục, 2 video — cái 243 ký tự TẢI ĐƯỢC, cái 264 ký tự CHẾT với
# `[Errno 2] No such file or directory` ở bước ghi '.part', rồi crawler CHẠY TIẾP như không có gì.
# Khách thấy "cào xong" nhưng thiếu video, không dòng nào nói vì sao.
# Dễ nổ hơn tưởng: app DỊCH tiêu đề Trung → Việt để đặt tên, bản Việt thường DÀI HƠN bản gốc.
# Chủ dự án chốt: cắt ngắn tên là chấp nhận được (mất vài chữ tiêu đề còn hơn mất cả video).
# ⚠ PHẢI GIỮ NGUYÊN đuôi `_<aweme_id>.<ext>`: cơ chế dedup dùng glob '*_<id>.mp4' (xem save_video)
#   — cắt trúng phần id là mọi lần cào sau tải lại từ đầu.
_GIOI_HAN_DUONG_DAN = 250   # 260 trừ chỗ cho hậu tố '.part' (5) + biên an toàn


def _cat_cho_vua(duong_dan: str) -> str:
    """Cắt phần TIÊU ĐỀ để đường dẫn nằm dưới MAX_PATH. Đủ ngắn rồi thì trả nguyên."""
    if len(duong_dan) <= _GIOI_HAN_DUONG_DAN:
        return duong_dan
    thu_muc, _, ten = duong_dan.rpartition("/")
    if not thu_muc:
        return duong_dan
    m = _re.search(r"(_\d+\.[A-Za-z0-9]+)$", ten)          # '_7629803455813243043.mp4'
    duoi = m.group(1) if m else ("." + ten.rsplit(".", 1)[-1] if "." in ten else "")
    dau = ten[: len(ten) - len(duoi)]
    con_lai = _GIOI_HAN_DUONG_DAN - len(thu_muc) - 1 - len(duoi)
    dau = dau[:con_lai].rstrip(" .-_") if con_lai > 0 else ""   # thư mục đã quá dài → chỉ còn id
    return "%s/%s%s" % (thu_muc, dau, duoi)


class DouYinImage(AbstractStoreImage):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.image_store_path = f"{config.SAVE_DATA_PATH}/douyin/images"
        else:
            self.image_store_path = "data/douyin/images"

    async def store_image(self, image_content_item: Dict):
        """
        store content

        Args:
            image_content_item:

        Returns:

        """
        await self.save_image(image_content_item.get("aweme_id"), image_content_item.get("pic_content"), image_content_item.get("extension_file_name"), image_content_item.get("sub_dir", ""))

    def make_save_file_name(self, aweme_id: str, extension_file_name: str, sub_dir: str = "") -> str:
        """
        make save file name by store type

        Args:
            aweme_id: aweme id
            extension_file_name: image filename with extension
            sub_dir: thư mục con tùy chọn

        Returns:

        """
        if sub_dir:
            return _cat_cho_vua(f"{self.image_store_path}/{sub_dir}/{extension_file_name}")
        return _cat_cho_vua(f"{self.image_store_path}/{aweme_id}/{extension_file_name}")

    async def save_image(self, aweme_id: str, pic_content: str, extension_file_name, sub_dir: str = ""):
        """
        save image to local

        Args:
            aweme_id: aweme id
            pic_content: image content
            extension_file_name: image filename with extension
            sub_dir: thư mục con tùy chọn

        Returns:

        """
        save_file_name = self.make_save_file_name(aweme_id, extension_file_name, sub_dir)
        pathlib.Path(save_file_name).parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[DouYinImageStoreImplement.save_image] save image {save_file_name} success ...")


class DouYinVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/douyin/videos"
        else:
            self.video_store_path = "data/douyin/videos"

    async def store_video(self, video_content_item: Dict):
        """
        store content

        Args:
            video_content_item:

        Returns:

        """
        await self.save_video(video_content_item.get("aweme_id"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"), video_content_item.get("sub_dir", ""))

    def make_save_file_name(self, aweme_id: str, extension_file_name: str, sub_dir: str = "") -> str:
        """
        make save file name by store type

        Args:
            aweme_id: aweme id
            extension_file_name: video filename with extension
            sub_dir: thư mục con tùy chọn (tu-khoa/<kw>, kenh/<ten>, link)

        Returns:

        """
        if sub_dir:
            return _cat_cho_vua(f"{self.video_store_path}/{sub_dir}/{extension_file_name}")
        return _cat_cho_vua(f"{self.video_store_path}/{aweme_id}/{extension_file_name}")

    async def save_video(self, aweme_id: str, video_content: str, extension_file_name, sub_dir: str = ""):
        """
        save video to local

        Args:
            aweme_id: aweme id
            video_content: video content
            extension_file_name: video filename with extension
            sub_dir: thư mục con tùy chọn

        Returns:

        """
        # 🔴 04/09/2026 — CHẶN LƯU TẬP TRẢ PHÍ ĐÃ MÃ HOÁ (CENC). Ca khách thật (DESKTOP-DVK6UNM):
        #   cào một bộ phim ngắn trả phí ⇒ **88 file ~5-6MB, dài ~1 phút, KHÔNG XEM ĐƯỢC**, mà app vẫn
        #   báo "thành công" đủ 88 lần. Khách mất băng thông, thư viện đầy rác, rồi còn đem đi render.
        #   Soi cấu trúc MP4 của chính mấy file đó (máy khách, 04/09):
        #       hộp: enca, encv, senc, saio, saiz, sbgp, sgpd   ← chữ ký CENC đầy đủ
        #       ffprobe đọc được metadata nhưng giải mã HỎNG: "error while decoding MB 0 0"
        #   Đối chứng CÙNG THƯ MỤC: tập MIỄN PHÍ (45-57MB, 4-5 phút) chỉ có `avc1`/`mp4a`, xem tốt.
        # ⚠ MUA RỒI CŨNG KHÔNG CỨU ĐƯỢC: khoá giải mã KHÔNG nằm trong file, Douyin chỉ cấp cho trình
        #   phát của họ. Quyền mua = quyền XEM TRONG APP, không phải quyền tải bản đã giải mã.
        #   ⇒ Việc đúng là NÓI THẲNG rồi bỏ qua, chứ không phải lưu rác rồi báo thành công.
        # Đòi ÍT NHẤT HAI dấu (enca/encv VÀ senc/sinf/pssh): một chuỗi 4 byte đơn lẻ hoàn toàn có thể
        # trùng ngẫu nhiên trong dữ liệu nén — hai dấu cùng lúc thì không.
        # Chỉ quét ĐẦU file: Douyin đặt `moov` ở đầu (faststart), quét cả file 500MB là phí công.
        # Giữ hành vi cũ: DY_LUU_DRM=1.
        try:
            _dau = bytes(video_content[:4 * 1024 * 1024])
            _ma = ((b"encv" in _dau or b"enca" in _dau)
                   and (b"senc" in _dau or b"sinf" in _dau or b"pssh" in _dau))
        except Exception:
            _ma = False
        if _ma and os.environ.get("DY_LUU_DRM", "0") != "1":
            print("LOG:🔒 BỎ QUA video %s — đây là TẬP TRẢ PHÍ được Douyin mã hoá (DRM). Tải về cũng "
                  "KHÔNG xem được: khoá giải mã chỉ cấp cho ứng dụng Douyin, không nằm trong file. "
                  "Mua rồi thì xem trực tiếp trong app Douyin. Tập miễn phí vẫn tải bình thường."
                  % aweme_id, flush=True)
            utils.logger.warning(
                f"[DouYinVideoStoreImplement.save_video] {aweme_id}: CENC/DRM -> khong luu")
            return

        save_file_name = self.make_save_file_name(aweme_id, extension_file_name, sub_dir)
        pathlib.Path(save_file_name).parent.mkdir(parents=True, exist_ok=True)
        # GHI ATOMIC: .part → replace. Kill giữa write chỉ để lại '.part' (KHÔNG khớp glob '*_<id>.mp4' dedup →
        # không bị coi "đã tải" oan); lần cào sau ghi đè. Chỉ khi write XONG mới đổi sang tên chính thức → không
        # bao giờ để file DỞ mang tên thật → hết cảnh dedup skip vĩnh viễn file truncate.
        tmp_name = save_file_name + ".part"
        async with aiofiles.open(tmp_name, 'wb') as f:
            await f.write(video_content)
        pathlib.Path(tmp_name).replace(save_file_name)
        # H.265 -> H.264 (30/08/2026 — khach: "co cai mo len chi nghe duoc audio thoi").
        # Ban va 28/08 doi luat chon gear sang UU TIEN DO PHAN GIAI => Douyin nay tra ve bac H.265
        # 2560x1440 (H.264 cao nhat chi 1080p). Net hon that, nhung Chromium/Electron cua app va nhieu
        # may khach KHONG decode duoc H.265 => thumbnail + preview ra KHUNG DEN, chi co tieng.
        # File van DUNG va ffmpeg render van doc duoc — nhung khach KHONG XEM DUOC truoc khi render.
        # Chay trong THREAD: transcode ton hang chuc giay, de thang trong coroutine la chan ca vong lap
        # su kien => moi luot tai khac dung hinh theo.
        # Moi nhanh hong deu GIU FILE GOC (xem tools/sua_hevc.py). Tat: SUA_HEVC=0.
        try:
            import asyncio as _aio
            from tools import sua_hevc as _sh
            await _aio.to_thread(_sh.sua, save_file_name, utils.logger.info)
        except Exception as _e_hevc:
            utils.logger.warning(f"[DouYinVideoStoreImplement.save_video] bo qua buoc H.265->H.264: {_e_hevc}")
        utils.logger.info(f"[DouYinVideoStoreImplement.save_video] save video {save_file_name} success ...")

# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/bilibili/bilibilli_store_media.py
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
# @Author  : helloteemo
# @Time    : 2024/7/12 20:01
# @Desc    : Bilibili media storage
import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
import config


class BilibiliVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/bili/videos"
        else:
            self.video_store_path = "data/bili/videos"

    async def store_video(self, video_content_item: Dict):
        """
        store content

        Args:
            video_content_item:

        Returns:

        """
        await self.save_video(video_content_item.get("aid"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"), video_content_item.get("sub_dir", ""))

    def make_save_file_name(self, aid: str, extension_file_name: str, sub_dir: str = "") -> str:
        """
        make save file name by store type

        Args:
            aid: aid
            extension_file_name: video filename with extension
            sub_dir: thư mục con tùy chọn (tu-khoa/<kw>, kenh/<tên>, link) — chia thư mục như Douyin

        Returns:

        """
        if sub_dir:
            return f"{self.video_store_path}/{sub_dir}/{extension_file_name}"
        return f"{self.video_store_path}/{aid}/{extension_file_name}"

    async def save_video(self, aid: int, video_content: str, extension_file_name="mp4", sub_dir: str = ""):
        """
        save video to local

        Args:
            aid: aid
            video_content: video content
            extension_file_name: video filename with extension
            sub_dir: thư mục con tùy chọn

        Returns:

        """
        save_file_name = self.make_save_file_name(str(aid), extension_file_name, sub_dir)
        pathlib.Path(save_file_name).parent.mkdir(parents=True, exist_ok=True)
        # GHI ATOMIC: .part → replace (xem giải thích ở douyin_store_media.save_video) → không để file DỞ mang
        # tên chính thức khi kill giữa write → hết cảnh dedup skip vĩnh viễn file truncate.
        # 🔴 09/09/2026 — NÓI RA. Đây là khe CÂM lớn nhất còn lại sau khi vá 2 chỗ kia: đo thật
        #   09/09 trên video 462MB, từ "ghép xong" tới "save video success" mất **16,5 giây** không
        #   một dòng log (nạp cả file vào RAM ở `core._tai_dash_bili` rồi ghi lại ra đĩa). Video 4K dài
        #   thì khe này tính bằng phút — đúng chỗ khách nhìn thanh 100% mà tưởng treo.
        try:
            print("LOG:💾 Đang ghi video ra đĩa (%.0fMB)…" % (len(video_content or b"") / 1048576.0),
                  flush=True)
        except Exception:
            pass
        tmp_name = save_file_name + ".part"
        async with aiofiles.open(tmp_name, 'wb') as f:
            await f.write(video_content)
        pathlib.Path(tmp_name).replace(save_file_name)
        # H.265 -> H.264: cung ly do voi Douyin (xem tools/sua_hevc.py). Rieng Bilibili con mot nguon
        # H.265 nua: ban va DASH 28/08 xin `fnval=4048` (gom 4K/HDR/Dolby) roi chon luong CAO NHAT —
        # ma HDR/Dolby tren Bilibili DEU la HEVC. Net hon nhung app/VLC may khach co the den hinh.
        # Chay trong THREAD de khong chan vong lap su kien. Hong -> giu file goc. Tat: SUA_HEVC=0.
        try:
            import asyncio as _aio
            from tools import sua_hevc as _sh
            await _aio.to_thread(_sh.sua, save_file_name, utils.logger.info)
        except Exception as _e_hevc:
            utils.logger.warning(f"[BilibiliVideo] bo qua buoc H.265->H.264: {_e_hevc}")
        utils.logger.info(f"[BilibiliVideoImplement.save_video] save video {save_file_name} success ...")

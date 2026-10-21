# -*- coding: utf-8 -*-
"""HEVC/H.265 -> H.264: video tải về mở ra ĐEN HÌNH, chỉ nghe được tiếng.

🔴 VÌ SAO CẦN (30/08/2026 — khách: *"tải video về có cái được, có cái mở lên chỉ nghe đc audio thôi"*):
Chromium/Electron (app dùng để hiện thumbnail + phát preview) và nhiều máy khách KHÔNG decode được
H.265/HEVC ⇒ khung ĐEN + chỉ có tiếng. File tải ĐÚNG và ffmpeg render vẫn đọc được — chỉ là **khách
không xem được** trước khi render, nên tưởng tải hỏng.

⚠ VÌ SAO GIỜ MỚI GẶP NHIỀU: bản vá 28/08 cho `store/douyin/__init__.py` đổi luật chọn gear sang **ưu
tiên ĐỘ PHÂN GIẢI** (trước đó ép H.264 trước) — đo thật thì Douyin có bậc H.265 **2560×1440** trong khi
H.264 cao nhất chỉ 1080p. Nét hơn thật, nhưng đổi lại là codec máy khách không mở nổi. Đây là cái giá
của bản vá đó, và đây là chỗ trả giá.

THIẾT KẾ — KHÔNG BAO GIỜ ĐƯỢC LÀM MẤT VIDEO:
· không probe được  -> giữ nguyên file (không đoán)
· không phải hevc/vvc -> giữ nguyên (H.264 khỏi đụng)
· không tìm thấy ffmpeg -> giữ nguyên + log rõ
· transcode lỗi/quá giờ -> giữ nguyên file GỐC, xoá file tạm
Mọi nhánh đều trả về không-ném-lỗi: đây là bước LÀM ĐẸP, hỏng nó KHÔNG được phá lượt cào.

Tắt: env `SUA_HEVC=0`. Ép CPU (máy NVENC lỗi): `SUA_HEVC_CPU=1`.
"""
import os
import shutil
import subprocess

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_CODEC_DEN = ("hevc", "vvc", "hev1", "hvc1")     # bytevc1 = HEVC, bytevc2 = VVC (H.266)


def _bin(ten):
    """ffmpeg/ffprobe: env trước (bản đóng gói theo app), rồi PATH."""
    for c in (os.environ.get(ten.upper() + "_BIN"), os.environ.get("FFMPEG_PATH") if ten == "ffmpeg" else None):
        if c and os.path.isfile(c):
            return c
    return shutil.which(ten) or ten


def _thoi_luong(path):
    """Thoi luong (giay) cua LUONG HINH. Khong doc duoc -> None (ben goi phai coi la THAT BAI)."""
    try:
        r = subprocess.run([_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=60, creationflags=_NO_WIN)
        return float((r.stdout or "").strip().splitlines()[0])
    except Exception:
        return None


def can_sua(path):
    """Codec của file có thuộc nhóm KHÔNG xem được không. Không probe được -> False (giữ nguyên)."""
    try:
        r = subprocess.run([_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=30, creationflags=_NO_WIN)
        return (r.stdout or "").strip().lower() in _CODEC_DEN
    except Exception:
        return False


def sua(path, log=None):
    """Trả True nếu ĐÃ đổi sang H.264; False nếu giữ nguyên (mọi lý do). KHÔNG bao giờ ném."""
    _log = log or (lambda m: None)
    if os.environ.get("SUA_HEVC") == "0" or not os.path.isfile(path):
        return False
    try:
        if not can_sua(path):
            return False
        ff = _bin("ffmpeg")
        if not (os.path.isfile(ff) or shutil.which("ffmpeg")):
            _log("  ↳ video H.265 nhưng KHÔNG thấy ffmpeg → giữ nguyên (app có thể hiện khung đen).")
            return False
        goc_gs = _thoi_luong(path)
        if not goc_gs:
            _log("  ↳ khong do duoc thoi luong ban goc -> GIU NGUYEN (khong dam de).")
            return False
        # 🔴 duoi .tmp (khong phai .mp4): manh sot sau taskkill KHONG lot qua _la_video.
        #    Duoi la nen phai chi dinh muxer bang -f mp4.
        # 🔴 09/09/2026 — NÓI RA TRƯỚC KHI CHẠY (chủ dự án: *"sao cào video về bị treo ở 99%"*).
        #   Khâu này MÃ HOÁ LẠI TOÀN BỘ video mà trước đây không in gì cho tới lúc xong ⇒ màn hình câm.
        #   ĐO THẬT trên máy dev (h264_nvenc p4 cq23, đúng lệnh dưới): 104,8s cho video 863s = **0,12×
        #   thời lượng** ⇒ video 30 phút ~3,6 phút, 60 phút ~7,3 phút ĐỨNG IM ở 99%.
        #   Hệ số 0,12 là CẬN DƯỚI: phép đo giải mã H.264, còn ở đây là HEVC (chậm hơn), và máy không có
        #   NVENC phải lùi `libx264 veryfast` nên lâu hơn nhiều — nên câu chữ nói "ước", không hứa chắc.
        #   `print("LOG:...")` chứ không `_log`: `_log` là `utils.logger.info`, KHÔNG tới được UI
        #   (`web_app._crawl_worker` chỉ có nhánh riêng cho tiền tố `LOG:`).
        #   try RIÊNG — thân hàm này bọc `except Exception: pass`, một `print` lỗi mã hoá sẽ nuốt luôn
        #   cả bước đổi codec (memory `cau-log-song-chung-try-voi-logic`).
        try:
            _uoc = goc_gs * 0.12
            print("LOG:🎞 Video tải về là H.265 — đang đổi sang H.264 để app/VLC xem được "
                  "(video %.0f phút, ước ~%s). Thanh tiến độ đứng yên lúc này là BÌNH THƯỜNG, "
                  "đừng bấm Dừng."
                  % (goc_gs / 60.0,
                     ("%.0f giây" % _uoc) if _uoc < 90 else ("%.0f phút" % (_uoc / 60.0))),
                  flush=True)
        except Exception:
            pass
        tmp = path + ".h264.tmp"
        # NVENC trước (nhanh), CPU sau. Máy NVENC lỗi driver -> ép CPU bằng SUA_HEVC_CPU=1.
        thu = (("libx264", ["-preset", "veryfast", "-crf", "20"]),) if os.environ.get("SUA_HEVC_CPU") == "1" else (
            ("h264_nvenc", ["-preset", "p4", "-cq", "23"]),
            ("libx264", ["-preset", "veryfast", "-crf", "20"]))
        for cv, extra in thu:
            try:
                r = subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                                    "-c:v", cv] + extra + ["-c:a", "copy", "-movflags", "+faststart", "-f", "mp4", tmp],
                                   capture_output=True, text=True, timeout=1800, creationflags=_NO_WIN)
                # 🔴 ffmpeg THOAT 0 khi gap loi giai ma giua file - no chi dung roi dong file.
                #    Ba cong cu (rc==0 - co file - >10KB) deu LOT => video 60' bi de thanh 3'.
                #    Bat buoc so THOI LUONG voi ban goc truoc khi dam de.
                if r.returncode == 0 and os.path.isfile(tmp) and os.path.getsize(tmp) > 10000:
                    moi_gs = _thoi_luong(tmp)
                    if not moi_gs or moi_gs < goc_gs * 0.99:
                        _log("  ↳ %s ra file CUT (%s / %.1fs) -> BO, giu ban goc."
                             % (cv, ("%.1fs" % moi_gs) if moi_gs else "khong doc duoc", goc_gs))
                        continue
                    os.replace(tmp, path)
                    _log("  ↳ chuyển H.265 → H.264 (%s) để xem được trên app/VLC" % cv)
                    return True
            except Exception:
                pass
            finally:
                if os.path.isfile(tmp):
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
        _log("  ↳ (giữ bản H.265 — đổi sang H.264 thất bại; video KHÔNG mất)")
    except Exception:
        pass
    return False

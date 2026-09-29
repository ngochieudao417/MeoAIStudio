"""Tiện ích ffmpeg — lấy binary ffmpeg, chạy lệnh, đo thời lượng, chọn encoder GPU."""
from __future__ import annotations
import os
import subprocess
import shutil
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    # 1. Try imageio_ffmpeg if available
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    # 2. Check shutil.which
    for name in ("ffmpeg.exe", "ffmpeg"):
        w = shutil.which(name)
        if w and os.path.exists(w):
            return w

    # 3. Check known paths in user profile or project
    known_paths = [
        r"C:\Users\Ngoc Hieu\Desktop\Career_path\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe",
        r"C:\Users\Ngoc Hieu\Desktop\Career_path - Copy\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for kp in known_paths:
        if os.path.exists(kp):
            return kp

    # 4. Fallback to xu_ly_video tim_exe if present
    try:
        from .xu_ly_video import tim_exe
        e = tim_exe("ffmpeg")
        if e and e != "ffmpeg" and os.path.exists(e):
            return e
    except Exception:
        pass

    return "ffmpeg"


@lru_cache(maxsize=1)
def ytdlp_ffmpeg() -> str:
    """yt-dlp cần file tên đúng 'ffmpeg.exe' để ghép video+audio; imageio đặt tên khác.
    Tạo 1 bản sao 'ffmpeg.exe' cạnh binary gốc (1 lần) rồi trả đường dẫn đó."""
    src = ffmpeg_exe()
    if not os.path.exists(src):
        return src
    dst = Path(src).with_name("ffmpeg.exe")
    if dst.exists():
        return str(dst)
    try:
        shutil.copy2(src, dst)
        return str(dst)
    except Exception:
        return src


def run(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Chạy ffmpeg với cờ mặc định gọn (ẩn banner, chỉ báo lỗi, tự ghi đè)."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    return subprocess.run(
        cmd, check=True,
        stdout=(subprocess.PIPE if capture else None),
        stderr=(subprocess.PIPE if capture else None),
        text=True,
    )


def _parse_ff_time(ts: str) -> float:
    """'00:01:23.456789' -> giây."""
    try:
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0


def run_progress(args: list[str], total_dur: float = 0.0, label: str = "ffmpeg",
                 stream=None) -> int:
    """Như run() nhưng vẽ thanh % theo tiến độ encode (out_time so với total_dur giây).

    total_dur <= 0 -> không biết thời lượng, chạy như run() thường (không có bar).
    """
    if not total_dur or total_dur <= 0:
        run(args)
        return 0
    try:
        from .progress import Bar
    except ImportError:
        from progress import Bar

    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
           "-progress", "pipe:1", "-nostats", *args]
    bar = Bar(total_dur, label=label, stream=stream, step=2)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, bufsize=1)
    try:
        for line in p.stdout:
            line = line.strip()
            if line.startswith("out_time="):
                sec = _parse_ff_time(line.split("=", 1)[1])
                bar.update(sec, f"{sec:.0f}/{total_dur:.0f}s")
            elif line == "progress=end":
                bar.update(total_dur, f"{total_dur:.0f}/{total_dur:.0f}s")
                break
        err = p.stderr.read() if p.stderr else ""
    finally:
        ret = p.wait()
    bar.finish()
    if ret != 0:
        tail = "\n".join((err or "").strip().splitlines()[-6:])
        raise RuntimeError(f"ffmpeg lỗi (mã {ret}):\n{tail}")
    return ret


def duration(path: str | Path) -> float:
    """Thời lượng (giây). Ưu tiên PyAV (đi kèm faster-whisper), fallback đọc stderr ffmpeg."""
    path = str(path)
    try:
        import av
        with av.open(path) as c:
            if c.duration is not None:
                return float(c.duration) / av.time_base
            for s in c.streams:
                if s.duration and s.time_base:
                    return float(s.duration * s.time_base)
    except Exception:
        pass
    try:
        p = subprocess.run(
            [ffmpeg_exe(), "-i", path], stderr=subprocess.PIPE, text=True
        )
        for line in p.stderr.splitlines():
            line = line.strip()
            if line.startswith("Duration:"):
                hms = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = hms.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0


def has_audio(path: str | Path) -> bool:
    try:
        import av
        with av.open(str(path)) as c:
            return any(s.type == "audio" for s in c.streams)
    except Exception:
        return True  # nghi ngờ -> coi như có, để pipeline tự xử


def _test_encoder(enc: str) -> bool:
    try:
        r = subprocess.run(
            [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "color=s=64x64:d=0.1", "-c:v", enc, "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        return r.returncode == 0
    except Exception:
        return False


@lru_cache(maxsize=1)
def best_h264() -> str:
    """Encoder H.264 tốt nhất máy có: NVENC (NVIDIA) > QSV (Intel) > AMF (AMD) > libx264 (CPU)."""
    if os.environ.get("VTOOL_FORCE_CPU"):
        return "libx264"
    for enc in ("h264_nvenc", "h264_qsv", "h264_amf"):
        if _test_encoder(enc):
            return enc
    return "libx264"


def video_encoder_args(quality: int = 22, pix_fmt: str | None = "yuv420p") -> list[str]:
    """Cờ encode video theo encoder tốt nhất (tự dùng GPU nếu có). quality: nhỏ = nét hơn.

    pix_fmt=None: KHÔNG ép -pix_fmt (dùng khi đã đặt định dạng trong filter, tránh xung đột với QSV).
    """
    enc = best_h264()
    if enc == "h264_nvenc":
        args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(quality)]
    elif enc == "h264_qsv":
        args = ["-c:v", "h264_qsv", "-global_quality", str(quality)]
    elif enc == "h264_amf":
        args = ["-c:v", "h264_amf", "-rc", "cqp", "-qp_i", str(quality), "-qp_p", str(quality)]
    else:
        args = ["-c:v", "libx264", "-preset", "medium", "-crf", str(quality)]
    return args + (["-pix_fmt", pix_fmt] if pix_fmt else [])


def filter_format() -> str:
    """Định dạng pixel nên đặt ở CUỐI filter chain cho encoder hiện tại.

    QSV/NVENC/AMF nhận nv12 (định dạng gốc HW) -> tránh lỗi -22/-40 khi qua concat/overlay.
    libx264 dùng yuv420p cho tương thích rộng.
    """
    return "nv12" if best_h264() in ("h264_qsv", "h264_nvenc", "h264_amf") else "yuv420p"

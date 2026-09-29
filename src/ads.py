"""Dò & cắt đoạn quảng cáo chèn giữa video (vd quảng cáo cờ bạc nền đỏ/vàng bão hoà).

Cách dò: lấy mẫu 1 khung mỗi `step` giây, tính tỉ lệ điểm ảnh "đỏ/vàng bão hoà" và độ sáng đỏ.
Quảng cáo cờ bạc rất khác nội dung phim (thường tối, ít bão hoà) nên tách được bằng ngưỡng màu.
KHÔNG chắc chắn 100% -> luôn cho người xem xác nhận khoảng thời gian trước khi cắt.
"""
from __future__ import annotations
from pathlib import Path

try:
    from .ffmpeg_util import run, duration
    from .progress import Bar
except ImportError:
    from ffmpeg_util import run, duration
    from progress import Bar



def parse_srt(srt_file: str | Path) -> list[dict]:
    """Đọc file SRT thành danh sách dict [{'start': float, 'end': float, 'text': str}]."""
    import re
    content = Path(srt_file).read_text(encoding="utf-8-sig", errors="ignore")
    blocks = re.split(r'\n\s*\n', content.strip())
    cues = []
    time_pat = re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})')
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 2:
            continue
        m = None
        text_lines = []
        for line in lines:
            match = time_pat.search(line)
            if match:
                m = match
            elif m:
                text_lines.append(line)
        if m:
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
            start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
            end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
            cues.append({"start": start, "end": end, "text": "\n".join(text_lines)})
    return cues


def write_srt(cues: list[dict], out_file: str | Path) -> str:
    """Ghi danh sách dict câu thành file .srt."""
    def format_ts(sec: float) -> str:
        sec = max(0.0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        if ms >= 1000:
            ms = 999
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, c in enumerate(cues, 1):
        lines.append(f"{i}")
        lines.append(f"{format_ts(c['start'])} --> {format_ts(c['end'])}")
        lines.append(c.get("text", ""))
        lines.append("")
    Path(out_file).write_text("\n".join(lines), encoding="utf-8")
    return str(out_file)



def _ad_score(img) -> tuple[float, float]:
    """img: numpy HxWx3 (RGB). Trả (tỉ lệ điểm ảnh ad, độ sáng đỏ trung bình)."""
    import numpy as np
    a = img.reshape(-1, 3).astype(float)
    R, G, B = a[:, 0], a[:, 1], a[:, 2]
    mx = a.max(1); mn = a.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    red = (R > 120) & (R > G * 1.25) & (R > B * 1.3)
    gold = (R > 150) & (G > 110) & (B < G * 0.7)
    adpx = ((red | gold) & (sat > 0.35)).mean() * 100
    return float(adpx), float(R.mean())


def detect_ads(video: str | Path, step: float = 2.0, thr_pct: float = 30.0,
               thr_r: float = 110.0, merge_gap: float = 6.0, pad: float = 1.0,
               min_dur: float = 12.0, log=print) -> list[tuple[float, float]]:
    """Quét video, trả danh sách (start, end) giây của các đoạn nghi là quảng cáo.

    Chỉ giữ đoạn dài >= min_dur giây: quảng cáo thường dài (vd 28s), còn cảnh lửa/đỏ trong phim
    chỉ loé vài giây -> lọc bớt dương tính giả.
    """
    import av
    path = str(Path(video).resolve())
    dur = duration(path)
    container = av.open(path)
    vs = container.streams.video[0]
    tb = vs.time_base
    hits: list[float] = []
    n = int(dur / step) + 1
    bar = Bar(n or 1, label="dò ad")
    i = 0
    t = 0.0
    while t < dur:
        try:
            container.seek(int(t / tb), stream=vs, backward=True)
            frame = next(container.decode(vs), None)
        except Exception:
            frame = None
        if frame is not None:
            img = frame.to_ndarray(format="rgb24")[::4, ::4, :]
            adpx, meanr = _ad_score(img)
            if adpx > thr_pct and meanr > thr_r:
                hits.append(round(t, 2))
        i += 1
        bar.update(i, f"{i}/{n}")
        t += step
    bar.finish()
    container.close()

    if not hits:
        return []
    # Gộp các mốc liền nhau (cách nhau <= merge_gap) thành khoảng
    ranges: list[list[float]] = []
    s = p = hits[0]
    for x in hits[1:]:
        if x - p <= merge_gap:
            p = x
        else:
            ranges.append([s, p + step])
            s = p = x
    ranges.append([s, p + step])
    # Lọc theo độ dài tối thiểu (bỏ loé lửa/đỏ ngắn) + đệm mép + kẹp biên
    out: list[tuple[float, float]] = []
    for a, b in ranges:
        if (b - a) < min_dur:
            continue
        a = max(0.0, a - pad)
        b = min(dur, b + pad)
        out.append((round(a, 2), round(b, 2)))
    return out


def detect_ads_by_resolution(video: str | Path, step: float = 2.0, pad: float = 0.3,
                             log=print) -> list[tuple[float, float]]:
    """Dò quảng cáo theo ĐỘ PHÂN GIẢI: nội dung thường 1 kích thước cố định, quảng cáo chèn vào
    hay khác kích thước (vd phim 1280x720, quảng cáo 1920x1080). Rất chuẩn khi ad khác res —
    không dính dương tính giả kiểu cảnh lửa/đỏ. Tự tinh chỉnh biên ở mức 0.2s và đệm `pad` vào
    content để cắt TRỌN vùng khác-res (đoạn giữ lại đồng nhất -> concat không mất frame)."""
    import av
    from collections import Counter
    path = str(Path(video).resolve())
    dur = duration(path)

    def dims(t: float):
        c = av.open(path); vs = c.streams.video[0]; tb = vs.time_base
        try:
            c.seek(int(t / tb), stream=vs, backward=True)
            f = next(c.decode(vs), None)
            return (f.width, f.height) if f else None
        finally:
            c.close()

    # kích thước phổ biến nhất = nội dung
    samples = []
    t = 0.0
    bar = Bar(int(dur / step) + 1 or 1, label="dò res")
    i = 0
    while t < dur:
        d = dims(t)
        if d:
            samples.append((round(t, 2), d))
        i += 1; bar.update(i, f"{i}")
        t += step
    bar.finish()
    if not samples:
        return []
    main = Counter(d for _, d in samples).most_common(1)[0][0]
    hits = [tt for tt, d in samples if d != main]
    if not hits:
        return []
    # gộp
    ranges = []
    s = p = hits[0]
    for x in hits[1:]:
        if x - p <= step * 2:
            p = x
        else:
            ranges.append([s, p]); s = p = x
    ranges.append([s, p])

    def is_main(t):
        return dims(t) == main

    out = []
    for a, b in ranges:
        # tinh chỉnh start lùi, end tiến ở mức 0.2s
        tt = a
        while tt > a - step - 0.2 and tt > 0 and not is_main(tt):
            tt -= 0.2
        a2 = tt + 0.2
        tt = b
        while tt < b + step + 0.2 and tt < dur and not is_main(tt):
            tt += 0.2
        b2 = tt - 0.2
        out.append((round(max(0.0, a2 - pad), 2), round(min(dur, b2 + pad), 2)))
    return out


def keep_segments(ad_ranges: list[tuple[float, float]], dur: float) -> list[tuple[float, float]]:
    """Phần bù của các đoạn ad -> các đoạn GIỮ LẠI."""
    keep: list[tuple[float, float]] = []
    cur = 0.0
    for a, b in sorted(ad_ranges):
        if a > cur:
            keep.append((cur, a))
        cur = max(cur, b)
    if cur < dur:
        keep.append((cur, dur))
    return [(a, b) for a, b in keep if b - a > 0.05]


def remap_srt(segments: list[dict], ad_ranges: list[tuple[float, float]]) -> list[dict]:
    """Bỏ cue nằm trong đoạn ad, dời cue còn lại sớm lại theo tổng thời lượng đã cắt trước nó."""
    ads = sorted(ad_ranges)

    def shift(t: float) -> float | None:
        removed = 0.0
        for a, b in ads:
            if a <= t < b:
                return None            # cue nằm trong ad -> bỏ
            if b <= t:
                removed += (b - a)
        return t - removed

    out: list[dict] = []
    for s in segments:
        ns, ne = shift(s["start"]), shift(s["end"])
        if ns is None or ne is None or ne <= ns:
            continue
        out.append(dict(s, start=ns, end=ne))
    return out


def cut_ads(video: str | Path, ad_ranges: list[tuple[float, float]], out: str | Path,
            reencode: bool = True, quality: int = 20, log=print) -> str:
    """Xuất video đã bỏ các đoạn ad (nối các đoạn giữ lại).

    Cách làm: trích TỪNG đoạn giữ bằng ffmpeg riêng (fast-seek `-ss/-t`, re-encode, scale đồng nhất),
    rồi nối bằng concat DEMUXER (stream copy). Bền với video ĐỔI ĐỘ PHÂN GIẢI giữa chừng (phim 720p,
    quảng cáo 1080p): dùng concat FILTER hay bị lỗi reconfig/nuốt đoạn; fast-seek thì scale chỉ thấy
    phần đã seek tới nên sạch và nhanh (~16x).
    """
    import os
    import shutil
    try:
        from .ffmpeg_util import video_encoder_args, run_progress, run, ffmpeg_exe
    except ImportError:
        from ffmpeg_util import video_encoder_args, run_progress, run, ffmpeg_exe

    path = str(Path(video).resolve())
    dur = duration(path)
    keep = keep_segments(ad_ranges, dur)
    if not keep:
        raise ValueError("Không còn đoạn nào để giữ.")
    # fps + kích thước nguồn (chuẩn hoá mọi đoạn về đây để concat copy được)
    fps = 25.0
    W, H = 1280, 720
    try:
        import av
        c = av.open(path)
        vstream = c.streams.video[0]
        r = vstream.average_rate
        if r:
            fps = float(r)
        W = vstream.codec_context.width or W
        H = vstream.codec_context.height or H
        c.close()
    except Exception:
        pass
    n = len(keep)
    total_keep = sum(b - a for a, b in keep)
    log(f"[ad] giữ {n} đoạn, tổng {total_keep:.0f}s (cắt {dur-total_keep:.0f}s)")
    tmpdir = Path(out).parent / (Path(out).stem + "_segs")
    tmpdir.mkdir(parents=True, exist_ok=True)
    seg_files: list[Path] = []
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps:g}")
    try:
        for i, (a, b) in enumerate(keep):
            segout = tmpdir / f"seg{i:03d}.mp4"
            run_progress(["-ss", f"{a}", "-t", f"{b - a}", "-i", path, "-vf", vf,
                          "-fps_mode", "cfr", "-c:a", "aac", "-ar", "48000",
                          *video_encoder_args(quality, pix_fmt=None), str(segout)],
                         total_dur=(b - a), label=f"cắt {i+1}/{n}")
            seg_files.append(segout)
        # nối bằng concat demuxer (stream copy)
        listfile = tmpdir / "list.txt"
        listfile.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in seg_files), encoding="utf-8")
        log(f"[ad] nối {n} đoạn...")
        run(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy",
             "-movflags", "+faststart", str(out)])
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
    return str(out)

import os, sys, time, subprocess, argparse, json, traceback

try:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except Exception:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('ascii', 'replace').decode('ascii')}", flush=True)
        except Exception:
            pass

def _tim_ffmpeg():
    paths = [
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\bin\ffmpeg.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\ffmpeg.exe",
        "ffmpeg"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "ffmpeg"

def _tim_ffprobe():
    paths = [
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\bin\ffprobe.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\ffprobe.exe",
        "ffprobe"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "ffprobe"

def get_video_info(video_path):
    ffprobe = _tim_ffprobe()
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json", video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        stream = data.get("streams", [{}])[0]
        dur = float(data.get("format", {}).get("duration", 0) or stream.get("duration", 0))
        return {
            "width": int(stream.get("width", 1920)),
            "height": int(stream.get("height", 1080)),
            "duration": dur
        }
    except Exception:
        return {"width": 1920, "height": 1080, "duration": 0}

def build_ffmpeg_filters(opts, info):
    vf_list = []
    af_list = []

    # 1. Dynamic Crop / Zoom
    zoom = float(opts.get("zoom", 1.04))
    if zoom > 1.0:
        w, h = info["width"], info["height"]
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        crop_w = crop_w - (crop_w % 2)
        crop_h = crop_h - (crop_h % 2)
        vf_list.append(f"crop={crop_w}:{crop_h},scale={w}:{h}")

    # 2. Mirror Flip
    if opts.get("mirror"):
        vf_list.append("hflip")

    # 3. Color Grading & Saturation
    if opts.get("color"):
        vf_list.append("eq=contrast=1.04:brightness=0.01:saturation=1.06")

    # 4. Border / Padding
    if opts.get("border"):
        w, h = info["width"], info["height"]
        vf_list.append(f"pad=w={w+20}:h={h+20}:x=10:y=10:color=black,scale={w}:{h}")

    # 5. FPS Adjustment
    fps = opts.get("fps")
    if fps:
        vf_list.append(f"fps=fps={fps}")

    # 6. Audio Pitch & Speed Shift
    pitch = float(opts.get("pitch", 1.03))
    speed = float(opts.get("speed", 1.02))

    if pitch != 1.0 or speed != 1.0:
        sample_rate = 44100
        new_rate = int(sample_rate * pitch)
        tempo = speed / pitch
        af_list.append(f"asetrate={new_rate},aresample={sample_rate},atempo={tempo:.4f}")

    vf_str = ",".join(vf_list) if vf_list else "null"
    af_str = ",".join(af_list) if af_list else "anull"

    return vf_str, af_str

_GPU_ENCODER_CACHE = None

def check_gpu_encoder():
    global _GPU_ENCODER_CACHE
    if _GPU_ENCODER_CACHE is not None:
        return _GPU_ENCODER_CACHE

    ffmpeg = _tim_ffmpeg()
    for enc in ["h264_nvenc", "h264_qsv", "h264_amf"]:
        try:
            cmd = [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1", "-c:v", enc, "-f", "null", "-"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                _GPU_ENCODER_CACHE = enc
                return _GPU_ENCODER_CACHE
        except Exception:
            pass

    _GPU_ENCODER_CACHE = "libx264"
    return _GPU_ENCODER_CACHE

def render_ne_ban_quuyen(input_path, output_path, opts=None):
    if opts is None:
        opts = {}

    ffmpeg = _tim_ffmpeg()
    info = get_video_info(input_path)
    vf, af = build_ffmpeg_filters(opts, info)
    encoder = check_gpu_encoder()

    enc_desc = ("Gia tốc GPU NVENC" if encoder == "h264_nvenc" 
                else ("Gia tốc iGPU Intel QuickSync (QSV)" if encoder == "h264_qsv"
                else ("Gia tốc AMD AMF" if encoder == "h264_amf" else "CPU libx264")))

    log(f"▶ Bắt đầu render né bản quyền: {os.path.basename(input_path)}")
    log(f"   · Bộ lọc video: {vf}")
    log(f"   · Bộ lọc audio: {af}")
    log(f"   · Encoder: {encoder} ({enc_desc})")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    preset_val = "p4" if encoder == "h264_nvenc" else ("veryfast" if encoder in ("h264_qsv", "h264_amf") else "fast")

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", vf,
        "-af", af,
        "-c:v", encoder,
        "-preset", preset_val,
        "-c:a", "aac",
        "-b:a", "192k",
        "-progress", "pipe:1",
        output_path
    ]

    duration = info.get("duration", 0)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", errors="replace")

    for line in proc.stdout:
        line = line.strip()
        if line.startswith("out_time_ms="):
            try:
                ms = float(line.split("=")[1])
                curr_sec = ms / 1000000.0
                if duration > 0:
                    pct = min(99.0, (curr_sec / duration) * 100.0)
                    log(f"Progress: {pct:.1f}%")
            except Exception:
                pass

    proc.wait()
    if proc.returncode == 0 and os.path.exists(output_path):
        log(f"✓ Hoàn tất 100% -> {os.path.basename(output_path)}")
        return True
    else:
        log(f"❌ Render hỏng với mã thoát: {proc.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Render Né Bản Quyền Thông Minh")
    parser.add_argument("--input", required=True, help="Đường dẫn file video hoặc thư mục chứa video")
    parser.add_argument("--output-dir", default="", help="Thư mục xuất file")
    parser.add_argument("--zoom", default="1.04", help="Thu/phóng động (mặc định 1.04)")
    parser.add_argument("--pitch", default="1.03", help="Đổi cao độ âm thanh (mặc định 1.03)")
    parser.add_argument("--speed", default="1.02", help="Đổi tốc độ (mặc định 1.02)")
    parser.add_argument("--mirror", action="store_true", help="Lật ngang video")
    parser.add_argument("--color", action="store_true", help="Chỉnh màu/độ tương phản")
    parser.add_argument("--border", action="store_true", help="Thêm viền khung")
    parser.add_argument("--fps", default="", help="Khung hình FPS (ví dụ 30)")

    args = parser.parse_args()

    opts = {
        "zoom": float(args.zoom),
        "pitch": float(args.pitch),
        "speed": float(args.speed),
        "mirror": args.mirror,
        "color": args.color,
        "border": args.border,
        "fps": args.fps
    }

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.output_dir or os.path.join(base_dir, "MediaCrawler", "data", "ne_ban_quuyen", "videos")
    os.makedirs(out_dir, exist_ok=True)

    if os.path.isfile(args.input):
        v_name = os.path.basename(args.input)
        name_no_ext, ext = os.path.splitext(v_name)
        out_path = os.path.join(out_dir, f"{name_no_ext}_nebanguoyen{ext}")
        render_ne_ban_quuyen(args.input, out_path, opts)
    elif os.path.isdir(args.input):
        files = [os.path.join(args.input, f) for f in os.listdir(args.input) if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm"))]
        if not files:
            log(f"⚠️ Không tìm thấy video nào trong thư mục: {args.input}")
            return
        log(f"Tìm thấy {len(files)} video trong thư mục...")
        for i, f in enumerate(files):
            log(f"[{i+1}/{len(files)}] Đang xử lý: {os.path.basename(f)}")
            name_no_ext, ext = os.path.splitext(os.path.basename(f))
            out_path = os.path.join(out_dir, f"{name_no_ext}_nebanguoyen{ext}")
            render_ne_ban_quuyen(f, out_path, opts)
    else:
        log(f"❌ Đường dẫn video/thư mục đầu vào không tồn tại: '{args.input}'")

if __name__ == "__main__":
    main()

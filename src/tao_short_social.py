import os
import sys
import time
import json
import random
import argparse
import subprocess
import re
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote

# Set UTF-8 encoding for stdout/stderr
try:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] [SHORT-SOCIAL] {msg}", flush=True)
    except Exception:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] [SHORT-SOCIAL] {msg.encode('ascii', 'replace').decode('ascii')}", flush=True)
        except Exception:
            pass

def _tim_ffmpeg():
    paths = [
        r"C:\Users\Ngoc Hieu\Desktop\Career_path\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe",
        r"C:\Users\Ngoc Hieu\Desktop\Career_path\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\bin\ffmpeg.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\ffmpeg.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    import shutil
    w = shutil.which("ffmpeg")
    if w:
        return w
    return "ffmpeg"

def _tim_ffprobe():
    paths = [
        r"C:\Users\Ngoc Hieu\Desktop\Career_path\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffprobe.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\bin\ffprobe.exe",
        r"C:\Users\Ngoc Hieu\Desktop\YT stuff\vncr_extracted\app_contents\resources\vendor\ffmpeg\ffprobe.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    import shutil
    w = shutil.which("ffprobe")
    if w:
        return w
    return None

def generate_silence(duration_sec, out_mp3):
    ffmpeg = _tim_ffmpeg()
    cmd = [ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(duration_sec), "-c:a", "libmp3lame", "-b:a", "128k", out_mp3]
    subprocess.run(cmd, capture_output=True, check=True)
    return out_mp3

def check_gpu_encoder():
    ffmpeg = _tim_ffmpeg()
    try:
        cmd = [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"

def get_audio_duration(audio_path):
    ffprobe = _tim_ffprobe()
    if ffprobe:
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                val = float(res.stdout.strip())
                if val > 0:
                    return val
        except Exception:
            pass

    ffmpeg = _tim_ffmpeg()
    cmd = [ffmpeg, "-i", audio_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if match:
            h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
            val = h * 3600 + m * 60 + s
            if val > 0:
                return val
    except Exception:
        pass

    return 3.0

def get_video_duration(video_path):
    ffprobe = _tim_ffprobe()
    if ffprobe:
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                val = float(res.stdout.strip())
                if val > 0:
                    return val
        except Exception:
            pass

    ffmpeg = _tim_ffmpeg()
    cmd = [ffmpeg, "-i", video_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if match:
            h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
            val = h * 3600 + m * 60 + s
            if val > 0:
                return val
    except Exception:
        pass

    return 60.0

def add_audio_buffer(audio_path, buffer_sec, temp_dir, idx_tag, timestamp):
    raw_dur = get_audio_duration(audio_path)
    if buffer_sec <= 0:
        log(f"   └─ Seg '{idx_tag}': Thời lượng đọc TTS = {raw_dur:.2f}s (Buffer = 0s)")
        return audio_path, raw_dur

    silence_p = os.path.join(temp_dir, f"silence_{idx_tag}_{timestamp}.mp3")
    padded_audio = os.path.join(temp_dir, f"padded_{idx_tag}_{timestamp}.mp3")
    generate_silence(buffer_sec, silence_p)

    concat_txt = os.path.join(temp_dir, f"concat_pad_{idx_tag}_{timestamp}.txt")
    raw_safe = audio_path.replace("\\", "/")
    sil_safe = silence_p.replace("\\", "/")

    with open(concat_txt, "w", encoding="utf-8") as f_pad:
        f_pad.write(f"file '{raw_safe}'\nfile '{sil_safe}'\n")

    ffmpeg = _tim_ffmpeg()
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c:a", "libmp3lame", "-b:a", "192k", padded_audio]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and os.path.exists(padded_audio):
        actual_padded_dur = get_audio_duration(padded_audio)
        log(f"   └─ Seg '{idx_tag}': Thời lượng đọc TTS = {raw_dur:.2f}s + Buffer = {buffer_sec:.1f}s -> Tổng hiển thị card = {actual_padded_dur:.2f}s")
        return padded_audio, actual_padded_dur
    else:
        log(f"   └─ Seg '{idx_tag}': Thời lượng đọc TTS = {raw_dur:.2f}s (Lỗi tạo buffer -> giữ audio gốc)")
        return audio_path, raw_dur

# ==========================================
# 1. DATA FETCHERS (REDDIT RSS & THREADS)
# ==========================================

def fetch_reddit_data(input_target, max_comments=2):
    """
    Fetches Reddit post data using unblocked Reddit RSS Atom feed with fallback.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 SocialShorts/1.0"
    }

    if input_target.startswith("http"):
        clean_url = input_target.split("?")[0].rstrip("/")
        rss_url = f"{clean_url}.rss"
    else:
        sub = input_target.replace("r/", "").replace("/", "").strip()
        rss_url = f"https://www.reddit.com/r/{sub}/hot.rss"

    log(f"Đang cào dữ liệu Reddit RSS từ: {rss_url}")
    
    try:
        req = urllib.request.Request(rss_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_content = response.read()

        root = ET.fromstring(xml_content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        if entries:
            chosen_entry = None
            for entry in entries:
                title_elem = entry.find('atom:title', ns)
                if title_elem is not None and title_elem.text:
                    t_text = title_elem.text
                    if "looking for new moderators" not in t_text.lower() and "welcome to" not in t_text.lower():
                        chosen_entry = entry
                        break
            if not chosen_entry:
                chosen_entry = entries[0]

            title = chosen_entry.find('atom:title', ns).text
            author_elem = chosen_entry.find('atom:author/atom:name', ns)
            author = author_elem.text if author_elem is not None else "/u/anonymous"
            
            comments = []
            link_elem = chosen_entry.find('atom:link', ns)
            if link_elem is not None:
                post_link = link_elem.get('href', '')
                if post_link and not post_link.endswith('.rss'):
                    comment_rss = f"{post_link.rstrip('/')}.rss"
                    try:
                        c_req = urllib.request.Request(comment_rss, headers=headers)
                        with urllib.request.urlopen(c_req, timeout=10) as c_res:
                            c_root = ET.fromstring(c_res.read())
                            c_entries = c_root.findall('atom:entry', ns)
                            for c_entry in c_entries[1:]:
                                c_author = c_entry.find('atom:author/atom:name', ns)
                                c_content = c_entry.find('atom:content', ns)
                                raw_txt = ""
                                if c_content is not None and c_content.text:
                                    raw_txt = re.sub('<[^<]+?>', '', c_content.text).strip()
                                if raw_txt and len(raw_txt) > 15 and not raw_txt.startswith("http"):
                                    c_auth_name = c_author.text if c_author is not None else "/u/user"
                                    comments.append({
                                        "author": c_auth_name,
                                        "body": raw_txt[:280],
                                        "score": random.randint(120, 3500)
                                    })
                                    if len(comments) >= max_comments:
                                        break
                    except Exception:
                        pass

            if not comments:
                comments = [
                    {"author": "/u/TopCommenter", "body": "This is honestly one of the most accurate responses I have read all week.", "score": 2450},
                    {"author": "/u/RedditUser99", "body": "I can completely relate to this. The exact same thing happened to a friend of mine last year.", "score": 1820}
                ][:max_comments]

            return {
                "platform": "reddit",
                "header_tag": "r/AskReddit" if "AskReddit" in rss_url else "r/Reddit",
                "author": author,
                "title": title,
                "body": "",
                "score": random.randint(1500, 18500),
                "comments": comments
            }
    except Exception as ex:
        log(f"Notice fetching RSS ({ex}) -> Fallback to default post data")

    # Hardcoded fallback post if Reddit blocks or is unreachable
    return {
        "platform": "reddit",
        "header_tag": "r/AskReddit",
        "author": "/u/StoryTellerPro",
        "title": "What is a life secret that everyone should know about?",
        "body": "",
        "score": 14200,
        "comments": [
            {"author": "/u/WiseMind", "body": "People care much less about your mistakes than you think. Everyone is focused on themselves.", "score": 4510},
            {"author": "/u/LifeExplorer", "body": "Consistency always beats intensity. Doing 15 minutes a day will yield better results than 5 hours once a month.", "score": 3210}
        ][:max_comments]
    }

def fetch_threads_data(threads_url, max_comments=2):
    """
    Fetches Threads post using Playwright or fallback mock.
    """
    log(f"Đang cào dữ liệu Threads từ: {threads_url}")
    title = "Ý kiến thảo luận hot nhất trên Threads hôm nay"
    comments = [
        {"author": "@user_one", "body": "Mình thấy điều này hoàn toàn chính xác luôn!", "score": 340},
        {"author": "@user_two", "body": "Chuẩn quá bạn ơi, góc nhìn rất thực tế.", "score": 210}
    ]

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(threads_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            text_nodes = page.query_selector_all("span, div[dir='auto']")
            texts = [t.inner_text().strip() for t in text_nodes if t.inner_text().strip()]
            
            unique_texts = []
            for txt in texts:
                if txt not in unique_texts and len(txt) > 15 and "Threads" not in txt and "Log in" not in txt:
                    unique_texts.append(txt)

            if unique_texts:
                title = unique_texts[0]
                comments = []
                for txt in unique_texts[1:1+max_comments]:
                    comments.append({
                        "author": "@threads_user",
                        "body": txt[:280],
                        "score": random.randint(50, 800)
                    })

            browser.close()
    except Exception as ex:
        log(f"Notice Playwright Threads fetch: {ex}")

    return {
        "platform": "threads",
        "header_tag": "Threads",
        "author": "@threads_post",
        "title": title,
        "body": "",
        "score": random.randint(500, 4200),
        "comments": comments[:max_comments]
    }

# ==========================================
# 2. TTS AUDIO GENERATOR (EDGE-TTS)
# ==========================================

def generate_tts_edge(text, out_mp3, lang="en", tts_rate="1.0"):
    """
    Generates TTS audio file using edge-tts with customizable reading speed.
    """
    voice = "en-US-ChristopherNeural" if lang == "en" else "vi-VN-HoaiMyNeural"
    
    rate_str = "+0%"
    try:
        if str(tts_rate).endswith("%"):
            rate_str = str(tts_rate)
        else:
            r_val = float(tts_rate)
            pct = int(round((r_val - 1.0) * 100))
            rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"
    except Exception:
        rate_str = "+0%"

    cmd = [sys.executable, "-m", "edge_tts", "--voice", voice]
    if rate_str != "+0%":
        cmd.extend(["--rate", rate_str])
    cmd.extend(["--text", text, "--write-media", out_mp3])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
        return out_mp3

    raise Exception(f"Không thể tạo âm thanh TTS cho: '{text[:30]}...'")

# ==========================================
# 3. UI CARD IMAGE GENERATOR (PILLOW)
# ==========================================

def create_ui_card(platform, header_tag, author, text, score, out_img, is_comment=False):
    """
    Draws a dark-mode UI card (Reddit/Threads style) with Pillow.
    Card dimensions: 900px wide, rendered with clean padding and rounded corners.
    """
    from PIL import Image, ImageDraw, ImageFont

    card_w = 900
    padding = 36
    bg_color = (26, 26, 27) if platform == "reddit" else (18, 18, 18)
    text_color = (240, 240, 240)
    sub_color = (155, 155, 155)
    brand_color = (255, 69, 0) if platform == "reddit" else (255, 255, 255)

    try:
        font_title = ImageFont.truetype("arial.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_body = ImageFont.truetype("arialbd.ttf", 28)
    except Exception:
        font_title = font_sub = font_body = ImageFont.load_default()

    max_txt_w = card_w - (padding * 2)
    
    def wrap_text(txt, font, max_w):
        lines = []
        words = txt.split()
        curr_line = ""
        for w in words:
            test_line = f"{curr_line} {w}".strip()
            bbox = font.getbbox(test_line) if hasattr(font, 'getbbox') else (0,0,len(test_line)*14, 28)
            w_px = bbox[2] - bbox[0]
            if w_px <= max_w:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = w
        if curr_line:
            lines.append(curr_line)
        return lines

    text_lines = wrap_text(text, font_body, max_txt_w)
    line_h = 40
    text_section_h = len(text_lines) * line_h

    header_h = 60
    footer_h = 50
    card_h = header_h + text_section_h + footer_h + (padding * 2)

    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    draw.rounded_rectangle([0, 0, card_w, card_h], radius=24, fill=bg_color, outline=(50, 50, 50), width=2)

    # Draw Avatar Circle
    avatar_r = 20
    avatar_x = padding + avatar_r
    avatar_y = padding + avatar_r
    draw.ellipse([avatar_x - avatar_r, avatar_y - avatar_r, avatar_x + avatar_r, avatar_y + avatar_r], fill=brand_color)
    
    init_char = (header_tag[0] if header_tag else "R").upper()
    draw.text((avatar_x - 7, avatar_y - 12), init_char, fill=(255, 255, 255) if platform == "reddit" else (0, 0, 0), font=font_sub)

    # Draw Header Tag & Author
    draw.text((padding + 52, padding + 2), header_tag, fill=text_color, font=font_title)
    draw.text((padding + 52, padding + 30), f"Posted by {author}", fill=sub_color, font=font_sub)

    # Draw Body Text Lines
    curr_y = padding + header_h + 10
    for line in text_lines:
        draw.text((padding, curr_y), line, fill=text_color, font=font_body)
        curr_y += line_h

    # Draw Footer (Upvote Score)
    footer_y = card_h - padding - 30
    upvote_str = f"▲  {score:,} Upvotes   💬 Comments"
    draw.text((padding, footer_y), upvote_str, fill=sub_color, font=font_sub)

    img.save(out_img, "PNG")
    return out_img

# ==========================================
# 4. GAMEPLAY BACKGROUND MANAGER
# ==========================================

def ensure_gameplay_bg(bg_dir, bg_type="minecraft"):
    """
    Ensures a 9:16 vertical gameplay background video exists in bg_dir/bg_type.
    """
    sub_dir = os.path.join(bg_dir, bg_type)
    os.makedirs(sub_dir, exist_ok=True)
    
    files = [os.path.join(sub_dir, f) for f in os.listdir(sub_dir) if f.lower().endswith((".mp4", ".mov", ".mkv")) and not f.endswith(".part")]
    if not files:
        files = [os.path.join(bg_dir, f) for f in os.listdir(bg_dir) if f.lower().endswith((".mp4", ".mov", ".mkv")) and not f.endswith(".part")]
    
    if files:
        real_files = [f for f in files if "fallback" not in os.path.basename(f) and "minecraft_gameplay_bg.mp4" not in os.path.basename(f)]
        if real_files:
            chosen = random.choice(real_files)
            log(f"Sử dụng video nền Gameplay thực tế ({bg_type}): {os.path.basename(chosen)}")
            return chosen
        return random.choice(files)

    # Fallback if no video found
    ffmpeg = _tim_ffmpeg()
    fallback_bg = os.path.join(sub_dir, f"{bg_type}_fallback.mp4")
    cmd_gen = [
        ffmpeg, "-y", "-f", "lavfi",
        "-i", "color=c=0x111827:s=1080x1920:d=120",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        fallback_bg
    ]
    subprocess.run(cmd_gen, capture_output=True, check=True)
    return fallback_bg

# ==========================================
# 5. FFMPEG SHORT VIDEO COMPOSITOR
# ==========================================

def composite_social_short(bg_video, segments, out_mp4):
    """
    Composites vertical background video (1080x1920) with TTS audio segments and UI card image overlays.
    """
    ffmpeg = _tim_ffmpeg()
    encoder = check_gpu_encoder()
    
    total_audio_dur = sum(s["duration"] for s in segments) + 0.5
    bg_dur = get_video_duration(bg_video)

    max_start = max(0.0, bg_dur - total_audio_dur - 2.0)
    start_time = random.uniform(0.0, max_start) if max_start > 0 else 0.0

    log(f"▶ Render Short Video: Tổng thời lượng = {total_audio_dur:.1f}s (Encoder: {encoder})")

    temp_dir = os.path.dirname(out_mp4)
    concat_list_file = os.path.join(temp_dir, f"audio_concat_{int(time.time())}.txt")
    combined_audio = os.path.join(temp_dir, f"combined_audio_{int(time.time())}.mp3")

    with open(concat_list_file, "w", encoding="utf-8") as f:
        for seg in segments:
            safe_p = seg["audio_path"].replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    cmd_a = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c:a", "libmp3lame", "-b:a", "192k", combined_audio]
    subprocess.run(cmd_a, capture_output=True, check=True)

    filter_complex = [
        f"[0:v]trim=start={start_time:.2f}:duration={total_audio_dur:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg]"
    ]

    curr_t = 0.0
    prev_stream = "[bg]"

    inputs = ["-i", bg_video]
    for i, seg in enumerate(segments):
        inputs.extend(["-i", seg["image_path"]])
        img_idx = i + 1
        seg_dur = seg["duration"]
        end_t = curr_t + seg_dur
        next_stream = f"[v{i+1}]"
        
        filter_complex.append(
            f"{prev_stream}[{img_idx}:v]overlay=x=(W-w)/2:y=(H-h)/2:enable='between(t,{curr_t:.2f},{end_t:.2f})'{next_stream}"
        )
        prev_stream = next_stream
        curr_t = end_t

    inputs.extend(["-i", combined_audio])
    combined_audio_idx = len(segments) + 1

    filter_str = ";".join(filter_complex)

    cmd_render = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", prev_stream,
        "-map", f"{combined_audio_idx}:a",
        "-c:v", encoder,
        "-preset", "p4" if encoder == "h264_nvenc" else "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{total_audio_dur:.2f}",
        out_mp4
    ]

    res = subprocess.run(cmd_render, capture_output=True, text=True)
    
    try:
        if os.path.exists(concat_list_file): os.remove(concat_list_file)
        if os.path.exists(combined_audio): os.remove(combined_audio)
    except Exception:
        pass

    if res.returncode == 0 and os.path.exists(out_mp4):
        log(f"✓ Hoàn tất Render Short Video -> {out_mp4}")
        return out_mp4
    else:
        log(f"❌ Lỗi render FFmpeg (code {res.returncode}): {res.stderr[:300]}")
        raise Exception(f"FFmpeg render code {res.returncode}")

# ==========================================
# MAIN PIPELINE FUNCTION
# ==========================================

def make_social_short_video(input_target, platform="reddit", lang="en", max_comments=2, bg_type="minecraft", outro="", comment_delay=1.0, genre="", tts_rate="1.0"):
    """
    Main orchestrator pipeline to create a Reddit/Threads Short video.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work_dir = os.path.join(base_dir, "MediaCrawler", "data", "social_shorts")
    temp_dir = os.path.join(work_dir, "temp")
    out_dir = os.path.join(work_dir, "videos")
    bg_dir = os.path.join(work_dir, "bg_gameplay")

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(bg_dir, exist_ok=True)

    timestamp = int(time.time())

    # Map genre if specified and target is default
    if genre and genre in ("funny", "confession", "horror", "quotes", "gaming"):
        genre_map = {"funny": "AskReddit", "confession": "AITAH", "horror": "nosleep", "quotes": "Showerthoughts", "gaming": "gaming"}
        if not input_target.startswith("http"):
            input_target = genre_map.get(genre, input_target)
            log(f"Đã chọn thể loại '{genre}' -> Chuyển sang Subreddit: {input_target}")

    log(f"--- 🚀 BƯỚC 1: CÀO BÀI VIẾT ({platform.upper()}) ---")
    if platform == "threads":
        data = fetch_threads_data(input_target, max_comments=max_comments)
    else:
        data = fetch_reddit_data(input_target, max_comments=max_comments)

    log(f"Tiêu đề: '{data['title']}' ({len(data['comments'])} bình luận)")

    log(f"--- 🔊 BƯỚC 2 & 3: TẠO GIỌNG ĐỌC TTS (Tốc độ {tts_rate}x) & VẼ THẺ UI CARD ---")
    segments = []

    # Segment 0: Main Title
    title_text = data['title']
    title_audio_raw = os.path.join(temp_dir, f"seg_0_title_raw_{timestamp}.mp3")
    title_card = os.path.join(temp_dir, f"seg_0_card_{timestamp}.png")

    log(f"🎙️ [0/Title] Đang tạo TTS & Thẻ UI...")
    generate_tts_edge(title_text, title_audio_raw, lang=lang, tts_rate=tts_rate)
    create_ui_card(data["platform"], data["header_tag"], data["author"], title_text, data["score"], title_card, is_comment=False)

    title_audio, dur_0 = add_audio_buffer(title_audio_raw, float(comment_delay), temp_dir, "title", timestamp)
    segments.append({"audio_path": title_audio, "image_path": title_card, "duration": dur_0})

    # Segments 1..N: Comments
    for idx, c in enumerate(data["comments"], 1):
        c_text = c["body"]
        c_audio_raw = os.path.join(temp_dir, f"seg_{idx}_c_raw_{timestamp}.mp3")
        c_card = os.path.join(temp_dir, f"seg_{idx}_card_{timestamp}.png")

        log(f"🎙️ [{idx}/{len(data['comments'])}] Đang tạo TTS & Thẻ UI Comment...")
        generate_tts_edge(c_text, c_audio_raw, lang=lang, tts_rate=tts_rate)
        create_ui_card(data["platform"], data["header_tag"], c["author"], c_text, c["score"], c_card, is_comment=True)

        c_audio, dur_i = add_audio_buffer(c_audio_raw, float(comment_delay), temp_dir, f"c_{idx}", timestamp)
        segments.append({"audio_path": c_audio, "image_path": c_card, "duration": dur_i})

    # Segment Outro (if provided)
    if outro and outro.strip():
        o_text = outro.strip()
        log(f"🎙️ [Outro] Thêm đoạn Outro kết video: '{o_text}'")
        o_audio_raw = os.path.join(temp_dir, f"seg_outro_raw_{timestamp}.mp3")
        o_card = os.path.join(temp_dir, f"seg_outro_card_{timestamp}.png")
        generate_tts_edge(o_text, o_audio_raw, lang=lang, tts_rate=tts_rate)
        create_ui_card(data["platform"], "💬 Câu Hỏi Kết Video", "Host", o_text, 9999, o_card, is_comment=True)

        o_audio, dur_o = add_audio_buffer(o_audio_raw, float(comment_delay), temp_dir, "outro", timestamp)
        segments.append({"audio_path": o_audio, "image_path": o_card, "duration": dur_o})

    log("--- 🎮 BƯỚC 4: CHUẨN BỊ VIDEO NỀN GAMEPLAY ---")
    bg_video = ensure_gameplay_bg(bg_dir, bg_type=bg_type)

    log("--- 🎬 BƯỚC 5: RENDER VIDEO SHORT (9:16) ---")
    clean_title = "".join(ch for ch in data['title'][:30] if ch.isalnum() or ch in (' ', '_', '-')).strip().replace(" ", "_")
    out_mp4 = os.path.join(out_dir, f"Short_{data['platform']}_{clean_title}_{timestamp}.mp4")

    composite_social_short(bg_video, segments, out_mp4)

    for seg in segments:
        try:
            if os.path.exists(seg["audio_path"]): os.remove(seg["audio_path"])
            if os.path.exists(seg["image_path"]): os.remove(seg["image_path"])
        except Exception:
            pass

    log(f"✨ HOÀN THÀNH! Video lưu tại: {out_mp4}")
    return out_mp4

def main():
    parser = argparse.ArgumentParser(description="Tự động tạo Short Video Reddit/Threads với Gameplay Background")
    parser.add_argument("--platform", default="reddit", choices=["reddit", "threads"], help="Nền tảng cào dữ liệu")
    parser.add_argument("--target", default="AskReddit", help="Tên Subreddit (vd: AskReddit) hoặc Link bài viết Reddit/Threads")
    parser.add_argument("--lang", default="en", choices=["en", "vi"], help="Ngôn ngữ giọng đọc TTS")
    parser.add_argument("--max-comments", type=int, default=2, help="Số lượng bình luận hiển thị (1-10)")
    parser.add_argument("--bg-type", default="minecraft", help="Loại video nền (minecraft / subway)")
    parser.add_argument("--outro", default="", help="Câu hỏi/kêu gọi kết video (Outro CTA)")
    parser.add_argument("--comment-delay", type=float, default=1.0, help="Thời gian chờ giữa các comment (giây)")
    parser.add_argument("--genre", default="", help="Thể loại nội dung (funny, confession, horror, quotes)")
    parser.add_argument("--tts-rate", default="1.0", help="Tốc độ giọng đọc TTS (1.0, 1.1, 1.2, 1.25, 1.5)")

    args = parser.parse_args()

    make_social_short_video(
        input_target=args.target,
        platform=args.platform,
        lang=args.lang,
        max_comments=args.max_comments,
        bg_type=args.bg_type,
        outro=args.outro,
        comment_delay=args.comment_delay,
        genre=args.genre,
        tts_rate=args.tts_rate
    )

if __name__ == "__main__":
    main()

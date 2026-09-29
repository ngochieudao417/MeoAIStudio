import os
import sys
import socket
import json
import threading
import subprocess
import time
import shutil

# 1. Force IPv4 globally to fix YouTube Read Timed Out (IPv6 socket hangs)
_orig_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _getaddrinfo_ipv4

# 2. Prepend vendor Node.js & FFmpeg binaries dynamically to PATH
current_dir = os.path.dirname(os.path.abspath(__file__))

def _tim_vendor_binary(bin_name):
    found = shutil.which(bin_name)
    if found:
        return os.path.dirname(os.path.abspath(found))
    candidates = [
        r"C:\Users\Ngoc Hieu\dev-tools\node",
        os.path.join(current_dir, ".venv", "Lib", "site-packages", "playwright", "driver"),
        r"C:\Users\Ngoc Hieu\AppData\Roaming\SnapAny\tools\ffmpeg\8.0",
        r"C:\Users\Ngoc Hieu\AppData\Roaming\SnapAny\tools\ffprobe\8.0",
        r"C:\Users\Ngoc Hieu\AppData\Local\CapCut\Apps\9.5.0.4050",
        r"C:\Users\Ngoc Hieu\Desktop\Career_path\vtool\.venv\Lib\site-packages\imageio_ffmpeg\binaries",
    ]
    for c in candidates:
        if os.path.exists(c):
            if os.path.exists(os.path.join(c, f"{bin_name}.exe")) or os.path.exists(os.path.join(c, bin_name)):
                return c
    return None

path_adds = []
node_dir = _tim_vendor_binary("node")
if node_dir and node_dir not in path_adds:
    path_adds.append(node_dir)
ffmpeg_dir = _tim_vendor_binary("ffmpeg")
if ffmpeg_dir and ffmpeg_dir not in path_adds:
    path_adds.append(ffmpeg_dir)
ffprobe_dir = _tim_vendor_binary("ffprobe")
if ffprobe_dir and ffprobe_dir not in path_adds:
    path_adds.append(ffprobe_dir)
if path_adds:
    os.environ["PATH"] = os.path.pathsep.join(path_adds) + os.path.pathsep + os.environ.get("PATH", "")

# 3. Patch yt_dlp default options (force IPv4, 15s socket timeout)
try:
    import yt_dlp
    _orig_ydl_init = yt_dlp.YoutubeDL.__init__
    def _patched_ydl_init(self, params=None, *args, **kwargs):
        params = dict(params or {})
        params.setdefault("source_address", "0.0.0.0")
        params.setdefault("socket_timeout", 15)
        _orig_ydl_init(self, params, *args, **kwargs)
    yt_dlp.YoutubeDL.__init__ = _patched_ydl_init
    print("[MEOWCRAWL STUDIO] Patched yt_dlp: IPv4 forced & socket timeout 15s set & FFmpeg bin path loaded.")
except Exception as e:
    print(f"[MEOWCRAWL STUDIO] Notice patching yt_dlp: {e}")

# 4. Set Environment Variables BEFORE importing web_app (Enforce CPU Mode - No NVIDIA GPU)
os.environ["VC_TIER"] = "unlimited"
os.environ["VC_TIER_FAILOPEN"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["VC_TAT_GPU"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

mc_dir = os.path.join(src_dir, "MediaCrawler")
if mc_dir not in sys.path:
    sys.path.insert(0, mc_dir)

print("[MEOWCRAWL STUDIO] Starting server in Unlocked Mode (Tier: unlimited)...")
print(f"[MEOWCRAWL STUDIO] Working Source Directory: {src_dir}")

# 5. Import web_app & patch tier functions
import web_app

web_app.TIER = "unlimited"
web_app._signed_tier = "unlimited"
web_app._tier_kind = lambda *a, **k: "unlimited"
web_app._refresh_tier = lambda *a, **k: "unlimited"
if hasattr(web_app, "_tier_tu_token_ky"):
    web_app._tier_tu_token_ky = lambda *a, **k: "unlimited"

# Allow all local API calls (bypass DNS rebinding / CSRF 403 guard locally)
if hasattr(web_app, "Handler"):
    web_app.Handler._guard = lambda self: True

# Set _NO_WINDOW to 0 so spawned processes like mo_dang_nhap can open visible GUI windows
web_app._NO_WINDOW = 0

# Clear _login_procs on every open_login request and launch mo_dang_nhap with interactive GUI creationflags
_orig_mo_dang_nhap = getattr(web_app, "mo_dang_nhap", None)
def _patched_mo_dang_nhap(platforms=None):
    print(f"[API HIT] /api/open_login requested for platforms: {platforms}", flush=True)
    if hasattr(web_app, "_login_procs") and isinstance(web_app._login_procs, dict):
        web_app._login_procs.clear()
        
    if isinstance(platforms, str):
        platforms = [platforms]
    elif not platforms:
        platforms = ["dy", "bili", "xhs"]
    else:
        platforms = list(platforms)

    python_venv = getattr(web_app, "PYTHON_VENV", sys.executable)
    script_path = os.path.join(src_dir, "mo_dang_nhap.py")
    
    cmd = [python_venv, script_path] + platforms
    print(f"[MEOWCRAWL STUDIO] Launching login browser script: {cmd}", flush=True)
    
    try:
        import subprocess
        proc = subprocess.Popen(
            cmd,
            cwd=current_dir,
            creationflags=0,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if hasattr(web_app, "_login_procs") and isinstance(web_app._login_procs, dict):
            for p in platforms:
                web_app._login_procs[p] = proc
        print(f"[MEOWCRAWL STUDIO] Login browser process launched successfully (PID={proc.pid})", flush=True)
        return True
    except Exception as e:
        print(f"[MEOWCRAWL STUDIO] Error launching login browser script: {e}", flush=True)
        if _orig_mo_dang_nhap:
            return _orig_mo_dang_nhap(platforms)
        return False

web_app.mo_dang_nhap = _patched_mo_dang_nhap

# Patch do_POST to add /api/honggo/list and /api/honggo/download
def send_json_resp(handler, code, obj):
    try:
        import json
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)
    except Exception as e:
        print(f"[MEOWCRAWL STUDIO] Error sending json response: {e}")

_orig_do_POST = web_app.Handler.do_POST
_social_shorts_lock = threading.Lock()
_social_shorts_state = {
    "running": False,
    "progress": 0,
    "step": "Sẵn sàng",
    "msg": "Sẵn sàng. Chọn Subreddit/Link và bấm 'Tạo Short Video Ngay'...",
    "lines": [],
    "last_video": ""
}

def _update_soc_state(running=None, progress=None, step=None, msg=None, add_line=None, last_video=None):
    with _social_shorts_lock:
        if running is not None: _social_shorts_state["running"] = running
        if progress is not None: _social_shorts_state["progress"] = progress
        if step is not None: _social_shorts_state["step"] = step
        if msg is not None: _social_shorts_state["msg"] = msg
        if last_video is not None: _social_shorts_state["last_video"] = last_video
        if add_line:
            _social_shorts_state["lines"].append(add_line)
            if len(_social_shorts_state["lines"]) > 200:
                _social_shorts_state["lines"].pop(0)

def _patched_do_POST(self):
    if self.path == "/api/them_video":
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            files = filedialog.askopenfilenames(
                title="Chọn video từ máy",
                filetypes=[
                    ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v *.wmv *.3gp"),
                    ("All files", "*.*")
                ]
            )
            root.destroy()
            
            res = []
            for f in files:
                f_norm = os.path.normpath(f)
                if os.path.isfile(f_norm):
                    res.append({
                        "p": f_norm,
                        "name": os.path.basename(f_norm),
                        "size_mb": round(os.path.getsize(f_norm) / (1024 * 1024), 1),
                        "duration": 0
                    })
            send_json_resp(self, 200, {"ok": True, "videos": res})
        except Exception as e:
            send_json_resp(self, 200, {"ok": False, "msg": f"Lỗi mở chọn video: {str(e)}", "videos": []})
        return

    elif self.path == "/api/quet_thu_muc":
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            folder_path = body.get("path", "").strip()
            res = []
            if folder_path and os.path.isdir(folder_path):
                valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v", ".wmv", ".3gp"}
                for root_dir, _, files in os.walk(folder_path):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in valid_exts:
                            full_p = os.path.normpath(os.path.join(root_dir, f))
                            try:
                                sz = round(os.path.getsize(full_p) / (1024 * 1024), 1)
                            except Exception:
                                sz = 0
                            res.append({
                                "p": full_p,
                                "name": f,
                                "size_mb": sz,
                                "duration": 0
                            })
            send_json_resp(self, 200, {"ok": True, "videos": res})
        except Exception as e:
            send_json_resp(self, 500, {"ok": False, "msg": f"Lỗi quét thư mục: {str(e)}", "videos": []})
        return

    elif self.path == "/api/honggo/list":
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            import tai_honggo
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            url = body.get("url", "").strip()
            if not url:
                send_json_resp(self, 400, {"ok": False, "msg": "Vui lòng nhập link hoặc ID phim Hồng Quả"})
                return

            if tai_honggo._la_duanju(url):
                sid = tai_honggo.tach_sid_dj(url)
                res_data = tai_honggo.liet_ke_bo_dj(sid)
                id_phim = sid
            else:
                id_phim = tai_honggo.tach_id(url)
                res_data = tai_honggo.liet_ke_bo(id_phim, delay=0.2)

            items = []
            if isinstance(res_data, (tuple, list)) and len(res_data) >= 3:
                title, thumb, tap_ds = res_data[0], res_data[1], res_data[2]
                for item in tap_ds:
                    ep_num = item[1]
                    ep_url = item[2]
                    items.append({
                        "id": f"{id_phim}-{ep_num}",
                        "title": f"{title} — Tập {ep_num}",
                        "thumb": thumb,
                        "url": ep_url,
                        "nick": title
                    })
                self._send(200, {"ok": True, "items": items, "tong": len(items), "title": title, "thumb": thumb})
            elif isinstance(res_data, list):
                self._send(200, {"ok": True, "items": res_data, "tong": len(res_data)})
            else:
                self._send(500, {"ok": False, "msg": "Không tìm thấy dữ liệu tập phim"})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi lấy danh sách phim Hồng Quả: {str(e)}"})
        return

    elif self.path == "/api/honggo/download":
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            url = body.get("url", "").strip()
            mode = body.get("mode", "all")
            count = str(body.get("count", "0")).strip()
            tap = str(body.get("tap", "")).strip()
            delay = str(body.get("delay", "1.5")).strip()

            if not url:
                self._send(400, {"ok": False, "msg": "Vui lòng nhập link hoặc ID phim Hồng Quả"})
                return

            python_venv = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
            if not os.path.exists(python_venv):
                python_venv = sys.executable

            script = os.path.join(src_dir, "tai_honggo.py")
            cmd = [python_venv, "-u", script, "--input", url, "--delay", delay]
            
            if mode == "count" and count:
                cmd.extend(["--count", count])
            elif mode == "range" and tap:
                cmd.extend(["--tap", tap])

            print(f"[API HIT] /api/honggo/download cmd: {cmd}", flush=True)

            def _run_download():
                try:
                    if hasattr(web_app, "_chay_stream_log"):
                        web_app._chay_stream_log(cmd, cwd=current_dir, timeout=7200)
                    else:
                        subprocess.run(cmd, cwd=current_dir, timeout=7200)
                except Exception as ex:
                    if hasattr(web_app, "them_log"):
                        web_app.them_log(f"❌ Lỗi tải phim Hồng Quả: {ex}")

            t = threading.Thread(target=_run_download, daemon=True)
            t.start()

            self._send(200, {"ok": True, "msg": "Đã khởi chạy tiến trình tải phim Hồng Quả thành công!"})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi khởi chạy tải: {str(e)}"})
        return

    elif self.path == "/api/open_login_edge":
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            import mo_dang_nhap
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            plat = body.get("plat", "dy")
            mo_dang_nhap.mo_edge_school(plat)
            self._send(200, {"ok": True, "msg": f"Đã mở Microsoft Edge (School Profile) cho {plat}!"})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi mở Edge: {str(e)}"})
        return

    elif self.path == "/api/nebanguoyen/start":
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            input_path = body.get("input", "").strip()
            
            if not input_path:
                # Default to uploads dir if not specified
                input_path = os.path.join(src_dir, "MediaCrawler", "data", "ne_ban_quuyen", "uploads")

            python_venv = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
            if not os.path.exists(python_venv):
                python_venv = sys.executable

            script = os.path.join(src_dir, "ne_ban_quuyen.py")
            cmd = [python_venv, "-u", script, "--input", input_path]

            if body.get("zoom"): cmd.extend(["--zoom", str(body.get("zoom"))])
            if body.get("pitch"): cmd.extend(["--pitch", str(body.get("pitch"))])
            if body.get("speed"): cmd.extend(["--speed", str(body.get("speed"))])
            if body.get("mirror"): cmd.append("--mirror")
            if body.get("color"): cmd.append("--color")
            if body.get("border"): cmd.append("--border")
            if body.get("fps"): cmd.extend(["--fps", str(body.get("fps"))])

            print(f"[API HIT] /api/nebanguoyen/start cmd: {cmd}", flush=True)

            def _run_nebanguoyen():
                try:
                    if hasattr(web_app, "_chay_stream_log"):
                        web_app._chay_stream_log(cmd, cwd=current_dir, timeout=7200)
                    else:
                        subprocess.run(cmd, cwd=current_dir, timeout=7200)
                except Exception as ex:
                    if hasattr(web_app, "them_log"):
                        web_app.them_log(f"❌ Lỗi render né bản quyền: {ex}")

            t = threading.Thread(target=_run_nebanguoyen, daemon=True)
            t.start()

            self._send(200, {"ok": True, "msg": "Đã khởi chạy tiến trình Render Né Bản Quyền thành công!"})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi khởi chạy render né bản quyền: {str(e)}"})
        return

    elif self.path == "/api/nebanguoyen/list":
        try:
            out_dir = os.path.join(src_dir, "MediaCrawler", "data", "ne_ban_quuyen", "videos")
            files = []
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
                        full_p = os.path.join(out_dir, f)
                        files.append({
                            "name": f,
                            "path": full_p,
                            "size": os.path.getsize(full_p),
                            "mtime": os.path.getmtime(full_p)
                        })
            files.sort(key=lambda x: x["mtime"], reverse=True)
            self._send(200, {"ok": True, "files": files, "total": len(files)})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi danh sách: {str(e)}"})
        return

    elif self.path.startswith("/api/upload_video"):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            up_dir = os.path.join(src_dir, "MediaCrawler", "data", "ne_ban_quuyen", "uploads")
            os.makedirs(up_dir, exist_ok=True)
            
            content_type = self.headers.get("Content-Type", "")
            if "application/json" in content_type:
                body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
                body = json.loads(body_bytes.decode("utf-8", errors="replace"))
                file_path = body.get("file_path", "").strip()
                if file_path and os.path.exists(file_path):
                    dest_p = os.path.join(up_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, dest_p)
                    print(f"[API HIT] /api/upload_video copied: {dest_p}", flush=True)
                    self._send(200, {"ok": True, "path": dest_p, "msg": f"Đã nhận file {os.path.basename(dest_p)}"})
                    return
            
            from urllib.parse import parse_qs, urlparse, unquote
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            filename = ""
            if "name" in query_params and query_params["name"]:
                filename = unquote(query_params["name"][0])
            if not filename:
                filename = unquote(self.headers.get("X-File-Name", ""))
            if not filename:
                filename = f"upload_{int(time.time())}.mp4"
            
            filename = os.path.basename(filename)
            dest_p = os.path.join(up_dir, filename)
            
            with open(dest_p, "wb") as f_out:
                remaining = content_length
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    f_out.write(chunk)
                    remaining -= len(chunk)
            
            print(f"[API HIT] /api/upload_video uploaded: {dest_p} ({os.path.getsize(dest_p)} bytes)", flush=True)
            self._send(200, {"ok": True, "path": dest_p, "msg": f"Đã tải lên thành công {filename}!"})
        except Exception as e:
            print(f"[API ERROR] /api/upload_video error: {e}", flush=True)
            self._send(500, {"ok": False, "msg": f"Lỗi upload video: {str(e)}"})
        return

    elif self.path in ("/api/socialshorts/start", "/api/video/start", "/api/video/render-assets"):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(body_bytes.decode("utf-8", errors="replace"))
            platform = body.get("platform", "reddit")
            target = body.get("target", "AskReddit")
            lang = body.get("lang", "en")
            max_comments = str(body.get("max_comments", "2"))
            bg_type = body.get("bg_type", "minecraft")
            outro = body.get("outro", "").strip()
            comment_delay = str(body.get("comment_delay", "1.0"))
            genre = body.get("genre", "").strip()
            tts_rate = str(body.get("tts_rate", "1.0")).strip()

            python_venv = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
            if not os.path.exists(python_venv):
                python_venv = sys.executable

            script = os.path.join(src_dir, "tao_short_social.py")
            cmd = [python_venv, "-u", script, "--platform", platform, "--target", target, "--lang", lang, "--max-comments", max_comments, "--bg-type", bg_type, "--comment-delay", comment_delay]
            if outro:
                cmd.extend(["--outro", outro])
            if genre:
                cmd.extend(["--genre", genre])
            if tts_rate:
                cmd.extend(["--tts-rate", tts_rate])

            print(f"[API HIT] /api/socialshorts/start cmd: {cmd}", flush=True)

            def _run_socialshorts():
                _update_soc_state(
                    running=True,
                    progress=5,
                    step="[1/4] Khởi chạy tiến trình...",
                    msg="🚀 Đang khởi chạy tiến trình cào dữ liệu và tạo Short Video...",
                    add_line=f"🚀 [SHORT-SOCIAL] Khởi chạy cho nới {platform.upper()} ({target})..."
                )
                try:
                    proc = subprocess.Popen(
                        cmd,
                        cwd=current_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1
                    )
                    for raw_line in iter(proc.stdout.readline, ''):
                        line = raw_line.strip()
                        if not line:
                            continue
                        print(f"[SHORT-SOCIAL LOG] {line}", flush=True)
                        _update_soc_state(add_line=line)
                        if hasattr(web_app, "them_log"):
                            try: web_app.them_log(line)
                            except Exception: pass

                        if "BƯỚC 1:" in line or "CÀO BÀI VIẾT" in line:
                            _update_soc_state(progress=25, step="[1/4] Cào dữ liệu bài viết & comment...", msg="📥 Đang cào dữ liệu bài viết & comment...")
                        elif "BƯỚC 2" in line or "TẠO GIỌNG ĐỌC TTS" in line:
                            _update_soc_state(progress=50, step="[2/4] Tạo giọng đọc TTS & Thẻ UI Card...", msg="🎙️ Đang tạo giọng đọc TTS & Thẻ UI Card...")
                        elif "BƯỚC 4:" in line or "VIDEO NỀN GAMEPLAY" in line:
                            _update_soc_state(progress=75, step="[3/4] Chuẩn bị Video Nền Gameplay...", msg="🎮 Đang ghép video nền Gameplay 9:16...")
                        elif "BƯỚC 5:" in line or "RENDER VIDEO SHORT" in line:
                            _update_soc_state(progress=90, step="[4/4] Render Video Short (9:16)...", msg="🎬 Đang render Video Short bằng FFmpeg...")
                        elif "HOÀN THÀNH!" in line or "Video lưu tại:" in line:
                            out_name = line.split(":")[-1].strip()
                            _update_soc_state(progress=100, step="✨ Hoàn tất!", msg="✨ Đã tạo Short Video thành công!", last_video=out_name)

                    proc.stdout.close()
                    rc = proc.wait()
                    if rc == 0:
                        _update_soc_state(running=False, progress=100, step="✨ Hoàn thành!", msg="✨ Tiến trình tạo Short Video đã hoàn tất!")
                    else:
                        _update_soc_state(running=False, step="❌ Lỗi render", msg=f"❌ Tiến trình thất bại (Mã lỗi {rc})")
                except Exception as ex:
                    _update_soc_state(running=False, step="❌ Lỗi tiến trình", msg=f"❌ Lỗi: {ex}", add_line=f"❌ Lỗi: {ex}")

            t = threading.Thread(target=_run_socialshorts, daemon=True)
            t.start()

            self._send(200, {"ok": True, "msg": "Đã khởi chạy tiến trình tạo Short Video Reddit/Threads thành công!"})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi khởi chạy tạo Short Video: {str(e)}"})
        return

    elif self.path == "/api/socialshorts/list":
        try:
            out_dir = os.path.join(src_dir, "MediaCrawler", "data", "social_shorts", "videos")
            files = []
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
                        full_p = os.path.join(out_dir, f)
                        files.append({
                            "name": f,
                            "path": full_p,
                            "size": os.path.getsize(full_p),
                            "mtime": os.path.getmtime(full_p)
                        })
            files.sort(key=lambda x: x["mtime"], reverse=True)
            self._send(200, {"ok": True, "files": files, "total": len(files)})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi danh sách: {str(e)}"})
        return
    elif self.path == "/api/open_folder":
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = {}
            if length > 0:
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw.decode('utf-8'))
                except Exception:
                    pass
            folder = body.get("folder") or body.get("path") or ""
            if folder:
                full_p = folder if os.path.isabs(folder) else os.path.join(src_dir, folder)
                os.makedirs(full_p, exist_ok=True)
                os.startfile(full_p)
                self._send(200, {"ok": True, "folder": full_p})
                return
        except Exception as e:
            pass
    elif self.path == "/api/threads/hot_posts":
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = {}
            if length > 0:
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw.decode('utf-8'))
                except Exception:
                    pass
            target = body.get("target") or "@zuck"
            days = int(body.get("days") or 7)
            min_likes = int(body.get("min_likes") or 0)
            limit = int(body.get("limit") or 12)

            import tao_short_social
            posts = tao_short_social.fetch_hot_threads_posts(target_input=target, max_days=days, min_likes=min_likes, limit=limit)
            self._send(200, {"ok": True, "posts": posts, "total": len(posts)})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi tìm bài Threads HOT: {str(e)}"})
        return

    return _orig_do_POST(self)

web_app.Handler.do_POST = _patched_do_POST

_orig_do_GET = web_app.Handler.do_GET
def _patched_do_GET(self):
    if self.path in ("/api/socialshorts/log", "/api/video/log"):
        try:
            with _social_shorts_lock:
                st = dict(_social_shorts_state)
                st["lines"] = list(_social_shorts_state["lines"])
            self._send(200, {"ok": True, **st})
        except Exception as e:
            self._send(500, {"ok": False, "msg": str(e)})
        return
    elif self.path == "/api/nebanguoyen/list":
        try:
            out_dir = os.path.join(src_dir, "MediaCrawler", "data", "ne_ban_quuyen", "videos")
            files = []
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
                        full_p = os.path.join(out_dir, f)
                        files.append({
                            "name": f,
                            "path": full_p,
                            "size": os.path.getsize(full_p),
                            "mtime": os.path.getmtime(full_p)
                        })
            files.sort(key=lambda x: x["mtime"], reverse=True)
            self._send(200, {"ok": True, "files": files, "total": len(files)})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi danh sách: {str(e)}"})
        return
    elif self.path == "/api/socialshorts/list":
        try:
            out_dir = os.path.join(src_dir, "MediaCrawler", "data", "social_shorts", "videos")
            files = []
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
                        full_p = os.path.join(out_dir, f)
                        files.append({
                            "name": f,
                            "path": full_p,
                            "size": os.path.getsize(full_p),
                            "mtime": os.path.getmtime(full_p)
                        })
            files.sort(key=lambda x: x["mtime"], reverse=True)
            self._send(200, {"ok": True, "files": files, "total": len(files)})
        except Exception as e:
            self._send(500, {"ok": False, "msg": f"Lỗi danh sách: {str(e)}"})
        return
    return _orig_do_GET(self)

web_app.Handler.do_GET = _patched_do_GET





# 6. Load custom API keys from config_keys.json if present
config_keys_file = os.path.join(current_dir, "config_keys.json")
if os.path.exists(config_keys_file):
    try:
        import json
        import ai_dich
        with open(config_keys_file, "r", encoding="utf-8") as f:
            keys_data = json.load(f)
            user_keys = keys_data.get("ai_keys", [])
            if user_keys and hasattr(ai_dich, "them_key"):
                for k in user_keys:
                    provider = k.get("provider", "gemini")
                    key_val = k.get("key", "")
                    label = k.get("label", "Custom Key")
                    if key_val:
                        ai_dich.them_key(provider, key_val, label)
                print(f"[MEOWCRAWL STUDIO] Registered {len(user_keys)} custom AI Key(s) to ai_dich store.")
    except Exception as e:
        print(f"[MEOWCRAWL STUDIO] Custom API key loader notice: {e}")

if __name__ == "__main__":
    web_app.main()

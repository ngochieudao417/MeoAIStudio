import os, sys, importlib.util as U, importlib.machinery as M, threading, time, subprocess, traceback

ERR_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mo_dang_nhap_err.log")

def log_err(msg):
    try:
        with open(ERR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

try:
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

orig_argv = list(sys.argv)
sys.argv = [sys.argv[0]]

__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mo_dang_nhap.pyc")
__vc_s = U.spec_from_file_location("_mo_dang_nhap_compiled", __vc_f, loader=M.SourcelessFileLoader("_mo_dang_nhap_compiled", __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules["_mo_dang_nhap_compiled"] = __vc_m

try:
    __vc_s.loader.exec_module(__vc_m)
except SystemExit:
    pass

current_name = __name__
globals().update(__vc_m.__dict__)
__name__ = current_name

def _clean_profile_locks(prof_dir):
    if not prof_dir or not os.path.exists(prof_dir):
        return
    try:
        for root, dirs, files in os.walk(prof_dir):
            for f in files:
                if f.lower() in ("lockfile", "lock", "singletonlock", "singletoncookie", "singletonsocket"):
                    full_p = os.path.join(root, f)
                    try:
                        os.chmod(full_p, 0o777)
                        os.remove(full_p)
                    except Exception:
                        pass
    except Exception:
        pass

def _patched_kill_profile_holders(user_data_dir=""):
    if not user_data_dir:
        return
    try:
        clean_name = os.path.basename(user_data_dir)
        cmd = f'powershell -NoProfile -Command "Get-CimInstance Win32_Process -EA SilentlyContinue | Where-Object {{ $_.CommandLine -like \'*{clean_name}*\' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }}"'
        subprocess.run(cmd, shell=True, creationflags=0x08000000)
    except Exception:
        pass
    _clean_profile_locks(user_data_dir)

def _tim_edge_exe():
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for ep in edge_paths:
        if os.path.exists(ep):
            return ep
    return ""

def _patched_tim_chrome():
    edge = _tim_edge_exe()
    if edge:
        return edge
    pw_chrome = os.path.expanduser(r"~\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe")
    if os.path.exists(pw_chrome):
        return pw_chrome
    sys_chrome = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    for sc in sys_chrome:
        if os.path.exists(sc):
            return sc
    return ""

def mo_edge_school(platform_or_url="dy"):
    url_map = {
        "dy": "https://www.douyin.com",
        "bili": "https://www.bilibili.com",
        "xhs": "https://www.rednote.com",
        "rednote": "https://www.rednote.com",
        "yt": "https://accounts.google.com/ServiceLogin?service=youtube",
        "wb": "https://weibo.com",
        "ks": "https://www.kuaishou.com",
        "tt": "https://www.tiktok.com",
        "fb": "https://www.facebook.com"
    }
    target_url = url_map.get(platform_or_url, platform_or_url)
    if not target_url.startswith("http"):
        target_url = "https://www.douyin.com"

    edge_exe = _tim_edge_exe()
    if not edge_exe:
        log_err("Microsoft Edge executable not found!")
        return False

    log_err(f"Launching Edge School Profile for {platform_or_url} -> {target_url}")
    try:
        cmd = [edge_exe, "--profile-directory=Default", target_url]
        subprocess.Popen(cmd, creationflags=0x00000008) # DETACHED_PROCESS
        print(f"[mo_dang_nhap] Đã mở Edge (School Profile) đăng nhập cho {platform_or_url}!", flush=True)
        return True
    except Exception as e:
        log_err(f"Error launching Edge School Profile: {e}")
        return False

_global_playwright = None
_global_context = None

def _patched_mo_login_youtube():
    global _global_playwright, _global_context
    try:
        edge = _tim_edge_exe()
        if edge:
            return mo_edge_school("yt")
            
        from playwright.sync_api import sync_playwright
        prof_fn = getattr(__vc_m, "yt_profile_dir", None)
        prof = prof_fn() if prof_fn else os.path.expanduser(r"~\AppData\Local\ViralCrawl\yt_chrome_profile")
        os.makedirs(prof, exist_ok=True)
        _patched_kill_profile_holders(prof)
        chrome = _patched_tim_chrome()
        log_err(f"Launching Playwright YouTube Window: browser={chrome}, prof={prof}")
        
        _global_playwright = sync_playwright().start()
        kwargs = {
            "headless": False,
            "args": [
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1180,880",
                "--window-position=120,30"
            ]
        }
        if chrome and os.path.exists(chrome):
            kwargs["executable_path"] = chrome
            
        _global_context = _global_playwright.chromium.launch_persistent_context(prof, **kwargs)
        page = _global_context.pages[0] if _global_context.pages else _global_context.new_page()
        page.goto("https://accounts.google.com/ServiceLogin?service=youtube")
        log_err("Playwright YouTube login window opened successfully!")
        print("[mo_dang_nhap] Cửa sổ Playwright Đăng nhập YouTube/Google đã mở!", flush=True)
        
        while _global_context and len(_global_context.pages) > 0:
            time.sleep(0.8)
            
        return True
    except Exception as e:
        err_str = f"Lỗi mở cửa sổ YouTube Playwright: {e}\n{traceback.format_exc()}"
        log_err(err_str)
        print(err_str, flush=True)
        return False

__vc_m._tim_chrome_that = _patched_tim_chrome
__vc_m._mo_login_youtube_chrome_that = _patched_mo_login_youtube
__vc_m._kill_profile_holders = _patched_kill_profile_holders

globals()["_tim_chrome_that"] = _patched_tim_chrome
globals()["_mo_login_youtube_chrome_that"] = _patched_mo_login_youtube
globals()["_kill_profile_holders"] = _patched_kill_profile_holders
globals()["mo_edge_school"] = mo_edge_school

if hasattr(__vc_m, "main") and hasattr(__vc_m.main, "__globals__"):
    __vc_m.main.__globals__["_tim_chrome_that"] = _patched_tim_chrome
    __vc_m.main.__globals__["_mo_login_youtube_chrome_that"] = _patched_mo_login_youtube
    __vc_m.main.__globals__["_kill_profile_holders"] = _patched_kill_profile_holders
    __vc_m.main.__globals__["mo_edge_school"] = mo_edge_school

def _dua_cua_so_len_tren():
    try:
        time.sleep(1.5)
        import ctypes
        user32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_windows_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if any(k in title for k in ["chrome", "chromium", "douyin", "bilibili", "youtube", "login", "đăng nhập", "edge"]):
                        user32.ShowWindow(hwnd, 9) # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
            return True
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    except Exception:
        pass

if __name__ == "__main__":
    sys.argv = orig_argv
    if hasattr(__vc_m, "sys"):
        __vc_m.sys.argv = orig_argv
    log_err(f"MAIN INVOKED sys.argv={sys.argv}")
    
    # If edge requested explicitly or args supplied
    if len(sys.argv) > 1:
        p = sys.argv[1].lower()
        if p in ["edge", "school", "edge_school"]:
            target = sys.argv[2] if len(sys.argv) > 2 else "dy"
            mo_edge_school(target)
            sys.exit(0)

    threading.Thread(target=_dua_cua_so_len_tren, daemon=True).start()
    if hasattr(__vc_m, "main"):
        try:
            __vc_m.main()
        except Exception as e:
            log_err(f"MAIN EXCEPTION: {e}\n{traceback.format_exc()}")

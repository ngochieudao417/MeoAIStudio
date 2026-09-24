import os, sys, importlib.util as U, importlib.machinery as M, json

__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kiem_tra_login.pyc")
__vc_s = U.spec_from_file_location("_kiem_tra_login_compiled", __vc_f, loader=M.SourcelessFileLoader("_kiem_tra_login_compiled", __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules["_kiem_tra_login_compiled"] = __vc_m

try:
    __vc_s.loader.exec_module(__vc_m)
except SystemExit:
    pass

current_name = __name__
globals().update(__vc_m.__dict__)
__name__ = current_name

def _kiem_tra_edge_cookies():
    try:
        import cookie_decrypt as cd
        edge_ud = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data")
        status = {}
        
        # Douyin check
        dy_cks = cd.doc_cookies(edge_ud, "douyin.com")
        if dy_cks and any(k in dy_cks for k in ["sessionid", "sid_tt", "passport_csrf_token"]):
            status["dy"] = "in"

        # Bilibili check
        bili_cks = cd.doc_cookies(edge_ud, "bilibili.com")
        if bili_cks and any(k in bili_cks for k in ["SESSDATA", "bili_jct", "DedeUserID"]):
            status["bili"] = "in"

        # Xiaohongshu check
        xhs_cks = cd.doc_cookies(edge_ud, "xiaohongshu.com") or cd.doc_cookies(edge_ud, "rednote.com")
        if xhs_cks and any(k in xhs_cks for k in ["a1", "web_session"]):
            status["xhs"] = "in"

        # YouTube / Google check
        yt_cks = cd.doc_cookies(edge_ud, "youtube.com") or cd.doc_cookies(edge_ud, "google.com")
        if yt_cks and any(k in yt_cks for k in ["SAPISID", "HSID", "SID", "LOGIN_INFO"]):
            status["yt"] = "in"

        # Weibo check
        wb_cks = cd.doc_cookies(edge_ud, "weibo.com")
        if wb_cks and any(k in wb_cks for k in ["SUB", "SUBP"]):
            status["wb"] = "in"

        return status
    except Exception:
        return {}

_orig_main = getattr(__vc_m, "main", None)

def main():
    res = {}
    if _orig_main:
        try:
            # We capture output if main prints json or returns dict
            _orig_main()
        except Exception:
            pass
    
    # Merge Edge cookie checks
    edge_status = _kiem_tra_edge_cookies()
    if edge_status:
        try:
            status_file = getattr(__vc_m, "FILE_LOGIN_CHECK", None)
            if not status_file:
                status_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "login_check_status.json")
            
            existing = {}
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    pass
            
            for k, v in edge_status.items():
                if existing.get(k) != "in":
                    existing[k] = v
                    
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(existing, f)
            print("LOGIN_CHECK_DONE " + json.dumps(existing), flush=True)
        except Exception:
            pass

globals()["main"] = main

if __name__ == "__main__":
    main()

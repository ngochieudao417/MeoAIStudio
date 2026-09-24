import os, sys, importlib.util as U, importlib.machinery as M, json, base64, ctypes, ctypes.wintypes, sqlite3, shutil, tempfile, subprocess

__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie_decrypt.pyc")
__vc_s = U.spec_from_file_location("_cookie_decrypt_compiled", __vc_f, loader=M.SourcelessFileLoader("_cookie_decrypt_compiled", __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules["_cookie_decrypt_compiled"] = __vc_m

try:
    __vc_s.loader.exec_module(__vc_m)
except SystemExit:
    pass

globals().update(__vc_m.__dict__)

_orig_doc_cookies = getattr(__vc_m, "doc_cookies", None)
_orig_cookie_header = getattr(__vc_m, "cookie_header", None)

def get_edge_cookies_raw(host_substr, user_data_dir=None):
    if not user_data_dir or not os.path.exists(user_data_dir):
        user_data_dir = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data")
    if not os.path.exists(user_data_dir):
        return {}

    ls_path = os.path.join(user_data_dir, "Local State")
    ck_path = os.path.join(user_data_dir, "Default", "Network", "Cookies")
    if not os.path.exists(ls_path) or not os.path.exists(ck_path):
        return {}

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    def dpapi_decrypt(b):
        in_b = DATA_BLOB(len(b), ctypes.create_string_buffer(b, len(b)))
        out_b = DATA_BLOB()
        if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(in_b), None, None, None, None, 0, ctypes.byref(out_b)):
            d = ctypes.string_at(out_b.pbData, out_b.cbData)
            ctypes.windll.kernel32.LocalFree(out_b.pbData)
            return d
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        with open(ls_path, "r", encoding="utf-8") as f:
            encrypted_key = base64.b64decode(json.load(f)["os_crypt"]["encrypted_key"])[5:]
        key = dpapi_decrypt(encrypted_key)
        if not key:
            return {}
        aesgcm = AESGCM(key)
    except Exception:
        return {}

    tmp_db = tempfile.mktemp(".sqlite")
    copied = False
    try:
        shutil.copy2(ck_path, tmp_db)
        copied = True
    except Exception:
        r = subprocess.run(["cmd.exe", "/c", "copy", "/y", ck_path, tmp_db], capture_output=True)
        if os.path.exists(tmp_db) and os.path.getsize(tmp_db) > 0:
            copied = True

    if not copied or not os.path.exists(tmp_db):
        return {}

    cookies = {}
    try:
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute("SELECT host_key, name, encrypted_value, value FROM cookies WHERE host_key LIKE ?", (f"%{host_substr}%",))
        for host, name, enc_val, val in c.fetchall():
            if val:
                cookies[name] = val
            elif enc_val:
                try:
                    nonce = enc_val[3:15]
                    ciphertext = enc_val[15:]
                    dec = aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
                    cookies[name] = dec
                except Exception:
                    pass
        conn.close()
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_db):
            try: os.remove(tmp_db)
            except Exception: pass

    return cookies

def doc_cookies(user_data_dir="", host_substr=""):
    res = {}
    if _orig_doc_cookies:
        try:
            res = _orig_doc_cookies(user_data_dir, host_substr)
        except Exception:
            pass
    if not res:
        res = get_edge_cookies_raw(host_substr, user_data_dir)
    return res

def cookie_header(user_data_dir="", host_substr=""):
    cks = doc_cookies(user_data_dir, host_substr)
    if not cks:
        return ""
    return "; ".join([f"{k}={v}" for k, v in cks.items()])

globals()["doc_cookies"] = doc_cookies
globals()["cookie_header"] = cookie_header
globals()["get_edge_cookies_raw"] = get_edge_cookies_raw

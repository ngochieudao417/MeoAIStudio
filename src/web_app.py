import os, sys, importlib.util as U, importlib.machinery as M
__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_app.pyc")
__vc_s = U.spec_from_file_location(__name__, __vc_f, loader=M.SourcelessFileLoader(__name__, __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules[__name__] = __vc_m
__vc_s.loader.exec_module(__vc_m)

# The backend is distributed as bytecode. Keep its runtime in personal mode
# for every launcher, including launchers that do not use local_server.py.
__vc_m.TIER = "unlimited"
__vc_m._tier_kind = "ok"
__vc_m._signed_tier = "unlimited"
__vc_m._signed_lohapage = True
__vc_m.LOHAPAGE_OK = True
__vc_m._tier_tu_token_ky = lambda: ("ok", "unlimited", True)
__vc_m._refresh_tier = lambda: "personal"

def _without_commerce(handler):
    return handler.path.split("?", 1)[0].startswith(("/api/goi", "/api/payment/"))

_original_get = __vc_m.Handler.do_GET
_original_post = __vc_m.Handler.do_POST

def _personal_get(self):
    if _without_commerce(self):
        self._send(404, {"ok": False, "msg": "Chức năng này đã được gỡ bỏ."})
        return
    return _original_get(self)

def _personal_post(self):
    if _without_commerce(self):
        self._send(404, {"ok": False, "msg": "Chức năng này đã được gỡ bỏ."})
        return
    return _original_post(self)

__vc_m.Handler.do_GET = _personal_get
__vc_m.Handler.do_POST = _personal_post
if __name__ != "__main__":
    globals().update(__vc_m.__dict__)

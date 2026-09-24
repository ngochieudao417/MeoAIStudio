import os, sys, importlib.util as U, importlib.machinery as M
__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tai_honggo.pyc")
__vc_s = U.spec_from_file_location(__name__, __vc_f, loader=M.SourcelessFileLoader(__name__, __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules[__name__] = __vc_m
__vc_s.loader.exec_module(__vc_m)

# Patch tai_tap and tai_mp4 to retry on Windows PermissionError [WinError 32] during file rename
_orig_tai_tap = getattr(__vc_m, "tai_tap", None)
if _orig_tai_tap:
    def _patched_tai_tap(*args, **kwargs):
        import time
        for attempt in range(5):
            try:
                return _orig_tai_tap(*args, **kwargs)
            except PermissionError as pe:
                if attempt < 4:
                    print(f"⚠️ [RETRY] File lock detected ({pe}). Retrying in 1s ({attempt+1}/5)...", flush=True)
                    time.sleep(1.0)
                else:
                    raise
    __vc_m.tai_tap = _patched_tai_tap

_orig_tai_mp4 = getattr(__vc_m, "tai_mp4", None)
if _orig_tai_mp4:
    def _patched_tai_mp4(*args, **kwargs):
        import time
        for attempt in range(5):
            try:
                return _orig_tai_mp4(*args, **kwargs)
            except PermissionError as pe:
                if attempt < 4:
                    print(f"⚠️ [RETRY] File lock detected ({pe}). Retrying in 1s ({attempt+1}/5)...", flush=True)
                    time.sleep(1.0)
                else:
                    raise
    __vc_m.tai_mp4 = _patched_tai_mp4

if __name__ != "__main__":
    globals().update(__vc_m.__dict__)

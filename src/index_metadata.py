import os, sys, importlib.util as U, importlib.machinery as M
__vc_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_metadata.pyc")
__vc_s = U.spec_from_file_location(__name__, __vc_f, loader=M.SourcelessFileLoader(__name__, __vc_f))
__vc_m = U.module_from_spec(__vc_s)
__vc_m.__file__ = __vc_f
sys.modules[__name__] = __vc_m
__vc_s.loader.exec_module(__vc_m)
if __name__ != "__main__":
    globals().update(__vc_m.__dict__)

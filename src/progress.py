"""Thanh tiến trình gọn, không thêm dependency.

- Terminal thật (TTY): vẽ 1 dòng cập nhật tại chỗ bằng '\r'  ->  giọng [████████░░░░] 62% 74/120  ETA 0:48
- Khi ghi log/redirect (không TTY): in mốc % thưa (mặc định mỗi ~2%) kèm ETA để không spam mà vẫn theo dõi được.
"""
from __future__ import annotations
import sys
import time


def _fmt_time(s: float) -> str:
    s = int(max(0, s))
    if s >= 3600:
        return f"{s // 3600:d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60:d}:{s % 60:02d}"


class Bar:
    def __init__(self, total: float, label: str = "", width: int = 24, stream=None, step: int = 2):
        self.total = max(1e-9, float(total))
        self.label = label
        self.width = width
        self.s = stream or sys.stdout
        self.tty = bool(getattr(self.s, "isatty", lambda: False)())
        self.step = max(1, int(step))      # non-TTY: in khi % tăng >= step
        self.start = time.time()
        self._last_pct = -1
        self._closed = False

    def _eta(self, current: float) -> str:
        el = time.time() - self.start
        if current <= 0 or el < 0.5:
            return ""
        rate = current / el
        if rate <= 0:
            return ""
        rem = (self.total - current) / rate
        if rem <= 0:
            return ""
        return f"  ETA {_fmt_time(rem)}"

    def update(self, current: float, suffix: str = ""):
        pct = max(0, min(100, int(current * 100 / self.total)))
        eta = self._eta(current)
        if self.tty:
            fill = int(self.width * pct / 100)
            barstr = "█" * fill + "░" * (self.width - fill)
            self.s.write(f"\r  {self.label:<7}[{barstr}] {pct:3d}%  {suffix}{eta}   ")
            self.s.flush()
        elif pct >= self._last_pct + self.step:
            self._last_pct = pct
            self.s.write(f"  {self.label} {pct}%  {suffix}{eta}\n")
            self.s.flush()

    def finish(self, msg: str = ""):
        if self._closed:
            return
        self._closed = True
        if self.tty:
            self.s.write("\r" + " " * (self.width + 56) + "\r")
            self.s.flush()
        if msg:
            self.s.write(f"  {msg}\n")
            self.s.flush()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.finish()

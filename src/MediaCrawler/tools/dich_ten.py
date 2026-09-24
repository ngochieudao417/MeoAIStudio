# -*- coding: utf-8 -*-
"""Dịch TIÊU ĐỀ video (Trung) sang ngôn ngữ đích để ĐẶT TÊN FILE khi cào
douyin/bilibili/xhs — không chỉ dịch hiển thị trên màn hình.

- Ngôn ngữ đích đọc qua env TARGET_LANG (vi/en) do web_app truyền vào subprocess cào.
- Dùng Google Translate web (không cần key), cache theo từng nền tảng để khỏi gọi lại.
- Không có chữ Trung -> giữ nguyên (đỡ tốn request). Lỗi mạng -> trả về gốc, KHÔNG cache (để thử lại lần sau).
- XOÁ HASHTAG ngay đầu dich_tieu_de -> áp cho CẢ douyin/bilibili/xhs từ MỘT chỗ (xem bo_hashtag).
- Ngoài hashtag thì KHÔNG làm sạch/cắt ở đây: chỗ gọi đã bọc _safe_name(...) để bỏ ký tự cấm + cắt độ dài.
"""
import json
import os
import re
import threading
import urllib.parse
import urllib.request

import config

_CACHE = {}            # {đường_dẫn_cache: {tiêu đề gốc: bản dịch}}
_LOCK = threading.Lock()


def _data_base() -> str:
    return config.SAVE_DATA_PATH if config.SAVE_DATA_PATH else "data"


def _target_lang() -> str:
    tl = (os.environ.get("TARGET_LANG") or "vi").strip().lower()
    return tl if tl in ("vi", "en") else "vi"


def _ma_lang_an_toan(s: str) -> str:
    """Mã ngôn ngữ truyền tay → chuỗi an toàn để ghép vào URL và TÊN FILE cache. Rỗng nếu không hợp lệ.
    Chỉ nhận dạng `vi` · `en` · `fil` · `zh-CN` — đúng bộ mã mà `tl=` của Google dùng."""
    s = (s or "").strip()
    return s if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?", s or "") else ""


def _co_chu_trung(s: str) -> bool:
    return any("一" <= c <= "鿿" for c in (s or ""))


def _load_cache(path: str) -> dict:
    if path not in _CACHE:
        c = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    c = json.load(f)
            except Exception:
                c = {}
        _CACHE[path] = c
    return _CACHE[path]


# '#' thường LẪN '＃' full-width (tiêu đề Trung/Douyin hay dùng bản full-width).
_RE_HASHTAG = re.compile(r"\s*[#＃][^\s#＃]+")


def bo_hashtag(text: str) -> str:
    """Bỏ MỌI hashtag khỏi tiêu đề trước khi dùng làm TÊN FILE.

    Tiêu đề video reup thường là cả 'rừng' hashtag ('… #havefuninsaigon #ZenergyPro #CT9 #bar #club …')
    ⇒ tên file dài lê thê, và cộng với thư mục sâu thì vượt MAX_PATH 260 của Windows — đã gây lỗi THẬT
    `WinError 3` ở bước lồng tiếng trên máy khách (đường dẫn 263 ký tự). Bỏ hashtag vừa gọn tên vừa
    cắt tận gốc rủi ro đó.
    TOÀN hashtag (bỏ xong còn rỗng) → GIỮ NGUYÊN gốc: thà tên xấu còn hơn mọi video thành cùng một tên."""
    t = (text or "").strip()
    if not t:
        return t
    _sach = _RE_HASHTAG.sub(" ", t)
    _sach = re.sub(r"\s{2,}", " ", _sach).strip(" -_·|,.")
    return _sach or t


def _bat_dich_ten() -> bool:
    """Công tắc "Dịch tiêu đề khi đặt tên file" (tab Cài đặt). Mặc định BẬT = hành vi cũ.

    🔴 09/09/2026 — chủ dự án: *"thêm 1 nút không dịch tên file … để họ đặt tên theo tiêu đề gốc"*.
    Có khách muốn giữ NGUYÊN tiêu đề gốc làm tên file (tra ngược về bài gốc / đối chiếu kênh nguồn).

    VÌ SAO CÔNG TẮC NẰM Ở ĐÂY, KHÔNG Ở 4 CHỖ GỌI: bốn đường đặt tên file —
    `bilibili/core.py:82` · `douyin/core.py:186` · `xhs/core.py:67` · `tai_ytdlp._dich_tieu_de_trung`
    — đều đi qua ĐÚNG hàm `dich_tieu_de` này. `web_app` đặt env một lần (`_ap_env_dich_ten`) rồi mọi
    tiến trình cào thừa hưởng qua `os.environ.copy()`. Sửa ở 4 chỗ là đúng cảnh "tắt một tính năng =
    sửa 4 chỗ, sót là chắc" mà CLAUDE.md cảnh báo.
    """
    return (os.environ.get("DICH_TEN_FILE") or "1").strip() != "0"


def dich_tieu_de(text: str, platform: str, lang: str = "", cho_ten_file: bool = True) -> str:
    """Dịch tiêu đề video Trung -> ngôn ngữ đích; cache theo nền tảng.
    Không có chữ Trung -> giữ nguyên. Lỗi/không dịch được -> trả về gốc.
    XOÁ HASHTAG trước tiên — đặt ở đây vì đây là chốt DUY NHẤT mà cả 3 nền (douyin/bilibili/xhs) đều đi qua
    khi dựng tên file; sửa ở 3 hàm _safe_name riêng lẻ thì sót là chắc.

    🔴 27/08/2026 — THAM SỐ `lang`. TRƯỚC ĐÂY chỉ đọc `TARGET_LANG` của TIẾN TRÌNH, mà env đó chỉ được
    đặt cho tiến trình render CON; bước dựng caption chạy trong thread của tiến trình CHA nên luôn lấy
    cài đặt CHUNG. Hậu quả từ khi có đa ngôn ngữ (26/08): Page tiếng Anh nhận video tiếng Anh nhưng
    **caption tiếng Việt** — mà caption CHÍNH LÀ thứ người xem đọc trước. Truyền `lang` vào là hết.
    ⚠ `_target_lang()` kẹp về vi/en (đúng cho đường crawler cũ, giữ nguyên). Còn `lang` truyền TAY thì
      KHÔNG kẹp — điểm cuối Google nhận nhiều mã hơn thế, kẹp ở đây là chặn mất Page tiếng Thái/Nhật…
      Chỉ lọc ký tự cho an toàn khi ghép vào URL + tên file cache.
    """
    text = bo_hashtag((text or "").strip())
    if not text or not _co_chu_trung(text):
        return text
    # 🔴 Công tắc TẮT ⇒ trả NGUYÊN tiêu đề gốc để đặt tên file. Hai điểm cố ý:
    #   · VẪN bỏ hashtag ở trên — đó là để chặn MAX_PATH 260 của Windows (đã gây `WinError 3` THẬT ở
    #     bước lồng tiếng, đường dẫn 263 ký tự), không liên quan gì tới dịch.
    #   · `cho_ten_file=False` = lời gọi dựng CAPTION (`web_app._kn_caption_tu_stem`) — caption là thứ
    #     người xem đọc TRƯỚC cả video, phải dịch bất kể công tắc TÊN FILE.
    if cho_ten_file and not _bat_dich_ten():
        return text
    lang = _ma_lang_an_toan(lang) or _target_lang()
    path = os.path.join(_data_base(), platform, f"_tieude_{lang}.json")
    c = _load_cache(path)
    if text in c:
        return c[text]
    # Tiêu đề douyin hay kèm cả "rừng" hashtag -> cắt nguồn ~120 ký tự cho gọn request
    # (chỗ gọi vẫn cắt tiếp về 50-60 nên không mất gì).
    nguon = text[:120]

    def _ep_gtx():
        url = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl=zh-CN&tl=" + lang + "&dt=t&q=" + urllib.parse.quote(nguon))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        return "".join(s[0] for s in d[0] if s and s[0]).strip()

    def _ep_clients5():
        url = ("https://clients5.google.com/translate_a/t?client=dict-chrome-ex"
               "&sl=zh-CN&tl=" + lang + "&q=" + urllib.parse.quote(nguon[:900]))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        v = d
        while isinstance(v, list) and v:
            v = v[0]
        return v.strip() if isinstance(v, str) else ""

    def _ep_mymemory():
        url = ("https://api.mymemory.translated.net/get?langpair="
               + urllib.parse.quote("zh-CN|" + lang) + "&q=" + urllib.parse.quote(nguon[:480]))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ra = str((d.get("responseData") or {}).get("translatedText") or "").strip()
        # MyMemory nhet CAU BAO LOI vao chinh `translatedText` va van tra 200 (quota / cap ngon ngu la).
        # Chung LUON in HOA toan bo + chua tu khoa duoi day -> coi la HONG, tra rong.
        u = ra.upper()
        if ra and ra == u and any(k in u for k in (
                "INVALID", "MYMEMORY WARNING", "QUERY LENGTH LIMIT", "EXCEEDED", "PLEASE CONTACT")):
            return ""
        return ra

    # 🔴 28/08/2026 — BA DIEM CUOI, truoc day CHI CO MOT (gtx).
    # Ham nay dat TEN FILE, ma ten file chi dat DUNG MOT LAN: hong phat nao la chu Han dong dinh
    # VINH VIEN vao ten video, moi chang sau (caption, ten file giao LoHa) deu keo theo. Do tren kho
    # that: 29/87 file cao ve con chu Han, trong do 27 file KHONG co muc nao trong kho dem — dung dau
    # van "that bai KHONG duoc cache". Doi lai, giao dien dich lai MOI LAN mo danh sach nen luon ra
    # tieng Viet => khach thay "cao ve tieng Viet ma render ra tieng Trung".
    # Thu tu lay theo so do cua `phu_de._dich_vi` (do 27/08 tren 5 tieu de that):
    #   clients5 4/5 · 0,27s  |  gtx 4/5 · 1,55s (chu ra GIONG HET)  |  MyMemory 5/5 · 1,22s (kem hon)
    # => clients5 truoc (nhanh gap ~6, cung ket qua), MyMemory CHOT vi cuu duoc ca ca hai kia thua.
    vi = ""
    for _goi in (_ep_clients5, _ep_gtx, _ep_mymemory):
        try:
            ra = _goi()
        except Exception:
            continue
        if ra and ra.strip() != text.strip():
            vi = ra.strip()
            break
    if not vi:
        # KHONG cache that bai (de lan sau thu lai) — nhung PHAI noi ra: im lang o day chinh la
        # cach chu Han lot vao ten file ma khong ai biet.
        try:
            print("[dich_ten] ⚠ Ca 3 diem cuoi dich deu thua — GIU NGUYEN tieu de goc: %s" % text[:50])
        except Exception:
            pass
        return text
    with _LOCK:
        c[text] = vi
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return vi

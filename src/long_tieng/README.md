# Lồng tiếng video (PoC) — zh → vi, KHÔNG dùng LLM

Tự động: tách giọng từ video → dịch → lồng tiếng Việt. Dùng cho **học tập/nghiên cứu**.

## Pipeline
```
Video → FFmpeg (tách audio) → faster-whisper (ASR + timestamp)
      → Google Dịch (zh→vi) → edge-tts (giọng Việt) → ép khớp + ghép video
```
| Bước | Công cụ | License |
|------|---------|---------|
| Tách audio | FFmpeg (đã bundle) | — |
| ASR tiếng Trung | faster-whisper | MIT |
| Dịch zh→vi | deep-translator (Google) | MIT (endpoint Google free) |
| TTS giọng Việt | edge-tts (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`) | free MS |
| Ghép/ép tiếng | FFmpeg | — |

## Cài đặt
**Core (cơ bản)** đã nằm trong `Meowcrawler/pyproject.toml` → bản cài app **tự có** sau first-run setup (`uv sync`). Chạy lẻ thì:
```powershell
Meowcrawler\.venv\Scripts\python.exe -m pip install -r long_tieng\requirements.txt
```
**Nâng cao (Demucs/NLLB/viXTTS ~5GB):** bấm nút **"⬇ Cài bản nâng cao"** trong tab Lồng tiếng,
hoặc chạy 1 lệnh:
```powershell
Meowcrawler\.venv\Scripts\python.exe long_tieng\cai_nangcao.py
```
> Lần chạy đầu, faster-whisper tự tải model (`small` ~0.5GB, `large-v3` ~3GB) về cache.
> Cần **internet** cho: tải model (1 lần), Google Dịch, edge-tts.

## Dùng
```powershell
# cơ bản
python long_tieng\long_tieng.py "video.mp4" -o "video_vi.mp4"

# chất lượng cao hơn (chậm hơn)
python long_tieng\long_tieng.py "video.mp4" --model large-v3

# giữ nhạc nền gốc, phủ giọng Việt lên (hạ nhỏ tiếng gốc)
python long_tieng\long_tieng.py "video.mp4" --keep-bg

# giọng nam
python long_tieng\long_tieng.py "video.mp4" --voice vi-VN-NamMinhNeural
```

Xuất ra: `video_vi.mp4` + phụ đề `video_vi.vi.srt`. Cuối log in 5 đoạn đối chiếu zh→vi để bạn đánh giá chất lượng dịch.

## Hạn chế PoC (đã biết)
- Dịch tiếng lóng/trend chưa thật mượt (không dùng LLM) — Google đã là tốt nhất trong nhóm free.
- Khớp tiếng theo từng đoạn (ép tốc độ ≤1.6x), không lip-sync theo môi.
- Chưa tách nhạc nền bằng AI (Demucs) — `--keep-bg` chỉ hạ nhỏ tiếng gốc rồi trộn.

## Đã tích hợp vào tool (web UI)
Có nút **🎙️ Lồng tiếng** trong sidebar web UI: chọn video đã tải → chọn giọng (nam/nữ) →
chọn nền (thay hẳn / giữ nền hạ nhỏ / **tách nhạc nền AI**) → bộ dịch → TTS → **Bắt đầu**.
Chạy nền, có **thanh % tiến trình** + log. Kết quả lưu cạnh video gốc (`_vi.mp4` + `.vi.srt`).
- Backend: `web_app.py` endpoints `/api/dub/{start,stop,log,engines}` (job qua subprocess `long_tieng.py`, parse `[NN%]`).
- Frontend: section `v-dub` trong `web/index.html` (poll `/api/dub/log` mỗi 1.5s).

## Backend nâng cao (tuỳ chọn — `--sep/--mt/--tts`)
Tool **tự phát hiện** backend đã cài; chưa cài thì option bị làm mờ và **tự fallback**.
Cài: `pip install -r long_tieng/requirements_nangcao.txt`.

| Cờ | Giá trị | Yêu cầu | Trạng thái (đã verify) |
|----|---------|---------|------------|
| `--sep` | `demucs` | demucs + soundfile | ✅ tách nhạc nền AI sạch (Python API, né torchcodec) — ~8s |
| `--mt` | `nllb` | transformers 4.56 + sentencepiece + model nllb-ct2 | ✅ dịch offline thẳng zh→vi, chất lượng tương đương Google |
| `--tts` | `xtts` (+ `--ref`) | coqui-tts + torchcodec + viXTTS + ffmpeg-shared | ✅ clone giọng Việt từ giọng gốc — CPU ~30s/câu; **GPU: load 1 lần ~30s rồi ~2-3s/câu** |

- Lồng tiếng tự **trích 8s giọng gốc** làm mẫu clone nếu không truyền `--ref`.
- Cài nâng cao: `pip install -r long_tieng/requirements_nangcao.txt` + tải model (xem file đó).
- `transformers` PHẢI pin **4.56.0** (5.x vỡ XTTS, <4.50 thiếu hàm). torchcodec cần **FFmpeg shared DLLs** ở `models/ffmpeg-shared/bin` (code tự nạp + tự patch tokenizer 'vi').

> Mặc định **Google + edge-tts** đã tốt + NHANH. Nâng cao chỉ khi cần: offline (NLLB) / nhạc nền sạch (Demucs) / clone giọng (XTTS, chấp nhận chậm trên CPU).

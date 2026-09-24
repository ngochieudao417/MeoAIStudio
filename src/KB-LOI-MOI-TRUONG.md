# KB — LỖI MÔI TRƯỜNG MÁY KHÁCH (chẩn đoán & vá nóng)

> Sổ tay tra cứu khi khách báo **render lỗi / mất phụ đề / máy mạnh mà chạy chậm**.
> Tổng hợp từ **6 máy thật trong một buổi (07–08/08/2026, bản 1.6.2 & 1.6.3)**.
> Mọi lệnh trong file đã chạy thật trên máy khách hoặc trên venv nháp, không phải viết ra rồi đưa.

---

## 0. LUẬT QUAN TRỌNG NHẤT — đừng tin câu báo lỗi trên màn hình

Câu thân thiện app hiện ra được **suy từ TỪ KHOÁ** trong log, nên nó sai hướng thường xuyên:

| App nói | Sự thật đã gặp |
|---|---|
| *"kiểm tra mạng rồi thử lại"* | gói `onnxruntime` hỏng — mạng hoàn toàn khoẻ |
| *"chạy sai môi trường, đóng app mở lại"* | thư mục `onnxruntime` mất hẳn trên đĩa |
| *"Mạng gián đoạn"* (setup 54%) | uv dựng venv bằng Python **32-bit** |
| *"Lỗi tăng tốc GPU, tắt tăng tốc đi"* | xung đột 2 bộ cuDNN |
| **không báo gì cả** | torch sai bản CUDA → demucs âm thầm chạy CPU |

**⇒ Luôn đọc `_loi_render.log` hoặc chạy Lệnh 1 trước khi kết luận.**

Log nằm ở `<thư mục lưu>/data/_loi_render.log`. Khách đổi ổ lưu thì nó theo ổ đó
(đã gặp: `D:\processed_videos\data\_loi_render.log`), **không** phải luôn ở `%APPDATA%`.

---

## 1. LỆNH 1 — CHẨN ĐOÁN (chạy đầu tiên, chỉ đọc, không cần Admin)

```powershell
$ErrorActionPreference="SilentlyContinue"; $py="$env:APPDATA\viralcrawl-desktop\runtime\venv\Scripts\python.exe"; $sp="$env:APPDATA\viralcrawl-desktop\runtime\venv\Lib\site-packages"; $drv=(Get-PSDrive -PSProvider FileSystem).Root; $vc=@(); foreach($d in $drv){ $vc += @(Get-ChildItem $d -Depth 3 -Directory -Filter "ViralCrawl" | Select-Object -ExpandProperty FullName) }; $vc=@(@("C:\Program Files\ViralCrawl","$env:LOCALAPPDATA\Programs\ViralCrawl")+$vc | Select-Object -Unique | Where-Object {Test-Path "$_\resources\app-src\phu_de.py"}); Write-Host "===== 1. CAI O DAU ====="; if($vc){ $vc | ForEach-Object { Write-Host "  $_" } } else { Write-Host "  !! KHONG THAY ban cai nao" }; Write-Host "  uv.exe : $(($vc | ForEach-Object {"$_\resources\vendor\uv.exe"} | Where-Object {Test-Path $_} | Select-Object -First 1))"; Write-Host "  python : $py  (co: $(Test-Path $py))"; Write-Host "`n===== 2. ONNXRUNTIME ====="; if(Test-Path "$sp\onnxruntime"){ $n=(Get-ChildItem "$sp\onnxruntime" | Select-Object -ExpandProperty Name) -join ", "; Write-Host "  thu muc chua: $n"; if($n -notmatch "capi"){ Write-Host "  >>> THIEU 'capi' = GO DO DANG = DUNG BENH NAY" } } else { Write-Host "  KHONG CO thu muc onnxruntime" }; Get-ChildItem $sp -Directory -Filter "onnxruntime*dist-info" | ForEach-Object { Write-Host "  metadata: $($_.Name)" }; & $py -c "import onnxruntime as o;print('  import OK  ',o.__version__);print('  SessionOpt ',type(o.SessionOptions()).__name__);print('  providers  ',o.get_available_providers())"; if($LASTEXITCODE -ne 0){ Write-Host "  >>> ONNXRUNTIME HONG - day la loi lam CHET RENDER" }; Write-Host "`n===== 3. TORCH + GPU ====="; & $py -c "import torch,os;print('  torch        ',torch.__version__);print('  cuda_available',torch.cuda.is_available());print('  torch/lib dll',len([x for x in os.listdir(os.path.join(os.path.dirname(torch.__file__),'lib')) if x.endswith('.dll')]))"; if(Get-Command nvidia-smi){ Write-Host "  GPU: $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader)" } else { Write-Host "  GPU: KHONG co nvidia-smi" }; Write-Host "`n===== 4. LOI GOC ====="; $lg=@(@("$env:APPDATA\viralcrawl-desktop\data\_loi_render.log") | Where-Object {Test-Path $_}); foreach($d in $drv){ $lg += @(Get-ChildItem $d -Depth 3 -Filter "_loi_render.log" | Select-Object -ExpandProperty FullName) }; $lg=@($lg | Select-Object -Unique | Sort-Object {(Get-Item $_).LastWriteTime} -Descending); if($lg){ Write-Host "  file: $($lg[0])"; Get-Content $lg[0] -Tail 6 -Encoding UTF8 } else { Write-Host "  (chua co log loi)" }
```

### Đọc kết quả

| Thấy gì trong output | Bệnh | Đi tới |
|---|---|---|
| Mục 2 thiếu `capi`, chỉ còn `quantization, tools` | onnxruntime gỡ dở dang | **§2** |
| Mục 2 `KHONG CO thu muc onnxruntime` mà vẫn có metadata | onnxruntime mất hẳn | **§2** |
| Mục 2 có **2 dòng** metadata (`onnxruntime-*` + `onnxruntime_gpu-*`) | LIB-02: bản CPU đè bản GPU | **§3** |
| Mục 2 providers **không có** `CUDAExecutionProvider` mà máy có NVIDIA | OCR chạy CPU | **§3** |
| Mục 3 `torch …+cpu` mà máy có NVIDIA | cài nhầm bản CPU | **§4** |
| Mục 3 GPU `compute_cap` = **12.0** mà torch là `+cu126` | Blackwell thiếu kernel | **§4** |
| Mục 4 có `WinError 127 … cudnn_cnn64_9.dll` | xung đột 2 bộ cuDNN | **§5** |
| Mục 1 hiện **2 dòng** bản cài | 2 bản song song | **§6** |
| Setup kẹt 54%, chưa cài xong | Python 32-bit | **§7** |

---

## 2. onnxruntime GỠ DỞ DANG — bệnh phổ biến nhất (3/6 máy)

**Triệu chứng khách thấy:** render dừng ở bước *"Lấy lời thoại gốc"*, app báo *"kiểm tra mạng"*.

**Chữ ký trong log** (3 mức độ hỏng, cùng một bệnh):
```
AttributeError: module 'onnxruntime' has no attribute 'SessionOptions'     ← còn thư mục, mất capi/+__init__.py
ModuleNotFoundError: No module named 'onnxruntime'                          ← mất HẲN thư mục
ImportError: cannot import name '…' from 'onnxruntime' (unknown location)   ← namespace rỗng
```

**Gốc:** gói bị gỡ nửa chừng nhưng `.dist-info` **vẫn còn** ⇒ uv/pip tưởng đã cài đủ và bỏ qua.
⇒ **Bấm "⚡ Cài/sửa tăng tốc GPU" bao nhiêu lần cũng KHÔNG khỏi** — đã xác nhận trên máy khách.
Phải xoá cứng thư mục + metadata rồi cài lại.

**Lệnh 2 — chữa.** Đóng **hẳn** app trước (Task Manager → `ViralCrawl.exe` **trước**, rồi `pythonw.exe`;
làm ngược lại thì Electron bật lại backend). Không cần Admin.

```powershell
$ErrorActionPreference="SilentlyContinue"; $py="$env:APPDATA\viralcrawl-desktop\runtime\venv\Scripts\python.exe"; $sp="$env:APPDATA\viralcrawl-desktop\runtime\venv\Lib\site-packages"; $drv=(Get-PSDrive -PSProvider FileSystem).Root; $vc=@(); foreach($d in $drv){ $vc += @(Get-ChildItem $d -Depth 3 -Directory -Filter "ViralCrawl" | Select-Object -ExpandProperty FullName) }; $vc=@(@("C:\Program Files\ViralCrawl","$env:LOCALAPPDATA\Programs\ViralCrawl")+$vc | Select-Object -Unique); $uv=($vc | ForEach-Object {"$_\resources\vendor\uv.exe"} | Where-Object {Test-Path $_} | Select-Object -First 1); if(-not $uv){ Write-Host "!! KHONG THAY uv.exe"; return }; $run=@(Get-Process -Name ViralCrawl,pythonw); if($run){ Write-Host "!! APP DANG CHAY ($($run.Count) tien trinh) - dong HAN roi chay lai"; return }; & $py -c "import onnxruntime as o;o.SessionOptions();print('  -> VAN DUNG DUOC, KHONG CAN CHUA')"; if($LASTEXITCODE -eq 0){ Write-Host "== DUNG LAI: onnxruntime khong hong. Loi may nay nam cho khac."; return }; Remove-Item "$sp\onnxruntime" -Recurse -Force; Get-ChildItem $sp -Directory -Filter "onnxruntime*dist-info" | Remove-Item -Recurse -Force; $goi = if(Get-Command nvidia-smi){"onnxruntime-gpu==1.22.0"} else {"onnxruntime==1.22.0"}; & $uv pip install --python $py --no-cache --no-deps $goi; & $py -c "import onnxruntime as o;print('  ',o.__version__,o.get_available_providers())"
```

**Đạt khi:** in `1.22.0` và (máy có NVIDIA) providers chứa `CUDAExecutionProvider`.
Lệnh này **từ chối đụng vào gói đang lành** — chạy nhầm cũng không hỏng gì.

> ⚠ Nếu vài hôm sau hỏng lại: nghi **phần mềm diệt virus cách ly** (onnxruntime nhiều `.dll` không ký số).
> Mở lịch sử cách ly của AV, thêm ngoại lệ cho `%APPDATA%\viralcrawl-desktop\runtime\venv`.

---

## 3. LIB-02 — bản CPU đè bản GPU (OCR chạy CPU)

**Triệu chứng:** không báo lỗi, chỉ **chậm**. OCR không dùng GPU.

**Chữ ký (Lệnh 1 mục 2):**
```
metadata: onnxruntime-1.26.0.dist-info        ← bản CPU
metadata: onnxruntime_gpu-1.22.0.dist-info    ← bản GPU
providers ['AzureExecutionProvider','CPUExecutionProvider']    ← MẤT CUDA
```

**Gốc:** `uv.lock` ghim `onnxruntime==1.26.0` (bản CPU, do `rapidocr-onnxruntime` kéo theo) còn `cai_gpu.py`
cài `onnxruntime-gpu==1.22.0` — **cùng một thư mục module**. Cái cài sau đè cái trước.

**Chữa:** dùng đúng **Lệnh 2** nhưng bỏ đoạn kiểm "còn dùng được thì dừng" (vì gói vẫn import được, chỉ sai bản):

```powershell
$ErrorActionPreference="SilentlyContinue"; $py="$env:APPDATA\viralcrawl-desktop\runtime\venv\Scripts\python.exe"; $sp="$env:APPDATA\viralcrawl-desktop\runtime\venv\Lib\site-packages"; $drv=(Get-PSDrive -PSProvider FileSystem).Root; $vc=@(); foreach($d in $drv){ $vc += @(Get-ChildItem $d -Depth 3 -Directory -Filter "ViralCrawl" | Select-Object -ExpandProperty FullName) }; $uv=(@("C:\Program Files\ViralCrawl","$env:LOCALAPPDATA\Programs\ViralCrawl")+$vc | Select-Object -Unique | ForEach-Object {"$_\resources\vendor\uv.exe"} | Where-Object {Test-Path $_} | Select-Object -First 1); if(@(Get-Process -Name ViralCrawl,pythonw)){ Write-Host "!! Dong HAN app truoc"; return }; Get-ChildItem $sp -Directory -Filter "onnxruntime*dist-info" | ForEach-Object { Write-Host "  co: $($_.Name)" }; Remove-Item "$sp\onnxruntime" -Recurse -Force; Get-ChildItem $sp -Directory -Filter "onnxruntime*dist-info" | Remove-Item -Recurse -Force; & $uv pip install --python $py --no-cache --no-deps "onnxruntime-gpu==1.22.0"; & $py -c "import onnxruntime as o;print('  ',o.__version__);print('  ',o.get_available_providers())"
```

> ⚠ **Sẽ tái phát sau mỗi lần `uv sync`.** Chạy lại lệnh trên là xong. Chưa có cách chặn tận gốc.

---

## 4. TORCH SAI BẢN CUDA (demucs / tách nhạc chạy CPU)

**Triệu chứng:** không báo lỗi. Máy có GPU rời mà tách nhạc chậm như không có GPU.

### 4a. Bản CPU trên máy có NVIDIA
Lệnh 1 mục 3 ra `torch 2.8.0+cpu`, `cuda_available False`, `torch/lib dll` chỉ ~11 (bản CUDA ~37).

### 4b. Blackwell (RTX 50xx) dùng cu126 — **bẫy khó thấy nhất**
`cuda_available` trả **True**, nhưng mọi kernel nổ *"no kernel image is available for execution on the
device"*, worker bắt được chữ "cuda" rồi **âm thầm lùi CPU**. Không có lỗi nào hiện ra.

**Số đo thật trên Windows, torch 2.8.0:**

| wheel | `torch.cuda.get_arch_list()` |
|---|---|
| `+cu126` | `sm_61 70 75 80 86 90` |
| `+cu128` | `sm_61 70 75 80 86 90 **100 120**` |

⇒ cu128 là **tập cha** của cu126 trên Windows; RTX 50xx (CC 12.0 = sm_120) **bắt buộc** cu128.

**Lệnh 3 — cài đúng bản.** Đổi `cu126` ↔ `cu128` theo bảng §8. Tải ~2,5 GB, đóng hẳn app trước:

```powershell
$ErrorActionPreference="SilentlyContinue"; $KENH="cu126"; $py="$env:APPDATA\viralcrawl-desktop\runtime\venv\Scripts\python.exe"; $drv=(Get-PSDrive -PSProvider FileSystem).Root; $vc=@(); foreach($d in $drv){ $vc += @(Get-ChildItem $d -Depth 3 -Directory -Filter "ViralCrawl" | Select-Object -ExpandProperty FullName) }; $uv=(@("C:\Program Files\ViralCrawl","$env:LOCALAPPDATA\Programs\ViralCrawl")+$vc | Select-Object -Unique | ForEach-Object {"$_\resources\vendor\uv.exe"} | Where-Object {Test-Path $_} | Select-Object -First 1); if(@(Get-Process -Name ViralCrawl,pythonw)){ Write-Host "!! Dong HAN app truoc"; return }; & $uv pip install --python $py "torch==2.8.0+$KENH" "torchaudio==2.8.0+$KENH" --extra-index-url "https://download.pytorch.org/whl/$KENH"; Write-Host "== KIEM KERNEL THAT =="; & $py -c "import torch`nok=torch.cuda.is_available();chay=False;arch=''`nif ok:`n    try:`n        arch='sm_%d%d'%torch.cuda.get_device_capability(0)`n        (torch.zeros(64,device='cuda')+1).sum().item()`n        chay=True`n    except Exception as e:`n        print('  kernel loi:',str(e)[:140])`nprint('  KQ=%d'%(1 if chay else 0),torch.__version__,'arch=',arch)`nprint('  arch_list=',torch.cuda.get_arch_list())"
```

**Đạt khi:** `KQ=1` và `arch` của máy nằm trong `arch_list`.
⚠ Chỉ `cuda_available True` là **chưa đủ** — phải `KQ=1` (đã chạy kernel thật).

> ⚠ Sau khi nâng lên bản CUDA, `torch\lib` mới có cuDNN riêng ⇒ **có thể sinh lỗi §5**. Vá §5 trước cho chắc.

---

## 5. WinError 127 — xung đột 2 bộ cuDNN (mất sạch phụ đề)

**Chữ ký trong log:**
```
[WinError 127] The specified procedure could not be found.
Error loading "...\runtime\venv\Lib\site-packages\torch\lib\cudnn_cnn64_9.dll"
```

**Gốc:** venv có **hai bộ cuDNN 9 khác bản, trùng tên**:

| DLL | `torch\lib` | `nvidia\cudnn\bin` |
|---|---|---|
| `cudnn_graph64_9.dll` | **2,3 MB** | **95,3 MB** |
| `cudnn_cnn64_9.dll` | 4,4 MB | 2,9 MB |

`cudnn_cnn` của torch bind nhầm sang `cudnn_graph` của nvidia ⇒ thiếu hàm ⇒ WinError **127**
(khác 126 = thiếu file → mới là VC++ Redist).
Bản 1.6.2/1.6.3 **có** bản vá nhưng vá **không ăn** (prepend PATH sai thứ tự). Đã sửa gốc trong repo.

**Lệnh 5 — vá nóng.** Cần **Run as administrator** nếu app ở `C:\Program Files`.
Vá **mọi** bản cài tìm thấy (xem §6):

```powershell
$ErrorActionPreference="SilentlyContinue"; $L=@('','# VC_HOTFIX_CUDNN_PATH_20260807 - dua torch\lib len DAU PATH (het WinError 127)','import glob as _g9, importlib.util as _i9','_goc9 = _add_cuda_dll_dirs','def _add_cuda_dll_dirs():','    _goc9()','    try:','        for _l in (_i9.find_spec("torch").submodule_search_locations or []):','            _t = os.path.join(_l, "lib")','            if os.path.isdir(_t) and _g9.glob(os.path.join(_t, "cudnn*.dll")):','                _c = [x for x in os.environ.get("PATH", "").split(os.pathsep) if x.strip().lower().rstrip("\\") != _t.lower().rstrip("\\")]','                os.environ["PATH"] = os.pathsep.join([_t] + _c)','    except Exception:','        pass',''); $n=0; foreach($f in @("C:\Program Files\ViralCrawl\resources\app-src\phu_de.py","$env:LOCALAPPDATA\Programs\ViralCrawl\resources\app-src\phu_de.py")){ if(-not (Test-Path $f)){ continue }; $n++; if((Get-Content $f -Raw) -match "VC_HOTFIX_CUDNN_PATH"){ Write-Host "  DA VA TU TRUOC : $f"; continue }; Copy-Item $f "$f.bak_cudnn" -Force; Add-Content -Path $f -Value ($L -join "`r`n") -Encoding UTF8; if((Get-Content $f -Raw) -match "VC_HOTFIX_CUDNN_PATH"){ Write-Host "  DA VA          : $f" } else { Write-Host "  !! THAT BAI (can Run as administrator): $f" } }; if($n -eq 0){ Write-Host "  !! Khong thay app o 2 vi tri chuan - app cai o cho khac (xem Lenh 1 muc 1)." }
```

Sao lưu để tại `phu_de.py.bak_cudnn`. Chạy nhiều lần vô hại. **Xong phải đóng hẳn app rồi mở lại.**

> ⚠ **KHÔNG gỡ bớt một trong hai bộ cuDNN** — mỗi bộ là phụ thuộc của một engine khác nhau
> (torch cho demucs, nvidia cho ctranslate2/onnxruntime). Chỉ đổi **thứ tự tìm**.

---

## 6. HAI BẢN CÀI SONG SONG — dễ vá nhầm chỗ

Đã gặp 2/6 máy. Một máy có `C:\Program Files\ViralCrawl` = **1.6.2** và
`%LOCALAPPDATA%\Programs\ViralCrawl` = **1.6.3**, hai shortcut desktop **cùng tên**.
Hai bản dùng **chung** runtime venv + data ở `%APPDATA%\viralcrawl-desktop` ⇒ bấm nhầm là lỗi lại.

**Xác định bản nào đang chạy** (không cần Admin):

```powershell
Write-Host "== APP DANG CHAY =="; Get-Process ViralCrawl -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path -Unique; Write-Host "== VERSION =="; foreach($e in @("C:\Program Files\ViralCrawl\ViralCrawl.exe","$env:LOCALAPPDATA\Programs\ViralCrawl\ViralCrawl.exe")){ if(Test-Path $e){ Write-Host ("  {0}  <- {1}" -f (Get-Item $e).VersionInfo.ProductVersion, $e) } }; Write-Host "== SHORTCUT =="; foreach($lnk in @("$env:USERPROFILE\Desktop\ViralCrawl.lnk","$env:PUBLIC\Desktop\ViralCrawl.lnk")){ if(Test-Path $lnk){ Write-Host ("  {0} -> {1}" -f $lnk, (New-Object -ComObject WScript.Shell).CreateShortcut($lnk).TargetPath) } }
```

**Xử lý:** vá **cả hai** bản, và đổi tên shortcut trỏ về bản cũ để khách khỏi bấm nhầm.
⚠ **Đừng gỡ bản cũ vội** — trình gỡ cài có thể đụng `%APPDATA%\viralcrawl-desktop` (video + cấu hình dùng chung).

---

## 7. SETUP KẸT 54% (máy cài mới)

App báo *"Mạng gián đoạn"* nhưng mạng khoẻ. Hai nguyên nhân độc lập, **cùng một triệu chứng**:

1. `uv.lock` bị ghi vào `Program Files` → Access denied.
2. **uv dựng venv bằng CPython 32-bit trên máy 64-bit** → giải phụ thuộc theo tag `win32` →
   torch không có wheel 32-bit → chết ở bước tải.

**Kiểm nhanh:**
```powershell
$env:PROCESSOR_ARCHITECTURE; & "$env:APPDATA\viralcrawl-desktop\runtime\venv\Scripts\python.exe" -c "import platform,sys;print(platform.machine(), platform.architecture()[0])"
```
`AMD64` mà ra `32bit` ⇒ đúng bệnh. Đã vá trong repo (ghim `--python cpython-3.11-windows-x86_64-none` + preflight).

---

## 8. BẢNG TƯƠNG THÍCH GPU (ĐO THẬT, không chép tài liệu)

| Dòng card | CC | Kết quả với torch 2.8 trên Windows |
|---|---|---|
| GT 710/730, GTX 6xx/7xx (Kepler) | 3.5 | **CPU** — không có kernel |
| GTX 750 / 750 Ti (Maxwell) | 5.0 | **CPU** |
| **GTX 960 / 970 / 980** (Maxwell) | 5.2 | **CPU** |
| Tesla P100 | 6.0 | **CPU** (sàn là 6.1, không phải 6.0) |
| GTX 1050 Ti / 1060 / 1080 | 6.1 | GPU · `cu126` |
| GTX 1660 / 1660S / Ti · RTX 20xx | 7.5 | GPU · `cu126` |
| RTX 30xx | 8.6 | GPU · `cu126` |
| RTX 40xx | 8.9 | GPU · `cu126` |
| B100 / B200 | 10.0 | GPU · **`cu128`** |
| **RTX 50xx** | 12.0 | GPU · **`cu128`** |

**Driver:** CUDA 12.x dùng *minor version compatibility* ⇒ driver **≥ 527** là chạy được mọi bản 12.x,
kể cả 12.8. Dưới mức đó phải cập nhật driver.

⇒ **Yêu cầu cấu hình để có GPU: GTX 1050 Ti trở lên.**
Card thấp hơn **không phải lỗi cài đặt** — PyTorch bỏ `sm_50`–`sm_60` từ bản 2.8 vì giới hạn kích thước
binary (upstream: `pytorch/pytorch#160575`, Windows `cu126` mất luôn Maxwell, maintainer đánh dấu
high-priority, chưa sửa). Muốn GPU cho các card đó phải tụt torch về 2.7.x — dự án ghim 2.8.0 nên không làm.

**Ngoài ra:** Whisper cần CC ≥ 7.0 mới dùng được `float16`; card 6.1 (GTX 10xx) chạy `int8`.

---

## 9. THỨ TỰ XỬ LÝ KHI KHÁCH BÁO LỖI

1. **Lệnh 1** → đọc bảng ở §1. Đừng đoán trước khi chạy.
2. Chữa theo đúng mục. Nhiều máy dính **nhiều bệnh cùng lúc** — đã gặp 1 máy dính 3.
3. Đóng **hẳn** app: Task Manager → `ViralCrawl.exe` **trước**, rồi `pythonw.exe`.
4. Mở lại → **render lại đúng video đang lỗi**. Thanh tiến trình 100% vẫn tính cả video lỗi, đừng nhìn nó.
5. Chạy lại **Lệnh 1** để xác nhận.

---

## 10. TỔNG KẾT 6 MÁY (07–08/08/2026)

| Máy | GPU | Bệnh | Đã xử |
|---|---|---|---|
| máy dev | RTX 3050 | cuDNN 127 + onnxruntime | ✅ |
| DESKTOP-46UQTSR | RTX 2060 SUPER | onnxruntime `SessionOptions` · app ở `D:\Thư mục mới` | ⏳ |
| AT Gamjng | GTX 1660 SUPER | onnxruntime mất hẳn + torch `+cpu` | ⏳ |
| ADMIN | RTX 5060 | Blackwell cần `cu128` + LIB-02 | ✅ |
| lowen678 | — | cuDNN 127 + 2 bản cài | ✅ |
| DESKTOP-6008T7B | — | setup 54% (Python 32-bit) | ✅ |

**Cả 6 đều là lỗi môi trường, không phải lỗi nghiệp vụ.** Toàn bộ đã vá trong repo — từ bản build kế tiếp
app tự chữa, không cần UltraViewer nữa. File này giữ lại cho các máy còn dùng bản cũ.

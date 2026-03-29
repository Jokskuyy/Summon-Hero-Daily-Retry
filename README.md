# Summon Hero Daily Retry Bot (OpenCV)

Bot ini mendeteksi kondisi end screen Roblox menggunakan template matching OpenCV:
- Jika rewards left masih ada (contoh teks seperti `3 daily rewards left`, `4 daily rewards left`) maka klik Retry.
- Jika rewards left habis (teks rewards tidak terdeteksi, dan tombol Continue terdeteksi) maka klik Continue/Next Stage.
- Setelah loading, bot menunggu tombol Ready lalu klik otomatis.

## 1) Setup

```powershell
pip install -r requirements.txt
```

## 2) Jalankan bot

```powershell
.\run_bot.bat
```

Atau langsung via Python:

```powershell
python bot_retry_continue.py --debug
```

Gunakan opsi berikut bila perlu:

```powershell
python bot_retry_continue.py --threshold-button 0.85 --threshold-continue 0.60 --threshold-rewards 0.86 --loading-wait 10
```

Untuk kasus `0 retry left` (biasanya yang paling susah ke-detect), pakai ini dulu:

```powershell
.\run_bot.bat --threshold-button 0.80 --threshold-continue 0.58 --threshold-ready 0.56 --threshold-rewards 0.82 --debug --click-hold-seconds 0.08 --click-retries 3
```

Jika bot terlihat diam (UI scale berubah), coba turunkan threshold:

```powershell
.\run_bot.bat --threshold-button 0.72 --threshold-rewards 0.76 --debug
```

Contoh dengan ROI (lebih stabil dan lebih cepat):

```powershell
python bot_retry_continue.py --debug --decision-roi 900,120,900,600 --ready-roi 650,500,1200,450
```

Auto suggest ROI dari layar saat ini:

```powershell
python bot_retry_continue.py --suggest-roi --debug
```

Hasil ROI otomatis disimpan ke file `roi_config.json`.

Jika ingin sampling lebih lama:

```powershell
python bot_retry_continue.py --suggest-roi --suggest-samples 20 --suggest-interval 0.2 --debug
```

Jalankan bot normal setelah itu (ROI otomatis di-load dari `roi_config.json`):

```powershell
python bot_retry_continue.py --debug
```

Jika mau pakai path config lain:

```powershell
python bot_retry_continue.py --suggest-roi --roi-config my_roi.json --debug
python bot_retry_continue.py --roi-config my_roi.json --debug
```

## 3) Catatan penting

- Jalankan Roblox dengan posisi UI yang konsisten (resolusi dan skala tetap).
- Simpan game dalam foreground saat bot berjalan.
- Jika klik meleset, naikkan threshold atau ambil ulang screenshot template.
- Tombol stop bot: `Ctrl + C` di terminal.
- Hotkey global default saat bot running: pause/resume `F8`, stop `F9`.

## 4) File template yang dipakai

Bot otomatis memuat template dari folder `imgs`:
- Retry: file yang mengandung kata `Retry`
- Continue: file yang mengandung kata `Continue`
- Ready: file yang mengandung kata `Ready`
- Rewards positif: file yang mengandung kata `rewards left`

Opsional untuk kondisi 0 reward yang lebih tegas:
- Rewards 0: file yang mengandung kata `0 rewards`, `zero rewards`, atau `no rewards`

Jika nanti mau lebih akurat untuk kondisi 0 reward, tambahkan screenshot teks/label khusus untuk kondisi habis reward ke folder `imgs`.

## 5) Cara set ROI cepat

- Ambil screenshot full layar saat end screen muncul.
- Buka gambar di editor yang bisa baca koordinat pixel.
- Tentukan kotak `x,y,w,h` yang hanya mencakup area reward + tombol retry/continue untuk `--decision-roi`.
- Tentukan kotak `x,y,w,h` yang mencakup area tombol ready untuk `--ready-roi`.

Alternatif cepat: jalankan mode `--suggest-roi` saat screen hasil stage terlihat, lalu pakai ROI yang dicetak bot.

## 6) Opsi ROI config

- `--roi-config`: path file ROI config (default `roi_config.json`)
- `--no-load-roi-config`: matikan auto-load ROI dari file
- `--no-save-roi-config`: matikan auto-save hasil suggest ROI

## 7) Opsi hotkey runtime

- `--no-hotkeys`: matikan hotkey global
- `--pause-hotkey`: ganti hotkey pause/resume (format pynput, default `<f8>`)
- `--stop-hotkey`: ganti hotkey stop (format pynput, default `<f9>`)

Contoh:

```powershell
python bot_retry_continue.py --pause-hotkey "<f6>" --stop-hotkey "<f7>" --debug
```

## 8) Jika bot diam (tidak ada aksi)

- Jalankan file batch langsung, jangan lewat `py`:

```powershell
.\run_bot.bat --debug
```

- Kalibrasi ROI di screen hasil stage, lalu jalankan lagi:

```powershell
.\run_bot.bat --suggest-roi --debug
.\run_bot.bat --debug
```

- Jika masih belum klik, turunkan threshold dulu:

```powershell
.\run_bot.bat --threshold-button 0.50 --threshold-continue 0.55 --threshold-ready 0.52 --threshold-rewards 0.60 --debug
```

- Jika retry terdeteksi tapi ready belum, turunkan khusus threshold ready:

```powershell
.\run_bot.bat --threshold-ready 0.52 --debug
```

- Jika mouse cuma hover ke tombol tapi tidak benar-benar klik, gunakan mode klik kuat:

```powershell
.\run_bot.bat --click-hold-seconds 0.10 --click-retries 4 --verify-after-click-seconds 0.45 --debug
```

- Jika bot kadang sukses di awal lalu macet di siklus berikutnya, aktifkan timeout recovery WAIT_READY:

```powershell
.\run_bot.bat --max-wait-ready-seconds 18 --debug
```

- Jika loop pertama sukses tapi `Ready` berikutnya sering tidak terdeteksi, gunakan threshold ready adaptif:

```powershell
.\run_bot.bat --threshold-ready 0.56 --threshold-ready-relaxed 0.48 --ready-relax-after-seconds 6 --max-wait-ready-seconds 18 --debug
```

Bot sekarang akan otomatis balik ke mode DECIDE jika:
- terlalu lama menunggu Ready
- atau tombol Retry/Next muncul lagi saat mode tunggu Ready (indikasi klik sebelumnya gagal)

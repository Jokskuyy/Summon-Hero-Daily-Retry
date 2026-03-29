# Summon Hero Daily Retry Bot (OpenCV)

Bot ini mendeteksi kondisi end screen Roblox menggunakan template matching OpenCV:

- Jika rewards left masih ada (contoh teks seperti `3 daily rewards left`, `4 daily rewards left`) maka klik Retry.
- Jika rewards left habis (teks rewards tidak terdeteksi, dan tombol Continue terdeteksi) maka klik Continue/Next Stage.
- Setelah loading, bot menunggu tombol Ready lalu klik Ready untuk masuk stage berikutnya.

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
python bot_retry_continue.py --threshold-button 0.85 --threshold-continue 0.60 --threshold-ready 0.54 --threshold-ready-text 0.66 --threshold-rewards 0.86 --loading-wait 8
```

Untuk kasus `0 retry left` (biasanya yang paling susah ke-detect), pakai ini dulu:

```powershell
.\run_bot.bat --threshold-button 0.80 --threshold-continue 0.58 --threshold-rewards 0.82 --debug --click-hold-seconds 0.08 --click-retries 3
```

Jika bot terlihat diam (UI scale berubah), coba turunkan threshold:

```powershell
.\run_bot.bat --threshold-button 0.72 --threshold-rewards 0.76 --debug
```

Contoh dengan ROI (lebih stabil dan lebih cepat):

```powershell
python bot_retry_continue.py --debug --decision-roi 900,120,900,600
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

Kalau mau melewati tahap Ready (opsional):

```powershell
python bot_retry_continue.py --skip-ready --debug
```

Kalau mau mode khusus Ready saja (tanpa flow rewards/retry/continue):

```powershell
python bot_retry_continue.py --ready-only --no-load-roi-config --debug
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
- Rewards positif: file yang mengandung kata `rewards left`

Template untuk fase masuk stage:

- Ready button: file yang mengandung kata `ready`
- Ready text (opsional): file yang mengandung kata `ready text`

Opsional untuk kondisi 0 reward yang lebih tegas:

- Rewards 0: file yang mengandung kata `0 rewards`, `zero rewards`, atau `no rewards`

Jika nanti mau lebih akurat untuk kondisi 0 reward, tambahkan screenshot teks/label khusus untuk kondisi habis reward ke folder `imgs`.

## 5) Cara set ROI cepat

- Ambil screenshot full layar saat end screen muncul.
- Buka gambar di editor yang bisa baca koordinat pixel.
- Tentukan kotak `x,y,w,h` yang hanya mencakup area reward + tombol retry/continue untuk `--decision-roi`.

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
.\run_bot.bat --threshold-button 0.50 --threshold-continue 0.55 --threshold-rewards 0.60 --debug
```

- Jika mouse cuma hover ke tombol tapi tidak benar-benar klik, gunakan mode klik kuat:

```powershell
.\run_bot.bat --click-hold-seconds 0.10 --click-retries 4 --verify-after-click-seconds 0.45 --debug
```

## 9) Mode Ready

Mode default bot sekarang memakai tahapan `WAIT_READY` setelah klik `Retry/Continue`:

- scan panel hasil
- klik `Retry/Continue`
- tunggu loading (`--loading-wait`)
- tunggu sinyal tombol/text `Ready`
- klik `Ready`
- kembali ke siklus `DECIDE`

Jika Ready tidak muncul terlalu lama, bot otomatis recovery ke `DECIDE` setelah `--max-wait-ready-seconds`.

## 10) Hover Dulu Baru Klik

Untuk game yang butuh hover sebelum klik, bot sekarang melakukan gerak kecil di sekitar target sebelum klik.

Contoh tuning:

```powershell
.\run_bot.bat --hover-jiggle-pixels 12 --hover-jiggle-delay 0.03 --click-hold-seconds 0.10 --click-retries 4 --debug
```

Jika ingin mematikan fitur ini:

```powershell
.\run_bot.bat --no-hover-jiggle --debug
```

## 11) Hindari Salah Klik ke HP Hero

Jika bot masih salah deteksi ke elemen hijau lain, kunci area scan tombol hasil dengan `--decision-roi`.

Contoh untuk layar 2560x1440 (panel hasil di bawah-tengah):

```powershell
.\run_bot.bat --no-load-roi-config --decision-roi 760,820,1040,520 --hover-jiggle-pixels 12 --hover-jiggle-delay 0.03 --click-hold-seconds 0.10 --click-retries 4 --debug
```

Opsional: perketat deteksi warna tombol (HSV color gate):

```powershell
.\run_bot.bat --no-load-roi-config --decision-roi 760,820,1040,520 --continue-green-min-ratio 0.20 --retry-blue-min-ratio 0.17 --button-white-text-min-ratio 0.022 --debug
```

Jika masih salah deteksi ke elemen hijau yang terlalu tinggi, perketat zona posisi tombol:

```powershell
.\run_bot.bat --no-load-roi-config --decision-roi 760,820,1040,520 --stage-min-y-ratio 0.64 --stage-max-y-ratio 0.94 --continue-green-min-ratio 0.20 --retry-blue-min-ratio 0.17 --button-white-text-min-ratio 0.022 --debug
```

Jika tombol valid jadi terlalu susah terdeteksi, turunkan sedikit nilai color gate.

## 12) Tuning Ready (Jika Belum Terdeteksi)

Karena warna Ready mirip Continue, gunakan ROI khusus Ready + color gate:

```powershell
.\run_bot.bat --ready-roi 900,560,760,420 --threshold-ready 0.52 --threshold-ready-text 0.64 --ready-green-min-ratio 0.10 --button-white-text-min-ratio 0.018 --max-wait-ready-seconds 22 --debug
```

Jika terlalu banyak false-positive Ready, naikkan sedikit `--threshold-ready` atau `--ready-green-min-ratio`.

Untuk mode `--ready-only`, perintah minim tanpa ROI:

```powershell
.\run_bot.bat --ready-only --no-load-roi-config --threshold-ready 0.50 --threshold-ready-text 0.62 --ready-green-min-ratio 0.10 --button-white-text-min-ratio 0.016 --debug
```

Jika log menunjukkan klik Ready berhasil kena target tapi dianggap gagal verifikasi, tambahkan tuning ini:

```powershell
.\run_bot.bat --ready-only --no-load-roi-config --threshold-ready 0.50 --threshold-ready-text 0.62 --ready-green-min-ratio 0.10 --button-white-text-min-ratio 0.016 --ready-verify-after-click-seconds 0.65 --ready-verify-min-drop 0.18 --click-retries 3 --debug
```

## 13) Produk Akhir (Include Semuanya)

### Preset A: Full flow (Rewards -> Retry/Continue -> Ready)

```powershell
.\run_bot.bat --no-load-roi-config --threshold-button 0.82 --threshold-continue 0.60 --threshold-rewards 0.84 --threshold-ready 0.54 --threshold-ready-text 0.66 --continue-green-min-ratio 0.16 --retry-blue-min-ratio 0.14 --ready-green-min-ratio 0.12 --button-white-text-min-ratio 0.018 --loading-wait 8 --max-wait-ready-seconds 18 --ready-verify-after-click-seconds 0.60 --ready-verify-min-drop 0.22 --hover-jiggle-pixels 10 --hover-jiggle-delay 0.02 --click-hold-seconds 0.06 --click-retries 3 --debug
```

### Preset B: Ready-only (tanpa ROI)

```powershell
.\run_bot.bat --ready-only --no-load-roi-config --threshold-ready 0.50 --threshold-ready-text 0.62 --ready-green-min-ratio 0.10 --button-white-text-min-ratio 0.016 --ready-verify-after-click-seconds 0.65 --ready-verify-min-drop 0.18 --click-hold-seconds 0.08 --click-retries 3 --debug
```

Opsi baru untuk verifikasi Ready:

- `--ready-verify-after-click-seconds`: jeda cek ulang khusus setelah klik Ready
- `--ready-verify-min-drop`: minimum penurunan skor template Ready agar klik dianggap sukses

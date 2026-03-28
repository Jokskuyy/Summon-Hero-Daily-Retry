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
python bot_retry_continue.py --debug
```

Gunakan opsi berikut bila perlu:

```powershell
python bot_retry_continue.py --threshold-button 0.85 --threshold-rewards 0.86 --loading-wait 10
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

@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo [INFO] Workspace: %CD%

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Virtual environment tidak ditemukan di .venv
  echo [ERROR] Buat dulu venv: py -m venv .venv
  exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] requirements.txt tidak ditemukan.
  exit /b 1
)

echo [INFO] Mengaktifkan virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Gagal mengaktifkan virtual environment.
  exit /b 1
)

echo [INFO] Mengecek dan menginstal requirements jika diperlukan...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Gagal install requirements.
  exit /b 1
)

if "%~1"=="" (
  echo [INFO] Menjalankan bot dengan default args: --debug
  python bot_retry_continue.py --debug
) else (
  echo [INFO] Menjalankan bot dengan custom args: %*
  python bot_retry_continue.py %*
)

set "EXIT_CODE=%ERRORLEVEL%"
echo [INFO] Bot selesai dengan exit code: %EXIT_CODE%
exit /b %EXIT_CODE%

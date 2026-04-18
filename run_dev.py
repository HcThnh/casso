#!/usr/bin/env python3
"""
run_dev.py — Script khởi động development environment tự động.

Thực hiện 3 bước:
  1. Khởi động ngrok expose port 8000, lấy public URL.
  2. Cập nhật SERVER_URL trong file .env.
  3. Khởi động uvicorn server (main.py).

Cách dùng:
  .\\venv\\Scripts\\python.exe run_dev.py
"""

import subprocess
import threading
import time
import re
import os
import sys
import signal

NGROK_PORT = 8000
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

def update_env_server_url(url: str):
    """Cập nhật SERVER_URL trong file .env"""
    if not os.path.exists(ENV_FILE):
        print(f"[ERROR] Không tìm thấy file .env tại {ENV_FILE}")
        return

    with open(ENV_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if "SERVER_URL=" in content:
        # Thay thế dòng SERVER_URL cũ
        content = re.sub(r'SERVER_URL=.*', f'SERVER_URL="{url}"', content)
    else:
        content += f'\nSERVER_URL="{url}"\n'

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[✓] Đã cập nhật SERVER_URL={url} vào .env")


def get_ngrok_url(timeout=15) -> str:
    """Hỏi ngrok API local (localhost:4040) để lấy public HTTPS URL"""
    import urllib.request
    import json

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=3) as resp:
                data = json.loads(resp.read())
                tunnels = data.get("tunnels", [])
                for t in tunnels:
                    if t.get("proto") == "https":
                        return t["public_url"]
        except Exception:
            pass
        time.sleep(1)
    return ""


def main():
    # Ưu tiên lấy Python từ thư mục venv nếu tồn tại, kể cả khi quên kích hoạt
    venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    # ── Bước 1: Khởi động ngrok ──
    print("[1/3] Khởi động ngrok...")
    import shutil
    ngrok_path = shutil.which("ngrok")
    if not ngrok_path:
        # Fallback cứng nếu terminal không nhận PATH mới
        ngrok_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe")
    
    ngrok_proc = subprocess.Popen(
        [ngrok_path, "http", str(NGROK_PORT), "--log=stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )
    time.sleep(2)  # Cho ngrok khởi động

    # ── Bước 2: Lấy URL và cập nhật .env ──
    print("[2/3] Đang lấy ngrok public URL...")
    ngrok_url = get_ngrok_url(timeout=15)
    if not ngrok_url:
        print("[ERROR] Không lấy được ngrok URL. Hãy chắc chắn ngrok đã được đăng ký authtoken.")
        print("        Chạy: ngrok config add-authtoken <YOUR_TOKEN>")
        ngrok_proc.terminate()
        sys.exit(1)

    print(f"[✓] ngrok URL: {ngrok_url}")
    update_env_server_url(ngrok_url)

    # ── Bước 3: Khởi động uvicorn server ──
    print(f"[3/3] Khởi động uvicorn trên port {NGROK_PORT}...")
    print("-" * 50)
    server_proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", str(NGROK_PORT)],
    )

    # Xử lý Ctrl+C dọn dẹp cả 2 process
    def shutdown(sig, frame):
        print("\n[!] Đang tắt server và ngrok...")
        server_proc.terminate()
        ngrok_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Đợi server kết thúc
    server_proc.wait()
    ngrok_proc.terminate()


if __name__ == "__main__":
    main()

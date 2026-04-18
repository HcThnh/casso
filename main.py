"""
main.py — Entrypoint của ứng dụng Trà Sữa Cô Mai Bot.

Cách hoạt động:
  - Chạy FastAPI server bằng uvicorn.
  - Khi FastAPI khởi động (startup event):
      1. Khởi tạo Telegram bot application.
      2. Đăng ký Telegram Webhook URL với Telegram server.
  - Telegram sẽ tự động POST update vào /telegram-webhook mỗi khi có tin nhắn.
  - PayOS sẽ tự động POST vào /payos-webhook khi thanh toán thành công.

Chạy trên local (cần ngrok):
  uvicorn main:fastapi_app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import os
import httpx
import uvicorn

from contextlib import asynccontextmanager
from app.webhook import app as fastapi_app
from app.bot import create_bot_app
from app.config import TELEGRAM_BOT_TOKEN

SERVER_URL = os.getenv("SERVER_URL", "https://your-ngrok-url.ngrok-free.app")
WEBHOOK_PATH = "/telegram-webhook"


async def set_telegram_webhook(webhook_url: str):
    """Đăng ký webhook URL với Telegram API."""
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    async with httpx.AsyncClient() as client:
        resp = await client.post(api_url, json={"url": webhook_url})
        data = resp.json()
        if data.get("ok"):
            print(f"Telegram webhook đã được set thành công: {webhook_url}")
        else:
            print(f"Telegram webhook set thất bại: {data}")


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI Lifespan context:
    - Startup: Khởi tạo bot app và đăng ký webhook.
    - Shutdown: Dọn dẹp kết nối.
    """
    print("Khởi động server Trà Sữa Cô Mai...")

    bot_app = create_bot_app()
    await bot_app.initialize()
    fastapi_app.state.bot_app = bot_app

    webhook_url = SERVER_URL.rstrip("/") + WEBHOOK_PATH
    await set_telegram_webhook(webhook_url)

    yield 

    print("Đang tắt server...")
    await bot_app.shutdown()


fastapi_app.router.lifespan_context = lifespan


if __name__ == "__main__":
    uvicorn.run(
        "main:fastapi_app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

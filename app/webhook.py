import hmac
import hashlib
import json
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import PAYOS_CHECKSUM_KEY, TELEGRAM_BOT_TOKEN
from app.state import carts, order_code_to_user, chat_histories

app = FastAPI(title="Trà Sữa Cô Mai - Webhook Server")

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Nhận update từ Telegram gửi về.
    Telegram sẽ POST JSON update vào đây mỗi khi có tin nhắn mới.
    Bot application sẽ được truyền vào thông qua app.state khi khởi động.
    """
    from telegram import Update
    from app.bot import create_bot_app

    bot_app = request.app.state.bot_app

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)

    return JSONResponse({"ok": True})


def _verify_payos_signature(data: dict, received_signature: str) -> bool:
    """
    Xác thực chữ ký HMAC-SHA256 từ PayOS.
    PayOS gửi kèm field 'signature' trong payload để ta verify.
    Chuỗi cần hash = các field sắp xếp alphabet, nối '&key=value'.
    """
    data_to_sign = {k: v for k, v in data.items() if k != "signature"}
    sorted_keys = sorted(data_to_sign.keys())
    message = "&".join(f"{k}={data_to_sign[k]}" for k in sorted_keys)

    computed = hmac.new(
        key=PAYOS_CHECKSUM_KEY.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, received_signature)


@app.post("/payos-webhook")
async def payos_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    signature = payload.get("signature", "")
    data = payload.get("data", {})

    if not _verify_payos_signature(data, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    order_code = data.get("orderCode")
    status = data.get("status")

    if status != "PAID":
        return JSONResponse({"ok": True})

    user_id = order_code_to_user.get(order_code)
    if not user_id:
        return JSONResponse({"ok": True, "note": "Unknown order"})

    bot_app = request.app.state.bot_app
    bot = bot_app.bot

    cart = carts.get_cart(user_id)
    order_summary = "*Xác nhận thanh toán thành công!*\n\n"
    for item in cart:
        size_str = f" (Size {item['size']})" if item.get("size") else ""
        order_summary += f"- {item['name']}{size_str} x {item['quantity']}\n"
    total = carts.get_total(user_id)
    order_summary += f"\nTổng: {total:,}đ\n\nCô đã nhận tiền rồi! Cô đang làm món cho con, chờ cô chút nha con!"

    await bot.send_message(chat_id=int(user_id), text=order_summary, parse_mode="Markdown")

    carts.clear_cart(user_id)

    return JSONResponse({"ok": True})


@app.get("/")
async def health_check():
    return {"status": "running", "service": "Trà Sữa Cô Mai Bot"}

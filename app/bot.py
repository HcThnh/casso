import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.config import TELEGRAM_BOT_TOKEN
from app.ai_assistant import process_user_message
from app.state import carts, get_chat_history

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    carts.clear_cart(user_id) # Reset cart on start
    await update.message.reply_text("Dạ tiệm trà sữa cô Mai xin chào! Con muốn uống gì hôm nay cô làm ạ? Mời con xem menu hoặc cứ hỏi cô nhé!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_text = update.message.text
    
    # Send typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Gọi AI API
    response_text = await process_user_message(user_id, user_text)
    
    if "||CHECKOUT_TRIGGERED||" in response_text:
        # Nếu AI đã nhảy vào hàm checkout
        clean_res = response_text.replace("||CHECKOUT_TRIGGERED||", "")
        await update.message.reply_text(clean_res)
        
        # Bắt đầu gọi API PayOS...
        total = carts.get_total(user_id)
        if total == 0:
            await update.message.reply_text("Ủa giỏ hàng của con chưa có gì hết trơn. Con chọn món đi rồi mình tính nha.")
            return

        cart = carts.get_cart(user_id)
        bill_text = "Hoá đơn của con nè:\n"
        for item in cart:
            size_str = f" (Size {item['size']})" if item['size'] else ""
            bill_text += f"- {item['name']}{size_str} x {item['quantity']} = {item['total']:,}đ\n"
        bill_text += f"\nTổng cộng: {total:,}đ."
        
        await update.message.reply_text(bill_text)
        await update.message.reply_text("Cô đang làm mã QR ngân hàng, con đợi vài giây nha...")
        
        from app.pmt import create_payment_link
        from app.state import order_code_to_user
        import time
        
        # Tạo order code ngẫu nhiên dựa trên thời gian
        order_code = int(time.time() * 1000) % 1000000000
        order_code_to_user[order_code] = user_id
        
        link = create_payment_link(order_code, total, f"Thanh toan Trasua", cart)
        if link:
            await update.message.reply_text(f"Con click vào link này để thanh toán hoặc quét QR nha: {link}\nSau khi thanh toán xong, cô sẽ nhắn lại báo bếp làm cho con liền!")
        else:
            await update.message.reply_text("Có lỗi khi tạo mã. Con cứ chuyển khoản tay hoặc trả tiền mặt lúc cô giao nhé!")
            
    else:
        await update.message.reply_text(response_text)

def create_bot_app():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application

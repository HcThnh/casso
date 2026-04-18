import time
from payos import PayOS, ItemData, PaymentData
from app.config import PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY

payos_client = PayOS(
    client_id=PAYOS_CLIENT_ID,
    api_key=PAYOS_API_KEY,
    checksum_key=PAYOS_CHECKSUM_KEY
)

def create_payment_link(order_code: int, amount: int, description: str, items: list) -> str:
    """Tạo link thanh toán từ PayOS, trả về URL của mã QR thanh toán"""
    try:
        # Chuẩn bị dữ liệu
        item_data_list = []
        for line in items:
            item_data_list.append(ItemData(name=line['name'], quantity=line['quantity'], price=line['price']))
            
        payment_data = PaymentData(
            orderCode=order_code,
            amount=amount,
            description=description,
            items=item_data_list,
            cancelUrl="https://google.com",
            returnUrl="https://google.com"
        )
        
        payment_link = payos_client.createPaymentLink(payment_data)
        
        return payment_link.checkoutUrl
        
    except Exception as e:
        print("Tạo payment link thất bại:", e)
        return ""

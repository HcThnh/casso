import json
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY
from app.state import carts, append_chat_message, get_chat_history
from app.menu import get_menu_text, get_item_details

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

tools = [
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Thêm một món (thức uống hoặc topping) vào giỏ hàng của khách.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "Mã món ăn/topping (vd TS01, TOP01)"},
                    "size": {"type": "string", "enum": ["M", "L", ""], "description": "Size M hoặc L. Bỏ qua nếu là topping."},
                    "quantity": {"type": "integer", "description": "Số lượng"}
                },
                "required": ["item_id", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_cart",
            "description": "Xoá một món khỏi giỏ hàng nếu khách đổi ý.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"}
                },
                "required": ["item_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "checkout",
            "description": "Kích hoạt chức năng thanh toán khi khách hàng báo chốt đơn, tạo link thanh toán chuyển khoản.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def get_system_prompt() -> str:
    menu = get_menu_text()
    sys_prompt = f"""Bạn là một người mẹ hiền lành, bán quán trà sữa gần khu văn phòng. 
Giọng điệu giao tiếp của bạn ân cần, chân chất, gọi khách bằng 'con', xưng 'cô' hoặc xưng 'mẹ' với 'con'.
Nhiệm vụ của bạn:
1. Chào hỏi, gửi menu nếu khách hỏi.
2. Hỏi rõ size (M hoặc L) và xem khách có muốn thêm topping không khi khách chọn món.
3. Sử dụng tool `add_to_cart` để thêm vào giỏ hàng NGAY SAU KHI khách chốt món (ví dụ khách nói: 'cho con 1 trà sữa đen size M' => gọi tool luôn).
4. Nếu khách muốn xoá món, gọi `remove_from_cart`.
5. Khi khách quyết định tính tiền hoặc chốt đơn, CẦN BÁO cho khách biết tổng cộng các món và gọi hàm `checkout`. KHÔNG TỰ BỊA RA link thanh toán hoặc QR, tool `checkout` sẽ đảm nhận việc tạo QR. Bạn chỉ việc gọi tool và báo khách chờ giây lát.
TUYỆT ĐỐI không chém gió món ngoài menu.

Dưới đây là Menu:
{menu}
"""
    return sys_prompt

async def process_user_message(user_id: str, message: str) -> str:
    """Xử lý tin nhắn và trả về câu trả lời, có thể sinh ra event đặc biệt nếu gọi checkout"""
    append_chat_message(user_id, "user", message)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    for msg in get_chat_history(user_id):
        if "role" in msg and "content" in msg:
            if msg["content"] is not None:
                messages.append({"role": msg["role"], "content": msg["content"]})
    
    clean_msgs = [m for m in messages if m["role"] in ["system", "user", "assistant"]]

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=clean_msgs,
            tools=tools,
            tool_choice="auto",
            temperature=0.7
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            tool_calls = response_message.tool_calls
            tool_res_text = ""
            is_checkout = False
            
            for tool_call in tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if fn_name == "add_to_cart":
                    item_id = args.get("item_id")
                    qty = args.get("quantity", 1)
                    size = args.get("size", "M").upper()
                    
                    details = get_item_details(item_id)
                    if not details:
                        tool_res_text += f"Hệ thống: Không tìm thấy món {item_id}.\n"
                        continue
                    
                    price = details["price_l"] if size == "L" else details["price_m"]
                    
                    carts.add_item(user_id, {
                        "item_id": item_id,
                        "name": details["name"],
                        "size": size if size in ["M", "L"] else "",
                        "quantity": qty,
                        "toppings": [],
                        "price": price,
                        "total": price * qty
                    })
                    tool_res_text += f"Hệ thống: Đã thêm {qty} {details['name']} (Size {size}) vào giỏ hàng. Tổng {price*qty} VND.\n"
                
                elif fn_name == "remove_from_cart":
                    item_id = args.get("item_id")
                    if carts.remove_item(user_id, item_id):
                        tool_res_text += f"Hệ thống: Đã xoá món {item_id} khỏi giỏ.\n"
                    else:
                        tool_res_text += f"Hệ thống: Món {item_id} không có trong giỏ.\n"
                
                elif fn_name == "checkout":
                    is_checkout = True
                    tool_res_text += "Hệ thống: Đang tạo mã QR thanh toán...\n"

            clean_msgs.append(response_message)
            for i, tool_call in enumerate(tool_calls):
                result = tool_res_text if i == len(tool_calls)-1 else "ok"
                clean_msgs.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.function.name, "content": result})
            
            final_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=clean_msgs,
                temperature=0.7
            )
            final_text = final_response.choices[0].message.content
            append_chat_message(user_id, "assistant", final_text)
            
            if is_checkout:
                return final_text + "||CHECKOUT_TRIGGERED||"
            return final_text
            
        else:
            final_text = response_message.content
            append_chat_message(user_id, "assistant", final_text)
            return final_text

    except Exception as e:
        print("OpenAI Error:", e)
        return "Con đợi cô chút nha, cô đang tính nhẩm hơi chậm (Lỗi kết nối AI)."

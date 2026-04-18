import pandas as pd
import os
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MENU_PATH = os.path.join(BASE_DIR, "Menu.csv")

def get_menu_text() -> str:
    """Đọc menu từ CSV và chuyển thành chuỗi văn bản format đẹp cho AI hiểu"""
    try:
        df = pd.read_csv(MENU_PATH)
        text = "MENU CỦA QUÁN TRÀ SỮA (Vui lòng tư vấn khách chọn size M hoặc L nếu áp dụng, và gợi ý topping):\n\n"
        
        grouped = df.groupby('category')
        for cat, group in grouped:
            text += f"[{cat.upper()}]\n"
            for _, row in group.iterrows():
                item_id = row['item_id']
                name = row['name']
                desc = row['description'] if pd.notna(row['description']) else ""
                pm = int(row['price_m'])
                pl = int(row['price_l'])
                if pl == pm:
                    price_str = f"Giá: {pm:,} VND"
                else:
                    price_str = f"Giá: Size M - {pm:,} VND | Size L - {pl:,} VND"
                text += f"- {item_id} | Tên: {name} ({desc}). {price_str}\n"
            text += "\n"
        text += "Lưu ý khách hàng:\n- Mọi món Topping không có size, vui lòng để size là Mặc định/Trống khi thêm vào giỏ.\n- Vui lòng hỏi kỹ số lượng trước khi thêm."
        return text
    except Exception as e:
        print(f"Error reading menu: {e}")
        return "Không lấy được dữ liệu Menu. Xin lỗi quý khách."

def get_item_details(item_id: str) -> Optional[Dict[str, Any]]:
    """Trả về chi tiết món dựa vào item_id"""
    try:
        df = pd.read_csv(MENU_PATH)
        row = df[df['item_id'] == item_id]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "item_id": r['item_id'],
            "name": r['name'],
            "price_m": int(r['price_m']),
            "price_l": int(r['price_l'])
        }
    except:
        return None

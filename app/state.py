from typing import Dict, List, Any
from pydantic import BaseModel

class CartItem(BaseModel):
    item_id: str
    name: str 
    size: str
    quantity: int
    toppings: List[str] = []
    price: int
    total: int

class CartCache:
    def __init__(self):
        self._carts: Dict[str, List[Dict[str, Any]]] = {}

    def get_cart(self, user_id: str) -> List[Dict[str, Any]]:
        return self._carts.get(user_id, [])

    def add_item(self, user_id: str, item: Dict[str, Any]):
        if user_id not in self._carts:
            self._carts[user_id] = []
        self._carts[user_id].append(item)

    def remove_item(self, user_id: str, item_id: str) -> bool:
        """Xoá một món khỏi giỏ hàng bằn item_id, trả về True nếu xoá thành công"""
        cart = self.get_cart(user_id)
        for i, item in enumerate(cart):
            if item.get("item_id") == item_id:
                cart.pop(i)
                return True
        return False

    def clear_cart(self, user_id: str):
        if user_id in self._carts:
            self._carts[user_id] = []

    def get_total(self, user_id: str) -> int:
        cart = self.get_cart(user_id)
        return sum(item.get("total", 0) for item in cart)

carts = CartCache()

chat_histories: Dict[str, List[Dict[str, str]]] = {}

def get_chat_history(user_id: str) -> List[Dict[str, str]]:
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    return chat_histories[user_id]

def append_chat_message(user_id: str, role: str, content: str):
    history = get_chat_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > 20:
        chat_histories[user_id] = history[-20:]

order_code_to_user: Dict[int, str] = {}

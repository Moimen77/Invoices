import mysql
import Database.connection
from rapidfuzz import fuzz

# 📌 إحضار الكلمات المفتاحية للعميل
def get_keywords_from_db(client_id: int):
    conn = conn
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT k.keyword, k.lang, i.item_id, i.product_name, i.unit_price
        FROM keywords k
        JOIN inventory i ON k.item_id = i.item_id
        WHERE i.client_id = %s
        """,
        (client_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def match_product_with_keywords(product_name, all_keywords, inventory_items):
    if not product_name:
        return None

    product_name_lower = product_name.lower().strip()

    # ✅ التطابق التام أولاً
    for kw in all_keywords:
        if kw["keyword"].lower().strip() == product_name_lower:
            return next((i for i in inventory_items if i["item_id"] == kw["item_id"]), None)

    # 🔍 التطابق بالتشابه
    best_match = None
    best_score = 0
    for kw in all_keywords:
        score = fuzz.token_set_ratio(product_name_lower, kw["keyword"].lower().strip())
        if kw["lang"] == "ar":
            score += 5  # أولوية للعربية
        if score > best_score:
            best_score = score
            best_match = kw

    if best_score < 80:
        return None

    matched_item = next((i for i in inventory_items if i["item_id"] == best_match["item_id"]), None)
    return matched_item

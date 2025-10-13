from .connection import get_connection

def get_keywords_by_client(client_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT k.keyword, k.lang, i.item_id, i.product_name, i.unit_price
        FROM keywords k
        JOIN inventory i ON k.item_id = i.item_id
        WHERE i.client_id = %s
    """, (client_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

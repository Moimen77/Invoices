from Database.connection import get_connection


def get_invoice_by_id(invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 جلب بيانات الفاتورة
    cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    invoice = cursor.fetchone()

    if not invoice:
        cursor.close()
        conn.close()
        return None

    # 🔹 جلب العناصر المرتبطة بالفاتورة
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
    invoice["items"] = cursor.fetchall()

    cursor.close()
    conn.close()
    return invoice


def update_invoice_by_id(invoice_id: int, data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    # 🛠️ بناء جملة SQL ديناميكية لتحديث الحقول الموجودة فقط
    fields = []
    values = []

    for key, value in data.items():
        fields.append(f"{key} = %s")
        values.append(value)

    if not fields:
        return False

    sql = f"UPDATE invoices SET {', '.join(fields)} WHERE id = %s"
    values.append(invoice_id)

    cursor.execute(sql, tuple(values))
    conn.commit()

    updated = cursor.rowcount > 0

    cursor.close()
    conn.close()
    return updated

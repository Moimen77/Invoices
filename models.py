from Database.connection import get_connection

def create_invoices_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            client_id INT,
            supplier_name VARCHAR(255),
            invoice_number VARCHAR(100),
            issue_date VARCHAR(50),
            image_url TEXT,
            total_amount DECIMAL(12,2),
            status VARCHAR(70),    
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,     
            FOREIGN KEY (`client_id`) REFERENCES `clients`(`client_id`) ON DELETE CASCADE ON UPDATE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            invoice_id INT,
            product_name VARCHAR(255),
            alt_name VARCHAR(255),
            quantity FLOAT,
            unit_of_measure VARCHAR(50),
            unit_price DECIMAL(10,2),
            total_before_discount DECIMAL(10,2),
            discount DECIMAL(10,2),
            total_after_discount DECIMAL(10,2),          
            vat_amount DECIMAL(10,2),
            final_total_per_product DECIMAL(10,2),
            category VARCHAR(100),
            matched_inventory VARCHAR(255),
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()


from datetime import datetime

def save_invoice(client_id, supplier, invoice, invoicesummary, products, image_url):
    conn = get_connection()
    cursor = conn.cursor()

    total_amount = invoicesummary.get("final_invoice_total", 0)
    invoice_number = invoice.get("invoice_number")
    issue_date = invoice.get("issue_date")
    supplier_name = supplier.get("name", "")

    # ✅ تحويل issue_date من dd-mm-yyyy إلى datetime.date
    issue_date_obj = None
    if issue_date:
        try:
            issue_date_obj = datetime.strptime(issue_date, "%d-%m-%Y").date()
        except ValueError:
            print(f"⚠️ تنسيق التاريخ غير متوقع: {issue_date}")
            issue_date_obj = None

    try:
        cursor.execute("""
            INSERT INTO invoices (client_id, supplier_name, invoice_number, issue_date, image_url, total_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            client_id,
            supplier_name,
            invoice_number,
            issue_date_obj,  
            image_url,
            total_amount,
            "pending"
        ))

        invoice_id = cursor.lastrowid

        for p in products:
            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, product_name, alt_name, quantity, unit_of_measure, 
                    unit_price, total_before_discount, discount, total_after_discount, vat_amount, final_total_per_product, 
                    category, matched_inventory
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                invoice_id,
                p.get("product_name"),
                p.get("alt_name"),
                p.get("quantity"),
                p.get("unit_of_measure"),
                p.get("unit_price"),
                p.get("total_before_discount"),
                p.get("discount_amount"),
                p.get("total_after_discount"),
                p.get("vat_amount"),
                p.get("final_total_per_product"),
                p.get("category"),
                p.get("matched_inventory"),
            ))

        conn.commit()
        print("✅ تم حفظ الفاتورة بنجاح\n")

    except Exception as e:
        print("❌ خطأ أثناء حفظ الفاتورة:", e)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()



def get_invoices_filtered(client_id=None, date_from=None, date_to=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # بناء الـ SQL حسب الفلاتر
    query = "SELECT * FROM invoices WHERE 1=1"
    params = []

    if client_id:
        query += " AND client_id = %s"
        params.append(client_id)

    if date_from:
        query += " AND issue_date >= %s"
        params.append(date_from)

    if date_to:
        query += " AND issue_date <= %s"
        params.append(date_to)

    # لو مفيش أي فلتر، رجّع آخر 50 فقط
    if not (client_id or date_from or date_to):
        query += " ORDER BY id DESC LIMIT 50"
    else:
        query += " ORDER BY id DESC"

    cursor.execute(query, tuple(params))
    invoices = cursor.fetchall()

    # جلب تفاصيل المنتجات لكل فاتورة
    for inv in invoices:
        cursor.execute("""
            SELECT id, product_name,matched_inventory, quantity, unit_of_measure, unit_price,total_before_discount,discount,total_after_discount, vat_amount,  final_total_per_product, category
            FROM invoice_items
            WHERE invoice_id = %s
        """, (inv["id"],))
        inv["items"] = cursor.fetchall()

    cursor.close()
    conn.close()

    return invoices

def get_inventory_by_client(client_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # جلب أصناف المخزون
    cursor.execute("""
        SELECT item_id as id, product_name as item_name, unit_of_measure, Min_Unit, unit_price
        FROM inventory WHERE client_id = %s ORDER BY item_id DESC
    """, (client_id,))
    inventory_items = cursor.fetchall()

    if not inventory_items:
        cursor.close()
        conn.close()
        return []

    # جلب الكلمات المفتاحية
    item_ids = [item['id'] for item in inventory_items]
    format_strings = ','.join(['%s'] * len(item_ids))
    cursor.execute(f"""
        SELECT item_id, keyword FROM keywords WHERE item_id IN ({format_strings})
    """, tuple(item_ids))
    keywords = cursor.fetchall()

    # دمج الكلمات المفتاحية مع الأصناف
    keywords_map = {}
    for kw in keywords:
        if kw['item_id'] not in keywords_map:
            keywords_map[kw['item_id']] = []
        keywords_map[kw['item_id']].append(kw['keyword'])

    for item in inventory_items:
        item['keywords'] = keywords_map.get(item['id'], [])

    cursor.close()
    conn.close()
    return inventory_items


def add_inventory_item(item_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inventory (client_id, product_name, unit_of_measure, Min_Unit, unit_price)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        item_data.get("client_id"),
        item_data.get("item_name"),
        item_data.get("unit_of_measure"),
        item_data.get("min_unit"),
        item_data.get("unit_price")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id




def add_new_client(client_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO clients (client_name, username, password)
            VALUES (%s, %s, %s)
        """, (
            client_data.get("client_name"),
            client_data.get("username"),
            client_data.get("password")
        ))
        conn.commit()
        new_id = cursor.lastrowid
        return new_id
    except Exception as e:
        print(f"❌ Error adding new client: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def add_keyword_for_item(keyword_data: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO keywords (client_id, item_id, keyword, lang)
        VALUES (%s, %s, %s, %s)
    """, (
        keyword_data.get("client_id"),
        keyword_data.get("item_id"),
        keyword_data.get("keyword"),
        keyword_data.get("lang", "ar") # Default to 'ar'
    ))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id

def get_invoices_by_client_name(client_name: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM invoices 
        WHERE client_name = %s
        ORDER BY id DESC
    """, (client_name,))
    invoices = cursor.fetchall()
    cursor.close()
    conn.close()
    return invoices

def get_all_clients():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients ORDER BY client_id DESC")
    clients = cursor.fetchall()
    conn.close()
    return clients


def delete_invoice_by_id(invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    # تأكد إن الفاتورة موجودة
    cursor.execute("SELECT id FROM invoices WHERE id = %s", (invoice_id,))
    invoice = cursor.fetchone()
    if not invoice:
        cursor.close()
        conn.close()
        return False

    # امسح العناصر المرتبطة بالفاتورة
    cursor.execute("DELETE FROM invoice_items WHERE invoice_id = %s", (invoice_id,))

    # امسح الفاتورة نفسها
    cursor.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
    conn.commit()

    cursor.close()
    conn.close()
    return True

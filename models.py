from Database.connection import get_connection

def create_invoices_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            client_id INT,
            client_name VARCHAR(255),
            supplier_name VARCHAR(255),
            invoice_number VARCHAR(100),
            issue_date VARCHAR(50),
            image_url TEXT,
            total_amount DECIMAL(12,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def save_invoice(client_id, client_name, supplier, invoice, products, image_url, total_amount, status="pending"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO invoices (
            client_id, client_name, supplier_name, invoice_number, issue_date, image_url, total_amount, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        client_id,
        client_name,
        supplier,
        invoice.get("invoice_number"),
        invoice.get("issue_date"),
        image_url,
        total_amount,
        status
    ))

    invoice_id = cursor.lastrowid

    for p in products:
        cursor.execute("""
            INSERT INTO invoice_items (
                invoice_id, product_name, alt_name, quantity, unit_of_measure, 
                unit_price, total_before_discount, vat_amount, final_total_per_product, 
                category, matched_inventory
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            invoice_id,
            p.get("product_name"),
            p.get("alt_name"),
            p.get("quantity"),
            p.get("unit_of_measure"),
            p.get("unit_price"),
            p.get("total_before_discount"),
            p.get("vat_amount"),
            p.get("final_total_per_product"),
            p.get("category"),
            p.get("matched_inventory")
        ))

    conn.commit()
    cursor.close()
    conn.close()


def get_invoices_by_client_id(client_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 🧾 جلب كل الفواتير الخاصة بالعميل
    cursor.execute("""
        SELECT * FROM invoices
        WHERE client_id = %s
        ORDER BY id DESC
    """, (client_id,))
    invoices = cursor.fetchall()

    # 📦 جلب كل المنتجات المرتبطة بكل فاتورة
    for inv in invoices:
        cursor.execute("""
            SELECT * FROM invoice_items
            WHERE invoice_id = %s
        """, (inv["id"],))
        inv["items"] = cursor.fetchall()

    cursor.close()
    conn.close()

    return invoices


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
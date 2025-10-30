import tempfile
from typing import Optional
from fastapi import APIRouter, Body, FastAPI, HTTPException, Path, Query
from fastapi.responses import FileResponse
from Database.connection import get_connection
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import openpyxl

from models import (
    create_invoices_table,
    add_inventory_item,
    add_new_client,
    add_keyword_for_item,
    delete_invoice_by_id,
    get_all_clients,
    get_inventory_by_client,
    get_invoices_by_client_name,
    get_invoices_filtered
)

from routers import upload_routes
from routers.UpdateRouters import get_invoice_by_id, update_invoice_by_id

app = FastAPI(
    title="Invoice AI API",
    description="API لتحليل الفواتير باستخدام الذكاء الصناعي وتسجيلها في قاعدة البيانات",
    version="1.0"
)

# 🟢 تفعيل CORS للـ Front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # أو ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 جعل الصور متاحة عبر /images
app.mount("/images", StaticFiles(directory="images"), name="images")

# 🔗 ربط راوتر رفع الفواتير
app.include_router(upload_routes.router)

# 🧾 راوتر الفواتير
invoices_router = APIRouter(prefix="/invoices", tags=["Invoices"])

@invoices_router.post("/add")
def add_client(client_data: dict = Body(...)):
    try:
        client_id = add_new_client(client_data)
        if not client_id:
            raise HTTPException(status_code=400, detail="Failed to add client, maybe username exists.")
        return {"status": "success", "message": "Client added successfully", "client_id": client_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@invoices_router.get("/filter")
def filter_invoices(
    client_id: Optional[int] = None,
    date_from: Optional[str] = Query(None, description="DD-MM-YYYY"),
    date_to: Optional[str] = Query(None, description="DD-MM-YYYY")
):
    try:
        invoices = get_invoices_filtered(client_id, date_from, date_to)
        return {"status": "success", "total": len(invoices), "data": invoices}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@invoices_router.get("/client/name/{client_name}")
def get_invoices_by_client_name_route(client_name: str):
    invoices = get_invoices_by_client_name(client_name)
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for this client name")
    return {"status": "success", "total": len(invoices), "data": invoices}



@invoices_router.get("/{invoice_id}")
def get_invoice(invoice_id: int = Path(..., description="رقم الفاتورة")):
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الفاتورة")
    return {"status": "success", "data": invoice}


@invoices_router.delete("/delete/{invoice_id}")
def delete_invoice(invoice_id: int):
    deleted = delete_invoice_by_id(invoice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"status": "success", "message": f"Invoice {invoice_id} deleted successfully"}


@invoices_router.get("/inventory/client/{client_id}")
async def get_client_inventory(client_id: int):
    inventory_items = get_inventory_by_client(client_id)
    return {"status": "success", "data": inventory_items}

@invoices_router.put("/invoices/{invoice_id}/items/{item_id}")
async def update_invoice_item(invoice_id: int, item_id: int, item_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE invoice_items SET
            product_name = %s,
            matched_inventory = %s,
            quantity = %s,
            unit_price = %s,
            category = %s
        WHERE id = %s AND invoice_id = %s
    """, (
        item_data.get("product_name"),
        item_data.get("matched_inventory"),
        item_data.get("quantity"),
        item_data.get("unit_price"),
        item_data.get("category"),
        item_id,
        invoice_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "success", "message": "✅ تم تحديث بيانات الصنف بنجاح"}


# 🟡 2️⃣ API لتحديث الفاتورة حسب الـ ID
@invoices_router.put("/update/{invoice_id}")
def update_invoice(invoice_id: int, data: dict = Body(...)):
    try:
        updated = update_invoice_by_id(invoice_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="لم يتم العثور على الفاتورة لتحديثها")
        return {"status": "success", "message": "تم تحديث الفاتورة بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# 👥 راوتر العملاء
clients_router = APIRouter(prefix="/clients", tags=["Clients"])

@invoices_router.get("/export/excel")
def export_invoices_to_excel(
    client_id: Optional[int] = None,
    date_from: Optional[str] = Query(None, description="DD-MM-YYYY"),
    date_to: Optional[str] = Query(None, description="DD-MM-YYYY")
):
    try:
        # 🧾 جلب الفواتير مع البنود
        invoices = get_invoices_filtered(client_id, date_from, date_to)
        if not invoices:
            raise HTTPException(status_code=404, detail="لا توجد فواتير لتصديرها")

        # 📘 إنشاء ملف Excel جديد
        wb = openpyxl.Workbook()

        # -------------------------------
        # 🧩 الشيت الأول: الفواتير الإجمالية
        # -------------------------------
        ws1 = wb.active
        ws1.title = "الفواتير الإجمالية"

        ws1.append([
            "رقم الفاتورة",
            "اسم المورد",
            "تاريخ الفاتورة",
            "الإجمالي النهائي",
            "عدد البنود",
            "رابط الصورة"
        ])

        for inv in invoices:
            ws1.append([
                inv.get("invoice_number", ""),
                inv.get("supplier_name", ""),
                inv.get("issue_date", ""),
                inv.get("total_amount", ""),
                len(inv.get("items", [])),
                inv.get("image_url", "")
            ])

        # -------------------------------
        # 🧾 الشيت الثاني: تفاصيل البنود
        # -------------------------------
        ws2 = wb.create_sheet("تفاصيل البنود")

        headers = [
            "اسم المورد",
            "رقم الفاتورة",
            "تاريخ الفاتورة",
            "اسم المنتج",
            "الصنف المقابل",
            "التصنيف الكلمية",
            "الوحدة",
            "سعر الوحدة",
            "السعر قبل الخصم",
            "الخصم",
            "السعر بعد الخصم",
            "الضريبة",
            "السعر النهائي",
            "رابط الصورة"
        ]
        ws2.append(headers)

        for inv in invoices:
            client_name = inv.get("client_db_name", inv.get("client_name", ""))
            supplier_name = inv.get("supplier_name", "")
            invoice_number = inv.get("invoice_number", "")
            issue_date = inv.get("issue_date", "")
            image_url = inv.get("image_url", "")

            for item in inv.get("items", []):
                ws2.append([
                    supplier_name,
                    invoice_number,
                    issue_date,
                    item.get("product_name", ""),
                    item.get("matched_inventory", ""),
                    item.get("category", ""),
                    item.get("unit_of_measure", ""),
                    item.get("unit_price", ""),
                    item.get("total_before_discount", ""),
                    item.get("discount", ""),
                    item.get("total_after_discount", ""),
                    item.get("vat_amount", ""),
                    item.get("final_total_per_product", ""),
                    image_url
                ])

        # 💾 حفظ الملف مؤقتًا
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        wb.save(temp_file.name)
        wb.close()

        # 📤 إرسال الملف للمستخدم
        filename = "invoices_export.xlsx"
        return FileResponse(
            path=temp_file.name,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@clients_router.get("/get_clients")
def get_clients():
    clients = get_all_clients()
    if not clients:
        raise HTTPException(status_code=404, detail="No clients found")
    return {"status": "success", "total": len(clients), "data": clients}

@clients_router.post("/add")
def add_client(client_data: dict = Body(...)):
    try:
        client_id = add_new_client(client_data)
        if not client_id:
            raise HTTPException(status_code=400, detail="Failed to add client, maybe username exists.")
        return {"status": "success", "message": "Client added successfully", "client_id": client_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])

@inventory_router.post("/add")
def add_item(item_data: dict = Body(...)):
    item_id = add_inventory_item(item_data)
    return {"status": "success", "message": "Item added successfully", "item_id": item_id}

keywords_router = APIRouter(prefix="/keywords", tags=["Keywords"])
@keywords_router.post("/add")
def add_keyword(keyword_data: dict = Body(...)):
    keyword_id = add_keyword_for_item(keyword_data)
    return {"status": "success", "message": "Keyword added successfully", "keyword_id": keyword_id}

app.include_router(invoices_router)
app.include_router(clients_router)
app.include_router(inventory_router)
app.include_router(keywords_router)
# 🧱 إنشاء الجداول عند بدء السيرفر
@app.on_event("startup")
def init_db():
    create_invoices_table()

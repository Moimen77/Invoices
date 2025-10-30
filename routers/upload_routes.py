from fastapi import APIRouter, WebSocket, UploadFile, Form
from typing import List
import os, json
from pdf2image import convert_from_bytes
from services.ai_parser import parse_invoice_from_image
from ReaderApi import get_keywords_from_db
from services.matching import match_product_with_keywords
from models import save_invoice

router = APIRouter(prefix="/upload", tags=["Invoices"])
os.makedirs("images", exist_ok=True)

# 🔌 تخزين WebSocket لكل عميل نشط
active_connections = {}

@router.websocket("/ws/progress/{client_id}")
async def websocket_progress(websocket: WebSocket, client_id: int):
    await websocket.accept()
    active_connections[client_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # لتجنب timeout
    except Exception:
        print(f"⚠️ تم إغلاق WebSocket للعميل {client_id}")
    finally:
        active_connections.pop(client_id, None)


@router.post("/invoices/")
async def upload_invoices(files: List[UploadFile], client_id: int = Form(...)):
    websocket = active_connections.get(client_id)
    keywords = get_keywords_from_db(client_id)
    results = []
    total_files = len(files)

    if websocket:
        await websocket.send_text(f"🚀 بدء رفع {total_files} ملف...")

    for file_index, file in enumerate(files, start=1):
        filename = file.filename
        try:
            if websocket:
                await websocket.send_text(f"📂 [{file_index}/{total_files}] معالجة الملف: {filename}")

            # 🧾 لو PDF
            if filename.lower().endswith(".pdf"):
                pdf_bytes = await file.read()
                pages = convert_from_bytes(pdf_bytes, dpi=150, poppler_path=r"C:\\poppler-25.07.0\\Library\\bin")
                total_pages = len(pages)

                for page_index, page in enumerate(pages, start=1):
                    image_name = f"{filename}_page{page_index}.jpg"
                    image_path = os.path.join("images", image_name)
                    page.save(image_path, "JPEG")

                    if websocket:
                        await websocket.send_text(f"🔍 تحليل الصفحة {page_index}/{total_pages}...")

                    # 🧠 تحليل الفاتورة
                    data = parse_invoice_from_image(image_path)
                    supplier = data.get("supplier_details", {})
                    invoice = data.get("invoice_details", {})
                    invoice_summary = data.get("invoice_summary", {})
                    products = data.get("products", [])

                    # 🧩 مطابقة المنتجات
                    inventory = [
                        {"item_id": k["item_id"], "product_name": k["product_name"], "unit_price": k["unit_price"]}
                        for k in keywords
                    ]
                    for p in products:
                        match = match_product_with_keywords(p["product_name"], keywords, inventory)
                        p["matched_inventory"] = match["product_name"] if match else ""

                    image_url = f"http://localhost:8000/images/{image_name}"

                    # 🗃️ حفظ البيانات
                    save_invoice(client_id, supplier, invoice, invoice_summary, products, image_url)

                    results.append({
                        "file": filename,
                        "page": page_index,
                        "supplier_details": supplier,
                        "invoice_details": invoice,
                        "invoice_summary": invoice_summary,
                        "products": products,
                        "image_url": image_url,
                        "status": "✅ تمت المعالجة"
                    })

                    if websocket:
                        await websocket.send_text(f"💾 تم حفظ الفاتورة من الصفحة {page_index} بنجاح ✅")

            # 🖼️ صورة مفردة
            else:
                image_path = os.path.join("images", filename)
                with open(image_path, "wb") as f:
                    f.write(await file.read())

                if websocket:
                    await websocket.send_text(f"🖼️ تم حفظ الصورة {filename}، جاري التحليل...")

                data = parse_invoice_from_image(image_path)
                supplier = data.get("supplier_details", {})
                invoice = data.get("invoice_details", {})
                invoice_summary = data.get("invoice_summary", {})
                products = data.get("products", [])

                inventory = [
                    {"item_id": k["item_id"], "product_name": k["product_name"], "unit_price": k["unit_price"]}
                    for k in keywords
                ]
                for p in products:
                    match = match_product_with_keywords(p["product_name"], keywords, inventory)
                    p["matched_inventory"] = match["product_name"] if match else ""

                image_url = f"http://localhost:8000/images/{filename}"

                save_invoice(client_id, supplier, invoice, invoice_summary, products, image_url)

                results.append({
                    "file": filename,
                    "supplier_details": supplier,
                    "invoice_details": invoice,
                    "invoice_summary": invoice_summary,
                    "products": products,
                    "image_url": image_url,
                    "status": "✅ تمت المعالجة"
                })

                if websocket:
                    await websocket.send_text(f"✅ تم تحليل الصورة {filename} وحفظها بنجاح")

        except Exception as e:
            error_msg = f"❌ خطأ أثناء معالجة {filename}: {str(e)}"
            print(error_msg)
            if websocket:
                await websocket.send_text(error_msg)
            results.append({
                "file": filename,
                "status": "❌ فشل التحليل",
                "error": str(e)
            })

    if websocket:
        await websocket.send_text(f"🎯 تم الانتهاء من معالجة {len(results)} ملف ✅")

    # 📦 إرجاع البيانات كاملة
    return {
        "client_id": client_id,
        "total_files": total_files,
        "processed_files": len(results),
        "results": results
    }

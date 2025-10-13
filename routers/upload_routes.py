from fastapi import APIRouter, UploadFile, Form
from typing import List
import os, json
from PIL import Image
from pdf2image import convert_from_bytes
from services.ai_parser import parse_invoice_from_image
from ReaderApi import get_keywords_from_db
from services.matching import match_product_with_keywords
from models import save_invoice
from fastapi.staticfiles import StaticFiles

router = APIRouter(prefix="/upload", tags=["Invoices"])

os.makedirs("images", exist_ok=True)

@router.post("/invoices/")
async def upload_invoices(files: List[UploadFile], client_id: int = Form(...), client_name: str = Form(...)):
    keywords = get_keywords_from_db(client_id)
    results = []

    for file in files:
        try:
            if file.filename.lower().endswith(".pdf"):
                pdf_bytes = await file.read()
                pages = convert_from_bytes(pdf_bytes, dpi=150, poppler_path=r"C:\\poppler-25.07.0\\Library\\bin")
                for idx, page in enumerate(pages, start=1):
                    image_name = f"{file.filename}_page{idx}.jpg"
                    image_path = os.path.join("images", image_name)
                    page.save(image_path, "JPEG")
                    image_url = f"http://localhost:8000/images/{image_name}"

                    data = parse_invoice_from_image(image_path)
                    supplier = data.get("supplier_details", {}).get("name", "")
                    invoice = data.get("invoice_details", {})
                    invoice_summary = data.get("invoice_summary", {})
                    products = data.get("product_details", [])
                     
                    
                    inventory = [{"item_id": k["item_id"], "product_name": k["product_name"], "unit_price": k["unit_price"]} for k in keywords]
                    # 🧠 Matching products
                    for p in products:
                        match = match_product_with_keywords(p["product_name"], keywords, inventory)
                        p["matched_inventory"] = match["product_name"] if match else ""

                    # 💾 Save invoice to DB
                    save_invoice(client_id, client_name, supplier, invoice, invoice_summary, products, image_url)

                    # ✅ Add to results in detailed format
                    results.append({
                        "file": file.filename,
                        "page": idx,
                        "status": "✅ تمت المعالجة",
                        "rows_added": len(products),
                        "image_url": image_url,
                        "invoice_data": {
                            "invoice_details": data.get("invoice_details", {}),
                            "supplier_details": data.get("supplier_details", {}),
                            "client_details": data.get("client_details", {}),
                            "product_details": data.get("product_details", []),
                            "invoice_summary": data.get("invoice_summary", {})
                        }
                    })

            else:
                image_path = os.path.join("images", file.filename)
                with open(image_path, "wb") as f:
                    f.write(await file.read())
                image_url = f"http://localhost:8000/images/{file.filename}"

                data = parse_invoice_from_image(image_path)
                supplier = data.get("supplier_details", {}).get("name", "")
                invoice = data.get("invoice_details", {})
                invoice_summary = data.get("invoice_summary", {})
                products = data.get("product_details", [])
                
                inventory = [{"item_id": k["item_id"], "product_name": k["product_name"], "unit_price": k["unit_price"]} for k in keywords]
                for p in products:
                    match = match_product_with_keywords(p["product_name"], keywords, inventory)
                    p["matched_inventory"] = match["product_name"] if match else ""

                save_invoice(client_id, client_name, supplier, invoice, invoice_summary, products, image_url)

                results.append({
                    "file": file.filename,
                    "status": "✅ تمت المعالجة",
                    "rows_added": len(products),
                    "image_url": image_url,
                    "invoice_data": {
                        "invoice_details": data.get("invoice_details", {}),
                        "supplier_details": data.get("supplier_details", {}),
                        "client_details": data.get("client_details", {}),
                        "product_details": data.get("product_details", []),
                        "invoice_summary": data.get("invoice_summary", {})
                    }
                })

        except Exception as e:
            results.append({
                "file": file.filename,
                "status": "❌ خطأ أثناء المعالجة",
                "error": str(e)
            })

    return {
        "total": len(results),
        "processed": results
    }

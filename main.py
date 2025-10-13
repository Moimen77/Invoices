from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from models import create_invoices_table, get_invoices_by_client_id
from routers import upload_routes

app = FastAPI(
    title="Da3em Invoice AI API",
    description="API لتحليل الفواتير باستخدام الذكاء الصناعي وتسجيلها في قاعدة البيانات",
    version="1.0"
)

# 📁 إعداد مجلد الصور ليكون متاح عبر الويب
app.mount("/images", StaticFiles(directory="images"), name="images")

# 🔗 ربط الراوتر (اللي فيه /upload/invoices)
app.include_router(upload_routes.router)

router = APIRouter(prefix="/invoices", tags=["Invoices"])



@router.get("/client/{client_id}")
def get_invoices_by_client(client_id: int):
    invoices = get_invoices_by_client_id(client_id)
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for this client")
    return {"status": "success", "total": len(invoices), "data": invoices}

app.include_router(router)

# 🧱 إنشاء الجداول أول ما السيرفر يشتغل
@app.on_event("startup")
def init_db():
    create_invoices_table()

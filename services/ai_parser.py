import google.generativeai as genai
from PIL import Image
import json

genai.configure(api_key="AIzaSyBDhIS_HQauE6BLCwD0qoa2MWGJHTLDIwk")
model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

def clean_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text

def parse_invoice_from_image(image_path: str):
    img = Image.open(image_path)
    prompt = """حلل لي فاتورة المرفقة واستخرج كل التفاصيل الممكنة في صيغة JSON بدون أي نصوص إضافية.
📌 مهم:
- لو المنتج بلغتين (عربي + إنجليزي) خُذ العربي كـ "product_name" والإنجليزي كـ "alt_name".
- الأولوية للعربي في المطابقة والحفظ.

- بالنسبة للمنتجات:
  🔹 حدد category (فئة المنتج) بشكل ذكي حسب نوعه، مثل:
    - حليب، لبن، جبن → منتجات ألبان
    - بيض → دواجن
    - زيت، دقيق، أرز → مواد غذائية
    - ماء، عصير، مشروبات غازية → مشروبات
    - لحم، دجاج → لحوم
    - كرتون، ورق، شنطة → مواد تغليف
    - طماطم، خيار، خس → خضار
    مواد مخزنية 
    مستشفي  تنقل و 
    - تفاح، موز، برتقال → فواكه
    - غير ذلك → أخرى
- نفس بنية JSON التالية بدقة:
{
  "invoice_details": {"invoice_number": "string","issue_date": "dd-mm-yyyy","issue_time": "string"},
  "supplier_details": {"name": "string","vat_id": "string","address": "string"},
  "client_details": {"name": "string","account_number": "string","type": "string","address": "string","vat_id": "string"},
  "products": [{"product_name": "string","alt_name": "string","quantity": 0,"unit_of_measure": "string",
  "unit_price": 0.0,"total_before_discount": 0.0,"discount_amount": 0.0,"total_after_discount": 0.0,
  "vat_percentage": 0.0,"vat_amount": 0.0,"final_total_per_product": 0.0,"category": "string"}],
  "invoice_summary": {"total_amount_before_vat": 0.0,"total_discount_amount": 0.0,"net_amount_before_vat": 0.0,
  "total_vat_amount": 0.0,"vat_percentage_summary": 0.0,"final_invoice_total": 0.0,"amount_in_words_ar": "string"}
}"""
    response = model.generate_content([prompt, img])
    return json.loads(clean_response(response.text))

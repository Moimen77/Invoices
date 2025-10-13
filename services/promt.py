def invoice_prompt():
    return """حلل لي فاتورة المرفقة واستخرج كل التفاصيل الممكنة في صيغة JSON بدون أي نصوص إضافية.
📌 مهم:
- لو المنتج بلغتين (عربي + إنجليزي) خُذ العربي كـ "product_name" والإنجليزي كـ "alt_name".
- الأولوية للعربي في المطابقة والحفظ.
- بالنسبة للمنتجات: حدد category (فئة المنتج) حسب نوعه.
- استخدم نفس الهيكل التالي بدقة:
{
  "invoice_details": {"invoice_number": "string","issue_date": "string","issue_time": "string"},
  "supplier_details": {"name": "string","vat_id": "string","address": "string"},
  "client_details": {"name": "string","account_number": "string","type": "string","address": "string","vat_id": "string"},
  "product_details": [{"product_name": "string","alt_name": "string","quantity": 0,"unit_of_measure": "string",
  "unit_price": 0.0,"total_before_discount": 0.0,"discount_amount": 0.0,"total_after_discount": 0.0,
  "vat_percentage": 0.0,"vat_amount": 0.0,"final_total_per_product": 0.0,"category": "string"}],
  "invoice_summary": {"total_amount_before_vat": 0.0,"total_discount_amount": 0.0,"net_amount_before_vat": 0.0,
  "total_vat_amount": 0.0,"vat_percentage_summary": 0.0,"final_invoice_total": 0.0,"amount_in_words_ar": "string"}
}"""
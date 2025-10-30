document.addEventListener("DOMContentLoaded", async () => {
    const API_BASE = "http://127.0.0.1:8000"; // 🔗 غيّرها لو السيرفر مختلف
    const clientFilter = document.getElementById("client_filter");
    const dateFrom = document.getElementById("date_from");
    const dateTo = document.getElementById("date_to");
    const tableBody = document.getElementById("invoice_table_body");
    const filterBtn = document.getElementById("filter_btn");
    const downloadBtn = document.getElementById("download_excel");

    // 🟢 تحميل العملاء
    async function loadClients() {
        try {
            const res = await fetch(`${API_BASE}/clients/get_clients`);
            const data = await res.json();
            clientFilter.innerHTML = `<option value="">الكل</option>` +
                data.data.map(c => `<option value="${c.client_id}">${c.client_name}</option>`).join("");
        } catch (err) {
            console.error(err);
            clientFilter.innerHTML = `<option>❌ خطأ أثناء تحميل العملاء</option>`;
        }
    }

    // 🟣 تحميل الفواتير
    async function loadInvoices() {
        tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center;">⏳ جاري تحميل البيانات...</td></tr>`;

        const params = new URLSearchParams();
        if (clientFilter.value) params.append("client_id", clientFilter.value);
        if (dateFrom.value) params.append("date_from", dateFrom.value);
        if (dateTo.value) params.append("date_to", dateTo.value);

        try {
            const res = await fetch(`${API_BASE}/invoices/filter?${params}`);
            const data = await res.json();

            if (data.status !== "success" || !data.data?.length) {
                tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center;">⚠️ لا توجد فواتير مطابقة</td></tr>`;
                return;
            }

            // ✅ عرض بيانات الفواتير
            tableBody.innerHTML = data.data.map((inv, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${inv.supplier_name || "-"}</td>
                    <td>${inv.invoice_number || "-"}</td>
                    <td>${inv.issue_date || "-"}</td>
                    <td>${inv.total_amount?.toFixed(2) || 0}</td>
                    <td><a href="${inv.image_url}" target="_blank">🖼️ عرض الصورة</a></td>
                    <td>
                        <button class="btn btn-info" onclick='showItems(${JSON.stringify(JSON.stringify(inv.items))}, ${inv.id})'>👁️ الأصناف</button>
                    </td>
                    <td>
                        <button class="btn btn-warning" onclick="editInvoice(${inv.id})">✏️ تعديل</button>
                        <button class="btn btn-danger" onclick="deleteInvoice(${inv.id})">🗑️ حذف</button>
                    </td>
                </tr>
            `).join("");

        } catch (err) {
            console.error("Error loading invoices:", err);
            tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center;">❌ حدث خطأ أثناء تحميل الفواتير</td></tr>`;
        }
    }

    // 🧾 عرض الأصناف داخل نافذة منبثقة مع زر تعديل كل صنف
    window.showItems = function (itemsJson, invoiceId) {
        const items = JSON.parse(itemsJson);
        const popup = window.open("", "_blank", "width=900,height=700,scrollbars=yes");
        let html = `
            <html lang="ar" dir="rtl">
            <head>
                <title>تفاصيل الأصناف</title>
                <style>
                    body { font-family: 'Cairo', sans-serif; background: #f5f5f5; padding: 20px; }
                    table { width: 100%; border-collapse: collapse; background: white; }
                    th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
                    th { background: #007bff; color: white; }
                    button { padding: 5px 10px; border: none; border-radius: 5px; cursor: pointer; }
                    .edit-btn { background-color: #ffc107; color: black; }
                </style>
            </head>
            <body>
                <h2>🧾 الأصناف في الفاتورة رقم ${invoiceId}</h2>
                <table>
                    <thead>
                        <tr>
                            <th>اسم المنتج</th>
                            <th>المخزون المطابق</th>
                            <th>الكمية</th>
                            <th>الوحدة</th>
                            <th>سعر الوحدة</th>
                            <th>الضريبة</th>
                            <th>الإجمالي</th>
                            <th>التصنيف</th>
                            <th>تعديل</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map(it => `
                            <tr>
                                <td>${it.product_name || "-"}</td>
                                <td>${it.matched_inventory || "❌ لا يوجد"}</td>
                                <td>${it.quantity || "-"}</td>
                                <td>${it.unit_of_measure || "-"}</td>
                                <td>${it.unit_price || "-"}</td>
                                <td>${it.vat_amount || "-"}</td>
                                <td>${it.final_total_per_product || "-"}</td>
                                <td>${it.category || "-"}</td>
                                <td>
                                    <button class="edit-btn" onclick="window.open('edit_item.html?invoice_id=${invoiceId}&item_id=${it.id}', '_blank')">✏️</button>
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </body></html>
        `;

        popup.document.write(html);
    };

    // ✏️ تعديل الفاتورة (ينقلك لصفحة التعديل)
    window.editInvoice = function (id) {
        window.location.href = `edit_invoice.html?id=${id}`;
    };

    // 🗑️ حذف الفاتورة
    window.deleteInvoice = async function (id) {
        if (!confirm("هل أنت متأكد من حذف هذه الفاتورة؟")) return;
        try {
            const res = await fetch(`${API_BASE}/invoices/delete/${id}`, { method: "DELETE" });
            const data = await res.json();
            if (data.status === "success") {
                alert("✅ تم حذف الفاتورة بنجاح");
                await loadInvoices();
            } else {
                alert("❌ فشل الحذف: " + (data.message || "حدث خطأ"));
            }
        } catch (err) {
            console.error("Error deleting invoice:", err);
            alert("⚠️ حدث خطأ أثناء الحذف");
        }
    };

    // 🔘 الأحداث
    filterBtn.addEventListener("click", loadInvoices);
    downloadBtn.addEventListener("click", async () => {
        const params = new URLSearchParams();
        if (clientFilter.value) params.append("client_id", clientFilter.value);
        if (dateFrom.value) params.append("date_from", dateFrom.value);
        if (dateTo.value) params.append("date_to", dateTo.value);
        window.open(`${API_BASE}/invoices/export/excel?${params.toString()}`, "_blank");
    });

    // 🚀 أول تحميل
    await loadClients();
    await loadInvoices();
});

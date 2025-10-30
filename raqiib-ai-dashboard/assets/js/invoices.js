const clientSelect = document.getElementById("client_select");
const results = document.getElementById("results");
const progressContainer = document.getElementById("progress_container");
const progressBar = document.getElementById("progress_bar");
const progressText = document.getElementById("progress_text");

let socket = null;
let totalFiles = 0;
let processedFiles = 0;
let uploadProgress = 0;
let analysisProgress = 0;

// 🟢 تحميل قائمة العملاء
async function loadClients() {
    clientSelect.innerHTML = "<option>⏳ جاري تحميل العملاء...</option>";
    try {
        const res = await fetch(`${API_BASE}/clients/get_clients`);
        const data = await res.json();
        clientSelect.innerHTML = "<option disabled selected>اختر العميل</option>";
        data.data.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.client_id;
            opt.textContent = c.client_name;
            clientSelect.appendChild(opt);
        });
    } catch (err) {
        clientSelect.innerHTML = "<option>❌ خطأ أثناء تحميل العملاء</option>";
    }
}

loadClients();

// 🟡 WebSocket لتتبع تقدم التحليل
clientSelect.addEventListener("change", () => {
    const clientId = clientSelect.value;
    if (!clientId) return;

    if (socket) socket.close();

    socket = new WebSocket(`ws://localhost:8000/upload/ws/progress/${clientId}`);

    socket.onopen = () => {
        results.innerHTML = `<div class="alert alert-info">📡 تم الاتصال بالسيرفر...</div>`;
    };

    socket.onmessage = (event) => {
        const text = event.data;
        const msg = document.createElement("p");
        msg.textContent = text;
        msg.className = "log-line";
        results.appendChild(msg);
        results.scrollTop = results.scrollHeight;

        // بدء المعالجة
        const startMatch = text.match(/بدء رفع (\d+) ملف/);
        if (startMatch) {
            totalFiles = parseInt(startMatch[1]);
            processedFiles = 0;
        }

        // تحديث النسبة أثناء التحليل
        if (text.includes("تم حفظ الصورة") || text.includes("تمت المعالجة")) {
            processedFiles++;
            if (totalFiles > 0) {
                const localProgress = Math.round((processedFiles / totalFiles) * 70); // التحليل = 70%
                analysisProgress = localProgress;
                updateProgressBar();
            }
        }

        // انتهاء التحليل
        if (text.includes("تم إنهاء المعالجة")) {
            uploadProgress = 30;
            updateProgressBar();
            progressText.textContent = " تم رفع الملفات، تم التحليل...";
            progressBar.style.background = "linear-gradient(90deg, #4caf50, #81c784)";
        }
    };

    socket.onclose = () => {
        const msg = document.createElement("p");
        msg.textContent = "🚫 تم قطع الاتصال بالسيرفر";
        msg.style.color = "red";
        results.appendChild(msg);
    };
});

// 🧮 دالة تحديث شريط التقدم الكلي
function updateProgressBar() {
    const totalPercent = Math.min(uploadProgress + analysisProgress, 100);
    progressBar.style.width = totalPercent + "%";
    progressText.textContent = `${totalPercent}%`;
}

// 🟣 رفع الملفات ومتابعة التقدم
document.getElementById("upload_btn").addEventListener("click", async (e) => {
    e.preventDefault();

    const client = clientSelect.value;
    const files = document.getElementById("invoice_files").files;

    if (!client || files.length === 0) {
        alert("يرجى اختيار عميل وملفات");
        return;
    }

    const formData = new FormData();
    formData.append("client_id", client);
    for (const f of files) formData.append("files", f);

    // 🔄 تهيئة الشريط
    progressContainer.style.display = "block";
    progressBar.style.width = "0%";
    progressText.textContent = "0%";
    progressBar.style.background = "linear-gradient(90deg, #2196f3, #64b5f6)";
    uploadProgress = 0;
    analysisProgress = 0;

    const xhr = new XMLHttpRequest();

    // 🟦 تحديث أثناء رفع الملفات (0 → 60%)
    xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
            uploadProgress = Math.round((event.loaded / event.total) * 30);
            updateProgressBar();
        }
    });

    xhr.addEventListener("loadstart", () => {
        progressText.textContent = "🚀 بدء رفع الملفات...";
    });

    xhr.addEventListener("loadend", () => {
        uploadProgress = 60;
        updateProgressBar();
        progressText.textContent = "📦 تم رفع الملفات، جاري التحليل...";
    });

    xhr.addEventListener("error", () => {
        progressText.textContent = "❌ فشل الرفع";
        progressBar.style.background = "#f44336";
    });

    xhr.open("POST", `${API_BASE}/upload/invoices/`);
    xhr.send(formData);
});
س
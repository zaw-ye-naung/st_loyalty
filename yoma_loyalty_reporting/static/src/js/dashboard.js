/** @odoo-module **/

function loadDashboard() {

    const startEl = document.getElementById("start_date");
    const endEl = document.getElementById("end_date");

    if (!startEl || !endEl) {
        console.log("[Dashboard] inputs not ready");
        return;
    }

    const start = startEl.value || "";
    const end = endEl.value || "";

    console.log("[Dashboard] loading KPI with", start, end);

    // ================= KPI =================
    fetch(`/loyalty/dashboard/kpi?start_date=${start}&end_date=${end}`)
        .then(r => r.json())
        .then(data => {

            console.log("[KPI]", data);

            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.innerText = val ?? 0;
            };

            set("kpi_earned", data.earned);
            set("kpi_redeemed", data.redeemed);
            set("kpi_expired", data.expired);
            set("kpi_balance", data.balance);

            const dbg = document.getElementById("debug_kpi");
            if (dbg) dbg.innerText = JSON.stringify(data, null, 2);
        })
        .catch(err => console.error("[KPI ERROR]", err));

    // ================= TOP CUSTOMERS =================
    fetch('/loyalty/dashboard/top_customers')
        .then(r => r.json())
        .then(data => {

            console.log("[TOP CUSTOMERS]", data);

            const table = document.getElementById("top_customers");
            if (!table) return;

            table.innerHTML = (data || []).map(c => `
                <tr>
                    <td>${c.customer || ""}</td>
                    <td>${c.earned || 0}</td>
                    <td>${c.redeemed || 0}</td>
                    <td>${c.expired || 0}</td>
                    <td>${c.balance || 0}</td>
                </tr>
            `).join("");

            const dbg = document.getElementById("debug_customers");
            if (dbg) dbg.innerText = JSON.stringify(data, null, 2);
        })
        .catch(err => console.error("[TOP ERROR]", err));

    // ================= MONTHLY =================
    fetch('/loyalty/dashboard/monthly')
        .then(r => r.json())
        .then(data => {

            console.log("[MONTHLY]", data);

            const dbg = document.getElementById("debug_monthly");
            if (dbg) dbg.innerText = JSON.stringify(data, null, 2);
        })
        .catch(err => console.error("[MONTHLY ERROR]", err));
}


/**
 * SAFE ODOO INIT
 */
function initDashboard() {

    if (!window.location.pathname.includes("/loyalty/dashboard")) {
        return;
    }

    const btn = document.getElementById("apply_filter");

    if (!btn) {
        console.log("[Dashboard] waiting DOM...");
        setTimeout(initDashboard, 300);
        return;
    }

    console.log("[Dashboard] Dashboard ready");

    btn.onclick = () => {
        console.log("[Dashboard] Apply clicked");
        loadDashboard();
    };

    loadDashboard();
}

// IMPORTANT: delay init for Odoo asset rendering
setTimeout(initDashboard, 500);
let ALL_PAYMENTS = [];

$(document).ready(function () {
  initFilters();
  loadPaymentHistory();

  $("#searchInput").on("input", function () {
    renderTable($(this).val());
  });
});

function initFilters() {
  const now = new Date();

  for (let m = 1; m <= 12; m++) {
    $("#filterMonth").append(`<option value="${m}">${m}</option>`);
  }

  for (let y = now.getFullYear()-5; y <= now.getFullYear() + 5; y++) {
    $("#filterYear").append(`<option value="${y}">${y}</option>`);
  }

  $("#filterMonth").val(now.getMonth() + 1);
  $("#filterYear").val(now.getFullYear());
}




function loadPaymentHistory() {
  apiGet("/payment-history/", {
    branch_id: CURRENT_BRANCH,
    year: $("#filterYear").val() || new Date().getFullYear(),
    month: $("#filterMonth").val() || (new Date().getMonth() + 1)
  }).done(function (rows) {
    ALL_PAYMENTS = rows || [];
    renderTable("");
  });
}

function renderTable(query) {
  const q = (query || "").toLowerCase();
  const $list = $("#historyTable");
  $list.empty();

  const filtered = ALL_PAYMENTS.filter(p =>
    !q ||
    (p.customer_name || "").toLowerCase().includes(q) ||
    (p.passport_id || "").toLowerCase().includes(q)
  );

  if (!filtered.length) {
    $list.html(`
      <div class="text-center text-tgHint py-10">
        ${t("no_payments_for_this_month")}
      </div>
    `);
    return;
  }

  filtered.forEach(p => {
      const methodColor =
      p.paid_by === "card" ? "text-blue-500" :
      p.paid_by === "cash" ? "text-green-500" :
      "text-gray-500";
    $list.append(`
      <div class="bg-card rounded-2xl shadow p-4 flex justify-between gap-3">

        <!-- LEFT -->
        <div class="space-y-1">
          <div class="text-xs text-tgHint">
            ${formatDateTime(p.paid_at)}
          </div>

          <div class="font-semibold text-gray-900">
            ${p.customer_name || "—"}
          </div>

          <div class="text-sm text-gray-600">
            ${p.passport_id || "—"}
          </div>

          <div class="text-sm text-gray-600">
            🏠 ${t("room")} ${p.room_number} · 🛏 ${t("bed")} ${p.bed_number}
          </div>
        </div>

        <!-- RIGHT -->
        <div class="text-right flex flex-col justify-between">
          <div class="text-lg font-bold text-green-600">
            ${formatNumber(p.paid_amount)}
          </div>

          <div class="text-xs ${methodColor}">
            ${p.paid_by || t("cash")}
          </div>

        </div>

      </div>
    `);
  });
}


function formatNumber(x) {
  if (x === null || x === undefined) return "0";

  const n = Number(x);
  if (isNaN(n)) return "0";

  return n.toLocaleString("ru-RU"); // 600 000
}

/* ===== SAFE DATE FORMAT (DESKTOP STYLE) ===== */
function formatDateTime(value) {
  if (!value) return "—";

  const d = new Date(value);
  if (isNaN(d)) return "—";

  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}



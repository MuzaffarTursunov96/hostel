let ALL_PAYMENTS = [];
let CURRENT_BRANCH = null;
let PAYMENT_ROOMS = [];

$(document).ready(function () {
  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }

  initFilters();
  loadRoomsForPaymentFilter();
  loadPaymentHistory();

  $("#searchInput").on("input", function () {
    renderTable($(this).val());
  });

  $("#filterRoom").on("change", function () {
    renderTable($("#searchInput").val());
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

function loadRoomsForPaymentFilter() {
  apiGet("/rooms", { branch_id: CURRENT_BRANCH }).done(function (rows) {
    PAYMENT_ROOMS = rows || [];
    const $sel = $("#filterRoom");
    const lang = (window.CURRENT_LANG || "ru").toLowerCase();
    const allLabel = lang.startsWith("uz") ? "Barcha xonalar" : "Все комнаты";

    $sel.empty();
    $sel.append(`<option value="">${allLabel}</option>`);

    PAYMENT_ROOMS.forEach(r => {
      const label = r.room_name || r.number || (`#${r.id}`);
      $sel.append(`<option value="${r.id}">${label}</option>`);
    });
  });
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
  const selectedRoomId = ($("#filterRoom").val() || "").trim();
  const $list = $("#historyTable");
  $list.empty();

  const filtered = ALL_PAYMENTS.filter(p =>
    (!q ||
      (p.customer_name || "").toLowerCase().includes(q) ||
      (p.passport_id || "").toLowerCase().includes(q)) &&
    (!selectedRoomId || String(p.room_id) === selectedRoomId)
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

      const secondGuestName =
          Array.isArray(p.second_guests) && p.second_guests.length > 0
            ? p.second_guests[0].name
            : null;

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

          ${
            secondGuestName
              ? `<div class="text-xs text-purple-600">
                  👥 ${secondGuestName}
                </div>`
              : ``
          }

          <div class="text-sm text-gray-600">
            ${p.passport_id || "—"}
          </div>

          <div class="text-sm text-gray-600">
            🏠 ${p.room_name || p.room_number} · 🛏 ${t("bed")} ${p.bed_number}

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



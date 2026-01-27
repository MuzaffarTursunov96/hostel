let ALL_DEBTS = [];
let searchTimer = null;

$(document).ready(function () {
  setDefaultRange();
  loadDebts();

  $("#searchInput").on("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      renderDebts($(this).val());
    }, 300);
  });
});

function setDefaultRange() {
  const today = new Date();
  const from = new Date(today.getFullYear(), 0, 1);

  $("#fromDate").val(from.toISOString().split("T")[0]);
  $("#toDate").val(
    new Date(today.setMonth(today.getMonth() + 3))
      .toISOString()
      .split("T")[0]
  );
}

function loadDebts() {
  apiGet("/debts/", {
    branch_id: CURRENT_BRANCH,
    from_date: $("#fromDate").val(),
    to_date: $("#toDate").val()
  }).done(function (rows) {
    ALL_DEBTS = rows || [];
    renderDebts($("#searchInput").val());
  });
}

function renderDebts(query = "") {
  const q = query.toLowerCase();
  const $list = $("#debtsTable");
  $list.empty();

  if (!ALL_DEBTS.length) {
    $list.append(`
      <div class="text-center text-tgHint py-6">
        ${t("no_unpaid_debts_in_selected_range")}
      </div>
    `);
    return;
  }

  ALL_DEBTS
    .filter(d =>
      !q ||
      d.customer_name.toLowerCase().includes(q) ||
      d.passport_id.toLowerCase().includes(q)
    )
    .forEach(d => {
      $list.append(`
        <div class="p-4 flex flex-col gap-2">

          <div class="flex justify-between items-start">
            <div>
              <div class="font-semibold">${d.customer_name}</div>
              <div class="text-sm text-gray-500">${d.passport_id}</div>
              <div class="text-sm text-gray-500">
                🏠 ${t("room")} ${d.room_number} · 🛏 ${t("bed")} ${d.bed_number}
              </div>
              <div class="text-xs text-tgHint">
                ${fmtDate(d.checkin_date)} → ${fmtDate(d.checkout_date)}
              </div>
            </div>

            <div class="text-right">
              <div class="font-bold text-red-600">
                ${fmtMoney(d.remaining_amount)}
              </div>
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <input
              type="number"
              class="flex-1 px-3 py-2 rounded-lg border"
              min="1"
              placeholder="${t("pay_amount")}"
              id="pay-${d.id}"
            >
            <button
              class="px-4 py-2 rounded-lg bg-green-500 text-white"
              onclick="payDebt(${d.id})">
              ${t("pay")}
            </button>
          </div>

        </div>
      `);
    });
}


function payDebt(bookingId) {
  const input = $(`#pay-${bookingId}`);
  const amount = parseFloat(input.val());

  if (!amount || amount <= 0) {
    alert("Enter valid amount");
    return;
  }

  apiPost("/debts/pay", {
    branch_id: CURRENT_BRANCH,
    booking_id: bookingId,
    amount: amount,
    paid_by: "admin"
  })
  .done(function () {
    loadDebts();
  })
  .fail(err => {
    alert(err.responseJSON?.detail || t("payment_failed"));
  });
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString("en-GB");
}

function fmtMoney(x) {
  return Number(x).toLocaleString("en-GB");
}

$(document).ready(function () {
  var CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }
  initFilters();
  loadFinance();
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

function loadFinance() {
  const month = $("#filterMonth").val();
  const year = $("#filterYear").val();

  

  apiGet("/payments/monthly-finance", {
    branch_id: CURRENT_BRANCH,
    month,
    year
  }).done(function (data) {


    const income   = Number(data.income   || 0);
    const expenses = Number(data.expenses || 0);
    const debt     = Number(data.debt     || 0);
    const refunds  = Number(data.refunds  || 0);

    const profit = income - expenses - refunds;

    $("#sumIncome").text(formatNumber(income));
    $("#sumExpenses").text(formatNumber(expenses));
    $("#sumDebt").text(formatNumber(debt));
    $("#sumRefunds").text(formatNumber(refunds));
    $("#sumProfit").text(formatNumber(profit));
  });
}



function addExpense() {
  const title = $("#expenseTitle").val().trim();
  const amount = parseFloat($("#expenseAmount").val());

  if (!title || !amount || amount <= 0) {
    alert(t("invalid_data"));
    return;
  }

  apiPost("/payments/expense", {
    branch_id: CURRENT_BRANCH,
    title,
    category: "other",
    amount,
    expense_date: new Date().toISOString().split("T")[0]
  }).done(function () {
    $("#expenseTitle").val("");
    $("#expenseAmount").val("");
    loadFinance();
  });
}

function openPaymentHistory() {
  window.location.href = "/payment-history";
}



function formatNumber(x) {
  if (x === null || x === undefined) return "0";
  return Number(x).toLocaleString("ru-RU");
}

function openDebtPage() {
  window.location.href = "/debts";
}

function openCustomersPage() {
  window.location.href = "/customers";
}






function openRefundHistory() {
  initRefundFilters();
  $("#refundHistoryModal").removeClass("hidden");
  loadRefundHistory();
}

function closeRefundHistory() {
  $("#refundHistoryModal").addClass("hidden");
}

function initRefundFilters() {
  const now = new Date();

  const monthSel = $("#refundMonth");
  const yearSel = $("#refundYear");

  monthSel.empty();
  yearSel.empty();

  for (let m = 1; m <= 12; m++) {
    monthSel.append(`<option value="${m}">${m}</option>`);
  }

  for (let y = now.getFullYear() - 5; y <= now.getFullYear() + 5; y++) {
    yearSel.append(`<option value="${y}">${y}</option>`);
  }

  monthSel.val(now.getMonth() + 1);
  yearSel.val(now.getFullYear());
}

function loadRefundHistory() {
  const month = parseInt($("#refundMonth").val());
  const year = parseInt($("#refundYear").val());

  // 🔥 convert to date range
  const fromDate = new Date(year, month - 1, 1);
  const toDate = new Date(year, month, 0); // last day of month

  const from = fromDate.toISOString().slice(0, 10);
  const to = toDate.toISOString().slice(0, 10);

  apiGet("/refunds/list", {
    branch_id: CURRENT_BRANCH,
    from_date: from,
    to_date: to
  }).done(renderRefundHistory);
}


function renderRefundHistory(rows) {
  const box = $("#refundHistoryTable");
  box.empty();

  if (!rows.length) {
    box.append(`
      <div class="text-center text-tgHint py-6">
        ${t("no_refunds_in_selected_range")}
      </div>
    `);
    return;
  }

  rows.forEach(r => {
    box.append(`
      <div class="border rounded-xl p-3">
        <div class="font-semibold">
          ${formatNumber(r.refund_amount)}
        </div>
        <div class="text-sm text-tgHint">
          ${r.refund_reason || "-"}
        </div>
        <div class="text-xs text-tgHint">
          ${formatDateTime(r.created_at)}
        </div>
      </div>
    `);
  });
}


function formatDateTime(value) {
  if (!value) return "-";

  const d = new Date(value.replace(" ", "T"));

  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

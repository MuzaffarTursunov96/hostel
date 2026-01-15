$(document).ready(function () {
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

    $("#sumIncome").text(formatNumber(data.income || 0));
    $("#sumExpenses").text(formatNumber(data.expenses || 0));
    $("#sumDebt").text(formatNumber(data.debt || 0));
    $("#sumProfit").text(
      formatNumber((data.income || 0) - (data.expenses || 0))
    );

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

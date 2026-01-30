


function initExpenseFilters() {
  const now = new Date();

  const months = [
    "Jan","Feb","Mar","Apr","May","Jun",
    "Jul","Aug","Sep","Oct","Nov","Dec"
  ];

  months.forEach((name, i) => {
    $("#expenseFilterMonth").append(
      `<option value="${i + 1}">${name}</option>`
    );
  });

  for (let y = now.getFullYear() - 5; y <= now.getFullYear() + 5; y++) {
    $("#expenseFilterYear").append(
      `<option value="${y}">${y}</option>`
    );
  }

  $("#expenseFilterMonth").val(now.getMonth() + 1);
  $("#expenseFilterYear").val(now.getFullYear());
}


$(document).on("change", "#expenseFilterMonth, #expenseFilterYear", function () {
  loadExpenseHistory();
});


let ALL_EXPENSES = [];

function openExpenseHistory() {
  $("#expenseHistoryModal").removeClass("hidden");

  initExpenseFilters();
  loadExpenseHistory();
}


function closeExpenseHistory() {
  $("#expenseHistoryModal").addClass("hidden");
}



function loadExpenseHistory() {
  apiGet("/payments/expenses", {
    branch_id: CURRENT_BRANCH,
    year: $("#expenseFilterYear").val(),
    month: $("#expenseFilterMonth").val()
  }).done(function (rows) {
    ALL_EXPENSES = rows || [];
    renderExpenseTable();
  });
}



function renderExpenseTable() {
  const $list = $("#expenseHistoryTable");
  $list.empty();

  if (!ALL_EXPENSES.length) {
    $list.append(`
      <div class="text-center text-tgHint py-10">
        ${t("no_expenses_for_this_period")}
      </div>
    `);
    return;
  }

  ALL_EXPENSES.forEach(e => {
    $list.append(`
      <div class="bg-gray-50 rounded-xl p-3 flex justify-between items-center">

        <div class="space-y-1">
          <div class="text-xs text-tgHint">
            ${formatDate(e.expense_date)}
          </div>

          <div class="font-medium">
            ${e.title}
          </div>

          <div class="text-sm text-gray-500">
            ${e.category || t("other")}
          </div>
        </div>

        <div class="font-semibold text-red-600">
          ${formatNumber(e.amount)}
        </div>

      </div>
    `);
  });
}


function formatNumber(x) {
  if (x == null) return "0";
  const n = Number(x);
  return isNaN(n) ? "0" : n.toLocaleString("ru-RU");
}

function formatDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt)) return "—";
  return dt.toLocaleDateString("en-GB");
}



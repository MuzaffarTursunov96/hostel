(function () {
  const lang = (window.CURRENT_LANG || "ru").toLowerCase();
  const isUz = lang.startsWith("uz");
  const tr = (ru, uz) => (isUz ? uz : ru);
  const fmt = (n) => {
    const x = Number(n || 0);
    return new Intl.NumberFormat(isUz ? "uz-UZ" : "ru-RU", { maximumFractionDigits: 0 }).format(x);
  };

  const now = new Date();
  const $scope = $("#arScope");
  const $year = $("#arYear");
  const $month = $("#arMonth");
  const $rows = $("#arRows");
  const $totals = $("#arTotals");

  $("#arTitle").text(tr("Отчеты по филиалам", "Filiallar hisobotlari"));
  $("#arListTitle").text(tr("Список филиалов", "Filiallar ro'yxati"));
  $("#arLoad").text(tr("Загрузить", "Yuklash"));
  $scope.find("option[value='month']").text(tr("Месяц", "Oy"));
  $scope.find("option[value='year']").text(tr("Год", "Yil"));
  $scope.find("option[value='total']").text(tr("Общий", "Umumiy"));

  $year.val(now.getFullYear());
  $month.val(now.getMonth() + 1);

  function updateInputs() {
    const s = $scope.val();
    $year.prop("disabled", s === "total");
    $month.prop("disabled", s !== "month");
  }

  function renderTotals(t) {
    const items = [
      [tr("Доход", "Daromad"), t.income],
      [tr("Расходы", "Xarajatlar"), t.expenses],
      [tr("Возвраты", "Qaytarishlar"), t.refunds],
      [tr("Долг", "Qarz"), t.debt],
      [tr("Прибыль", "Foyda"), t.profit],
    ];
    $totals.empty();
    items.forEach(([label, value]) => {
      $totals.append(`
        <div class="bg-card rounded-xl shadow p-3">
          <div class="text-xs text-gray-500">${label}</div>
          <div class="text-lg font-bold mt-1">${fmt(value)}</div>
        </div>
      `);
    });
  }

  function renderRows(rows) {
    $rows.empty();
    if (!rows.length) {
      $rows.append(`<div class="p-4 text-gray-500">${tr("Нет данных", "Ma'lumot yo'q")}</div>`);
      return;
    }
    rows.forEach((r) => {
      $rows.append(`
        <div class="p-4 space-y-1">
          <div class="font-semibold">${r.branch_id} - ${r.branch_name || ""}</div>
          <div class="text-sm text-gray-700">${tr("Доход", "Daromad")}: <b>${fmt(r.income)}</b></div>
          <div class="text-sm text-gray-700">${tr("Расходы", "Xarajatlar")}: <b>${fmt(r.expenses)}</b></div>
          <div class="text-sm text-gray-700">${tr("Возвраты", "Qaytarishlar")}: <b>${fmt(r.refunds)}</b></div>
          <div class="text-sm text-gray-700">${tr("Долг", "Qarz")}: <b>${fmt(r.debt)}</b></div>
          <div class="text-sm text-blue-700">${tr("Прибыль", "Foyda")}: <b>${fmt(r.profit)}</b></div>
        </div>
      `);
    });
  }

  function loadReport() {
    const scope = $scope.val();
    const query = { scope };
    if (scope !== "total") query.year = String($year.val() || now.getFullYear());
    if (scope === "month") query.month = String($month.val() || now.getMonth() + 1);

    apiGet("/admin-reports/finance", query).done((data) => {
      renderTotals(data.totals || {});
      renderRows(data.branches || []);
    });
  }

  $scope.on("change", () => {
    updateInputs();
    loadReport();
  });
  $("#arLoad").on("click", loadReport);

  updateInputs();
  loadReport();
})();

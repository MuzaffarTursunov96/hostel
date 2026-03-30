(function () {
  const lang = (window.CURRENT_LANG || "ru").toLowerCase();
  const isUz = lang.startsWith("uz");
  const tr = (ru, uz) => (isUz ? uz : ru);
  const $rows = $("#fbRows");

  function esc(v) {
    return String(v ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function load() {
    const branchId = ($("#fbBranchId").val() || "").trim();
    const status = ($("#fbStatus").val() || "").trim().toLowerCase();
    const q = {};
    if (branchId) q.branch_id = branchId;
    q.limit = "300";

    apiGet("/feedback/admin", q).done((items) => {
      const list = Array.isArray(items) ? items : [];
      const filtered = status ? list.filter((x) => String(x.status || "new").toLowerCase() === status) : list;
      $rows.empty();
      if (!filtered.length) {
        $rows.append(`<div class="text-gray-500">${tr("Нет отзывов", "Fikrlar yo'q")}</div>`);
        return;
      }

      filtered.forEach((x) => {
        const st = (x.status || "new").toLowerCase();
        const senti = x.sentiment ? ` • ${esc(x.sentiment)}` : "";
        const who = esc(x.user_name || x.contact || x.telegram_id || "-");
        const note = esc(x.admin_note || "");
        const reportType = esc(x.report_type || "general");
        const roomLabel = esc(x.room_label || "");
        const imagePath = esc(x.image_path || "");

        $rows.append(`
          <div class="bg-card rounded-2xl shadow p-4 space-y-2">
            <div class="font-semibold">${esc(x.branch_id)} - ${esc(x.branch_name || "")}</div>
            <div class="text-sm text-gray-600">${tr("Клиент", "Mijoz")}: ${who}</div>
            <div class="text-sm text-gray-600">${tr("Статус", "Holat")}: <b>${esc(st)}</b>${senti}</div>
            <div class="text-xs text-gray-500">${tr("Тип", "Turi")}: <b>${reportType}</b>${roomLabel ? ` • ${tr("Комната", "Xona")}: <b>${roomLabel}</b>` : ""}</div>
            <div class="text-sm whitespace-pre-line">${esc(x.message || "")}</div>
            ${imagePath ? `<a href="${imagePath}" target="_blank" rel="noopener"><img src="${imagePath}" alt="report photo" class="w-36 h-24 object-cover rounded-lg border"></a>` : ""}
            ${note ? `<div class="text-xs text-gray-500">${tr("Заметка", "Izoh")}: ${note}</div>` : ""}
            <div class="flex gap-2 pt-1">
              <button class="fbMark px-3 py-1 rounded-lg border" data-id="${x.id}" data-status="read">${tr("Прочитано", "O'qildi")}</button>
              <button class="fbMark px-3 py-1 rounded-lg bg-green-600 text-white" data-id="${x.id}" data-status="resolved">${tr("Решено", "Hal qilindi")}</button>
            </div>
          </div>
        `);
      });
    });
  }

  $(document).on("click", ".fbMark", function () {
    const id = $(this).data("id");
    const status = $(this).data("status");
    apiPut(`/feedback/admin/${id}`, { status: status, is_read: true }).done(load);
  });

  $("#fbLoad").on("click", load);
  load();
})();


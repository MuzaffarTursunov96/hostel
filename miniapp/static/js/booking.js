let CURRENT_ROOM_ID = null;
let SELECTED_BED_ID = null;
let CURRENT_BRANCH = null;



$(document).ready(function () {
  const today = new Date().toISOString().split("T")[0];

  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }

  $("#checkin").val(today);
  $("#checkout").val(today);

  loadRooms();
  document.addEventListener("DOMContentLoaded", startWebSocket);

  $("#checkin, #checkout").on("change", loadAvailableBeds);
  $("#total, #paid").on("input", updateRemaining);
});

/* ---------- ROOMS ---------- */
function loadRooms() {
  apiGet("/booking/rooms", { branch_id: CURRENT_BRANCH })
    .done(function (rooms) {
      const $room = $("#roomSelect");
      $room.empty();
      rooms.forEach(r => {
        $room.append(`<option value="${r.id}">${t("room")} ${r.room_number}</option>`);
      });

      if (rooms.length) {
        CURRENT_ROOM_ID = rooms[0].id;
        loadAvailableBeds();
      }
    });

  $("#roomSelect").on("change", function () {

    CURRENT_ROOM_ID = $(this).val();
    loadAvailableBeds();
  });
}

/* ---------- BEDS ---------- */
function loadAvailableBeds() {
  $("#bedsList").empty();
  SELECTED_BED_ID = null;

  if (!CURRENT_ROOM_ID) return;

  const checkin = $("#checkin").val();
  const checkout = $("#checkout").val();

  if (!checkin || !checkout || checkout <= checkin) {
    $("#bedsList").html(`<div class="text-danger">${t("invalid_dates")}</div>`);
    return;
  }

  apiGet("/booking/available-beds", {
    branch_id: CURRENT_BRANCH,
    room_id: CURRENT_ROOM_ID,
    checkin: checkin,
    checkout: checkout
  }).done(function (beds) {

    if (!beds.length) {
      $("#bedsList").html(`<div class="text-muted">${t("no_free_beds_available")}</div>`);
      return;
    }

    beds.forEach(b => {
      const btn = $(`
          <button
            class="bed-btn px-4 py-2 rounded-xl border
                  bg-gray-100 text-gray-700
                  font-medium transition-all">
            🛏 ${t("bed")} ${b.bed_number}
          </button>
        `);


      btn.on("click", function () {

      // Remove selection from all beds
      $("#bedsList .bed-btn")
        .removeClass("bg-tgButton text-white border-tgButton")
        .addClass("bg-gray-100 text-gray-700 border-gray-300");

      // Select current bed
      $(this)
        .removeClass("bg-gray-100 text-gray-700 border-gray-300")
        .addClass("bg-tgButton text-white border-tgButton");

      SELECTED_BED_ID = b.id;
    });


      $("#bedsList").append(btn);
    });
  });
}

/* ---------- PAYMENT ---------- */
function updateRemaining() {
  const total = parseFloat($("#total").val()) || 0;
  const paid = parseFloat($("#paid").val()) || 0;
  $("#remaining").text(Math.max(total - paid, 0).toFixed(2));
}

/* ---------- CONFIRM ---------- */
function confirmBooking() {
  if (!SELECTED_BED_ID) {
    alert(t("select_a_bed"));
    return;
  }

  

  const name = $("#customerName").val().trim();
  const passport = $("#passport").val().trim();
  const contact = $("#contact").val().trim();
  const total = $("#total").val()
  const pai = $("#paid").val()

  if (!name || !passport || !contact || !total) {
    alert(t("fill_all_required_fields"));
    return;
  }

  const btn = document.getElementById("confirmBookingBtn");

  // 🔒 disable immediately
  btn.disabled = true;
  btn.classList.add("opacity-60", "cursor-not-allowed");

  apiPost("/booking/", {
    branch_id: CURRENT_BRANCH,
    name: name,
    passport_id: passport,
    contact: $("#contact").val(),
    room_id: CURRENT_ROOM_ID,
    bed_id: SELECTED_BED_ID,
    total: parseFloat($("#total").val()),
    paid: pai ? pai : 0,
    checkin: $("#checkin").val(),
    checkout: $("#checkout").val()
  })
  .done(function () {
  alert("✅ " + t("booking_created"));

  SELECTED_BED_ID = null;

  // refresh current page only
  //  loadRooms();
  btn.disabled = false;
  btn.classList.remove("opacity-60", "cursor-not-allowed");
  window.location.href = window.location.href;
});

}


/* ================= BOOKING HISTORY ================= */

function openBookingHistory() {
  $("#bookingHistoryModal").removeClass("hidden");
  setBookingHistoryDefaults();
  loadBookingHistory();
}

function closeBookingHistory() {
  $("#bookingHistoryModal").addClass("hidden");
}

function setBookingHistoryDefaults() {
  const today = new Date();
  const from = new Date();
  from.setMonth(today.getMonth() - 1);

  $("#bhFrom").val(from.toISOString().split("T")[0]);
  $("#bhTo").val(today.toISOString().split("T")[0]);
  $("#bhSearch").val("");
}

function loadBookingHistory() {
  $("#bookingHistoryTable").html(
    `<div class="text-center text-tgHint py-6">${t("loading")}…</div>`
  );

  apiGet("/booking-history/", {
    branch_id: CURRENT_BRANCH,
    from_date: $("#bhFrom").val(),
    to_date: $("#bhTo").val()
  })
  .done(function (rows) {
    renderBookingHistory(rows || []);
  });
}

function renderBookingHistory(rows) {
  const q = ($("#bhSearch").val() || "").toLowerCase();
  const $c = $("#bookingHistoryTable");
  $c.empty();

  if (!rows.length) {
    $c.html(
      `<div class="text-center text-tgHint py-6">${t("no_bookings")}</div>`
    );
    return;
  }

  rows
    .filter(r =>
      !q ||
      (r.customer_name || "").toLowerCase().includes(q) ||
      (r.passport_id || "").toLowerCase().includes(q)
    )
    .forEach(r => {
      $c.append(`
        <div class="py-3 text-sm">
          <div class="font-semibold">
            👤 ${r.customer_name}
          </div>

          <div class="text-xs text-tgHint">
            🪪 ${r.passport_id || "—"}
          </div>

          <div class="mt-1 text-xs text-gray-600">
            🏠 ${t("room")} ${r.room_number} • 🛏 ${t("bed")} ${r.bed_number}
          </div>

          <div class="text-xs text-gray-600">
            📅 ${fmtDate(r.checkin_date)} → ${fmtDate(r.checkout_date)}
          </div>

          <div class="mt-1 font-semibold text-right">
            💰 ${Number(r.total_amount).toFixed(2)}
          </div>
        </div>
      `);
    });
}

function fmtDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-GB");
}

/* live search */
$("#bhSearch").on("input", function () {
  loadBookingHistory();
});

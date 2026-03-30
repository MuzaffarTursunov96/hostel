let CURRENT_ROOM_ID = null;
let SELECTED_BED = null;
let CURRENT_BRANCH = null;
let CURRENT_ROOM_MODE = "bed";
let notifyDateManuallyChanged = false;
let BRANCH_CUSTOMERS = [];
let BOOKING_HISTORY_ROOMS = [];

function addOneDay(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  d.setDate(d.getDate() + 1);
  return d.toISOString().split("T")[0];
}




$(document).ready(function () {
  const today = new Date().toISOString().split("T")[0];

  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }

  loadBranchCustomers();


  $("#checkin").val(today);
  $("#checkout").val(today);
  $("#notifyDate").val(today); 

  loadRooms();
  document.addEventListener("DOMContentLoaded", startWebSocket);

  $("#checkin, #checkout").on("change", loadAvailableBeds);
  $("#isHourlyBooking").on("change", loadAvailableBeds);
  $("#total, #paid").on("input", updateRemaining);

  $("#notifyDate").on("change", function () {
    notifyDateManuallyChanged = true;
  });

  $("#checkout").on("change", function () {
    const checkout = $(this).val();

    if (!checkout) return;

    if (!notifyDateManuallyChanged) {
      $("#notifyDate").val(checkout);
    }
  });

});



$("#customerName").on("input focus", function () {
  const q = $(this).val().toLowerCase().trim();
  const $dd = $("#customerDropdown");
  $dd.empty();

  if (!BRANCH_CUSTOMERS.length) return;

  const matches = BRANCH_CUSTOMERS
    .filter(c =>
      !q ||
      (c.name || "").toLowerCase().includes(q) ||
      (c.passport_id || "").toLowerCase().includes(q)
    )
    .slice(0, 8);

  if (!matches.length) {
    $dd.addClass("hidden");
    return;
  }

  matches.forEach(c => {
    $dd.append(`
      <div class="px-3 py-2 cursor-pointer hover:bg-gray-100"
           onclick="selectCustomer(${c.id})">
        <div class="font-medium">${c.name}</div>
        <div class="text-xs text-gray-500">
          🪪 ${c.passport_id || "—"} · 📞 ${c.contact || "—"}
        </div>
      </div>
    `);
  });

  $dd.removeClass("hidden");
});


function selectCustomer(customerId) {
  const c = BRANCH_CUSTOMERS.find(x => x.id === customerId);
  if (!c) return;

  $("#customerName").val(c.name || "");
  $("#passport").val(c.passport_id || "");
  $("#contact").val(c.contact || "");

  $("#customerDropdown").addClass("hidden");
}


$(document).on("click", function (e) {
  if (!$(e.target).closest("#customerName, #customerDropdown").length) {
    $("#customerDropdown").addClass("hidden");
  }
});


function getBedIcon(bedType) {
  switch (bedType) {
    case "double":
      return "👥";      // double bed
    case "child":
      return "🧸";      // child bed
    case "family":
      return "👨‍👩‍👧"; // family
    case "single":
    default:
      return "👤";      // single / fallback
  }
}

function bookingModeTitle(mode) {
  const isRu = (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  const m = String(mode || "bed").toLowerCase();
  if (m === "full") return isRu ? "Полная комната" : "To'liq xona";
  return isRu ? "По кроватям" : "Kravat bo'yicha";
}

function updateRoomModeBadge(mode) {
  const $badge = $("#roomModeBadge");
  if (!$badge.length) return;
  const m = String(mode || "bed").toLowerCase();
  const titleRu = (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  const label = titleRu ? "Режим брони" : "Bron rejimi";
  const text = `${label}: ${bookingModeTitle(m)}`;
  $badge
    .removeClass("hidden bg-blue-100 text-blue-700 bg-amber-100 text-amber-700")
    .addClass(m === "full" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700")
    .text(text);
}




function loadBranchCustomers() {
  apiGet("/customers/", { branch_id: CURRENT_BRANCH })
    .done(function (rows) {
      BRANCH_CUSTOMERS = rows || [];
    });
}

/* ---------- ROOMS ---------- */
function loadRooms() {
  apiGet("/booking/rooms", { branch_id: CURRENT_BRANCH })
    .done(function (rooms) {
      BOOKING_HISTORY_ROOMS = rooms || [];
      const $room = $("#roomSelect");
      $room.empty();
      rooms.forEach(r => {
        const label = r.room_name || r.room_number;
        $room.append(`<option value="${r.id}">${label} (${bookingModeTitle(r.booking_mode)})</option>`);

        // $room.append(`<option value="${r.id}">${t("room")} ${r.room_number}</option>`);
      });

      if (rooms.length) {
        CURRENT_ROOM_ID = rooms[0].id;
        CURRENT_ROOM_MODE = String(rooms[0].booking_mode || "bed").toLowerCase();
        updateRoomModeBadge(CURRENT_ROOM_MODE);
        loadAvailableBeds();
      } else {
        $("#roomModeBadge").addClass("hidden").text("");
      }

      renderBookingHistoryRoomFilter();
    });

  $("#roomSelect").on("change", function () {

    CURRENT_ROOM_ID = $(this).val();
    const row = (BOOKING_HISTORY_ROOMS || []).find((x) => String(x.id) === String(CURRENT_ROOM_ID));
    CURRENT_ROOM_MODE = String((row && row.booking_mode) || "bed").toLowerCase();
    updateRoomModeBadge(CURRENT_ROOM_MODE);
    loadAvailableBeds();
  });
}

function renderBookingHistoryRoomFilter() {
  const $sel = $("#bhRoomFilter");
  if (!$sel.length) return;

  const lang = (window.CURRENT_LANG || "ru").toLowerCase();
  const allLabel = lang.startsWith("uz") ? "Barcha xonalar" : "Все комнаты";

  $sel.empty();
  $sel.append(`<option value="">${allLabel}</option>`);

  (BOOKING_HISTORY_ROOMS || []).forEach(r => {
    const label = r.room_name || r.room_number || (`#${r.id}`);
    $sel.append(`<option value="${r.id}">${label}</option>`);
  });
}

/* ---------- BEDS ---------- */
function loadAvailableBeds() {
  $("#bedsList").empty();
  SELECTED_BED = null;

  if (!CURRENT_ROOM_ID) return;

  const checkin = $("#checkin").val();
  const checkout = $("#checkout").val();
  const isHourly = $("#isHourlyBooking").is(":checked");

  if (!checkin || !checkout || (!isHourly && checkout <= checkin) || (isHourly && checkout < checkin)) {
    $("#bedsList").html(`<div class="text-danger">${t("invalid_dates")}</div>`);
    return;
  }
  const effectiveCheckout = (isHourly && checkout <= checkin)
    ? addOneDay(checkin)
    : checkout;

  apiGet("/booking/available-beds", {
    branch_id: CURRENT_BRANCH,
    room_id: CURRENT_ROOM_ID,
    checkin: checkin,
    checkout: effectiveCheckout,
    is_hourly: isHourly
  }).done(function (beds) {

    if (!beds.length) {
      const msg = CURRENT_ROOM_MODE === "full"
        ? ((document.documentElement.lang || "").toLowerCase().startsWith("ru")
            ? "Комната (полная бронь) уже занята на выбранный период"
            : "Xona (to'liq bron) tanlangan davrda band")
        : t("no_free_beds_available");
      $("#bedsList").html(`<div class="text-muted">${msg}</div>`);
      return;
    }

    beds.forEach(b => {
      const btn = $(`
          <button
            class="bed-btn px-4 py-2 rounded-xl border
                  bg-gray-100 text-gray-700
                  font-medium transition-all">
            ${getBedIcon(b.bed_type)} ${t("bed")} ${b.bed_number}
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

      SELECTED_BED = b;

      handleBedTypeUI(b);
    });


      $("#bedsList").append(btn);
    });
  });
}



function handleBedTypeUI(bed) {

  if (bed && bed.bed_type === "double") {
    // show checkbox
    $("#secondGuestToggle").removeClass("hidden");
  } else {
    // hide everything for single bed
    $("#secondGuestToggle").addClass("hidden");
    $("#enableSecondGuest").prop("checked", false);
    $("#secondGuestForm").addClass("hidden");
  }
}




$("#enableSecondGuest").on("change", function () {
  if (this.checked) {
    $("#secondGuestForm").removeClass("hidden");
  } else {
    $("#secondGuestForm").addClass("hidden");
  }
});


/* ---------- PAYMENT ---------- */
function updateRemaining() {
  const total = parseFloat($("#total").val()) || 0;
  const paid = parseFloat($("#paid").val()) || 0;
  $("#remaining").text(Math.max(total - paid, 0).toFixed(2));
}

/* ---------- CONFIRM ---------- */
function confirmBooking() {
  if (!SELECTED_BED) {
    alert(t("select_a_bed"));
    return;
  }

  const name = $("#customerName").val().trim();
  const passport = $("#passport").val().trim();
  const contact = $("#contact").val().trim();
  const total = $("#total").val();
  const paid = $("#paid").val();
  const isHourly = $("#isHourlyBooking").is(":checked");
  const checkin = $("#checkin").val();
  const checkout = $("#checkout").val();
  const effectiveCheckout = (isHourly && checkout <= checkin)
    ? addOneDay(checkin)
    : checkout;

  if (!name || !passport || !contact || !total) {
    alert(t("fill_all_required_fields"));
    return;
  }

  const isDouble = SELECTED_BED.bed_type === "double";
  const secondEnabled = $("#enableSecondGuest").is(":checked");

  let secondGuest = null;

  if (isDouble && secondEnabled) {
    const name2 = $("#customerName2").val().trim();
    const passport2 = $("#passport2").val().trim();
    const contact2 = $("#contact2").val().trim();

    if (!name2 || !passport2 || !contact2) {
      alert(t("fill_all_required_fields"));
      return;
    }

    secondGuest = {
      name: name2,
      passport_id: passport2,
      contact: contact2
    };
  }

  const btn = document.getElementById("confirmBookingBtn");
  btn.disabled = true;
  btn.classList.add("opacity-60", "cursor-not-allowed");

  apiPost("/booking/", {
    branch_id: CURRENT_BRANCH,

    // primary guest
    name: name,
    passport_id: passport,
    contact: contact,

    // optional second guest
    second_guest: secondGuest,

    room_id: CURRENT_ROOM_ID,
    bed_id: SELECTED_BED.id,
    total: parseFloat(total),
    paid: paid ? parseFloat(paid) : 0,
    checkin: checkin,
    checkout: effectiveCheckout,
    notify_date: $("#notifyDate").val(),
    is_hourly: isHourly
  })
  .done(function () {
    alert("✅ " + t("booking_created"));
    btn.disabled = false;
    btn.classList.remove("opacity-60", "cursor-not-allowed");
    window.location.reload();
  })
  .fail(function () {
    btn.disabled = false;
    btn.classList.remove("opacity-60", "cursor-not-allowed");
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
  $("#bhRoomFilter").val("");
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
  const selectedRoomId = ($("#bhRoomFilter").val() || "").trim();

  let selectedRoom = null;
  if (selectedRoomId) {
    selectedRoom = (BOOKING_HISTORY_ROOMS || []).find(r => String(r.id) === selectedRoomId);
  }

  const selectedRoomNames = selectedRoom ? new Set([
    String(selectedRoom.room_name || "").toLowerCase(),
    String(selectedRoom.room_number || "").toLowerCase(),
    String(selectedRoom.number || "").toLowerCase()
  ]) : null;

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
      (!q ||
        (r.customer_name || "").toLowerCase().includes(q) ||
        (r.passport_id || "").toLowerCase().includes(q)) &&
      (!selectedRoomNames ||
        selectedRoomNames.has(String(r.room_name || "").toLowerCase()) ||
        selectedRoomNames.has(String(r.room_number || "").toLowerCase()))
    )
    .forEach(r => {
      const secondGuestName =
          Array.isArray(r.second_guests) && r.second_guests.length > 0
            ? r.second_guests[0].name
            : null;

      $c.append(`
        <div class="py-3 text-sm">
          <div class="font-semibold">
            👤 ${r.customer_name}
          </div>

          ${
            secondGuestName
              ? `<div class="text-xs text-purple-600">
                  👥 ${secondGuestName}
                </div>`
              : ``
          }

          <div class="text-xs text-tgHint">
            🪪 ${r.passport_id || "—"}
          </div>

          <div class="mt-1 text-xs text-gray-600">
            🏠 ${r.room_name || r.room_number} • 🛏 ${t("bed")} ${r.bed_number}
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

$("#bhRoomFilter").on("change", function () {
  loadBookingHistory();
});

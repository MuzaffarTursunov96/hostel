/* ===============================
   GLOBAL STATE
================================ */
let rooms = [];
let countdownTimers = new Map();
let currentEditingBooking = null;

let ALL_ACTIVE_BOOKINGS = [];
let CURRENT_BRANCH = null;
let ACTIVE_BOOKING_ROOM_FILTER = "";



function getDashboardBedIcon(bedType) {
  switch (bedType) {
    case "double":
      return "👥";   // double bed
    case "child":
      return "🧸";   // child bed
    case "single":
    default:
      return "👤";   // single / fallback
  }
}




/* ===============================
   LOAD DASHBOARD
================================ */
function loadDashboard(filter=false) {

    const checkin = $("#fromDate").val();
    const checkout = $("#toDate").val();
    
    if(filter){
        var params ={
            branch_id: CURRENT_BRANCH,
            checkin_date: checkin,
            checkout_date: checkout
        }
    }else{
        var params ={branch_id: CURRENT_BRANCH}
    }

    countdownTimers.forEach((timerId) => clearInterval(timerId));
    countdownTimers.clear();


  $("#roomsGrid").empty();

  $("#dashboardSkeleton").removeClass("hidden");
  $("#roomsGrid").addClass("hidden");

  $.get("/api2/dashboard/rooms", params, function (data) {

    rooms = data || [];

    if (!rooms.length) {
      $("#roomsGrid").html(
        `<div class="text-center text-gray-500 py-10">${t("no_rooms_found")}</div>`
      );
    }

    $.each(rooms, function (_, room) {

      const $roomEl = $(`
        <div class="bg-white rounded-2xl shadow p-4 space-y-3">
          <div class="font-semibold text-gray-900">
            🏠 ${room.room_name || room.room_number}
          </div>
          <div class="beds-flow flex flex-wrap gap-2"></div>
        </div>
      `);

      const $bedsFlow = $roomEl.find(".beds-flow");

      $.each(room.beds || [], function (_, bed) {
        const isBusy = bed.is_busy === true;

        const $bedEl = $(`
                <div class="bed-card w-[31%] sm:w-[120px] rounded-xl border overflow-hidden cursor-pointer
                    ${isBusy ? 'border-red-300' : 'border-green-300'}"
                    onclick="onBedClick(${bed.bed_id}, ${isBusy})">

                  <div class="bed-header flex justify-between items-center px-2 py-1 text-[11px] font-semibold
                      ${isBusy ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">

                    <span>
                      ${t("bed")} ${bed.bed_number}
                    </span>


                    ${
                      bed.has_future
                        ? `<span class="future-icon text-blue-600 cursor-pointer"
                                onclick="openFutureBookings(${bed.bed_id}, event)">📅</span>`
                        : ``
                    }
                  </div>


                  <div class="bed-body grid grid-cols-2 text-center text-[10px] p-1">
                    <div><strong>00</strong><br>${t("days")}</div>
                    <div><strong>00</strong><br>${t("hours")}</div>
                    <div><strong>00</strong><br>${t("minutes")}</div>
                    <div><strong>00</strong><br>${t("seconds")}</div>
                  </div>

                  <div class="px-2 pb-1 text-[10px] font-semibold flex items-center gap-1 whitespace-nowrap">
                    <span class="inline-flex">
                      ${getDashboardBedIcon(bed.bed_type)}
                    </span>

                    ${
                      isBusy
                        ? `<span class="text-red-700 inline-flex">🕒 ${formatDate(bed.checkout_date)}</span>`
                        : `<span class="text-green-700 inline-flex">✔ ${t("free")}</span>`
                    }
                  </div>

                  <div class="bed-status h-1 ${isBusy ? 'bg-red-500' : 'bg-green-500'}"></div>

                </div>
              `);


        $bedsFlow.append($bedEl);

        if (isBusy && bed.checkout_date) {
          startCountdown(
            $bedEl.find(".bed-body")[0],
            bed.checkout_date
          );
        }
      });

      $("#roomsGrid").append($roomEl);
    });

    $("#dashboardSkeleton").addClass("hidden");
    $("#roomsGrid").removeClass("hidden");
  });
}


window.openFutureBookings = function (bedId, e) {
  
  e.stopPropagation(); // 🔥 prevent bed click
  $("#futureBookingsModal").removeClass("hidden");
  showFutureBookingsModal(bedId);
};


window.closeFutureBookings = function () {
  $("#futureBookingsModal").addClass("hidden");
};


/* ===============================
   COUNTDOWN TIMER
================================ */
function startCountdown(container, checkoutDate) {
  const existingTimer = countdownTimers.get(container);
  if (existingTimer) clearInterval(existingTimer);

  const timerId = setInterval(() => {
    const now = new Date();
    const end = new Date(checkoutDate);
    const diff = end - now;

    if (diff <= 0) {
      clearInterval(timerId);
      countdownTimers.delete(container);
      container.innerHTML =
        `<div class="col-span-2 text-green-600 font-semibold">✔ ${t("free")}</div>`;
      return;
    }

    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const m = Math.floor((diff / (1000 * 60)) % 60);
    const s = Math.floor((diff / 1000) % 60);

    const boxes = container.querySelectorAll("strong");
    boxes[0].innerText = d;
    boxes[1].innerText = h;
    boxes[2].innerText = m;
    boxes[3].innerText = s;
  }, 1000);

  countdownTimers.set(container, timerId);
}

/* ===============================
   BED CLICK
================================ */
function onBedClick(bedId) {
  if (!bedId) return;
  $("#futureBookingsModal").removeClass("hidden");
  showFutureBookingsModal(bedId);
}


/* ===============================
   FILTERS
================================ */
function applyFilter() {
  const from = $("#fromDate").val();
  const to = $("#toDate").val();

  if (!from || !to) {
    alert(t("please_select_both_dates"));
    return;
  }

  if (from > to) {
    alert(t("from_date_must_be_before_to_date"));
    return;
  }

  loadDashboard(filter=true);
}


function showFutureBookingsModal(bedId) {
  CURRENT_BED_ID = bedId;

  $("#futureBookingsModal").removeClass("hidden");
  $("#futureBookingsTable").html(`${t("loading")}...`);

  fetch(`/api2/dashboard/beds/future-bookings?branch_id=${CURRENT_BRANCH}&bed_id=${bedId}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(renderFutureBookings)
    .catch(() => {
      $("#futureBookingsTable").html(
        `<p class="text-red-500 text-center">${t("request_failed")}</p>`
      );
    });
}


function closeFutureBookings() {
  $("#futureBookingsModal").addClass("hidden");
}

function renderFutureBookings(rows) {
  const table = $("#futureBookingsTable");
  table.empty();

  if (!rows || rows.length === 0) {
    table.html(`
      <p class="text-center text-gray-500">
        ${t("no_future_bookings")}
      </p>
    `);
    return;
  }

  rows.forEach(b => {
    table.append(`
      <div class="bg-white rounded-xl border p-3 mb-3">

        <div class="text-sm font-medium">
          ${b.customer_name || ""}
        </div>

        <div class="text-xs text-gray-500 mb-2">
          ${b.checkin_date} → ${b.checkout_date}
        </div>

        <div class="flex justify-end gap-2">

          <!-- EDIT BUTTON -->
          <button
            class="px-3 py-1.5 text-xs rounded-lg border"
            onclick='openEditFromFuture(${JSON.stringify(b)})'>
            ✏️ ${t("edit")}
          </button>

          <!-- CANCEL BUTTON -->
          <button
            class="px-3 py-1.5 text-xs rounded-lg border text-red-600"
            onclick='openCancelFutureBooking(${JSON.stringify(b)})'>
            ❌ ${t("cancel")}
          </button>

        </div>
      </div>
    `);
  });
}





window.cancelFutureBooking = function (bookingId) {
  if (!confirm(t("cancel_booking"))) return;

  fetch("/api2/active-bookings/cancel", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: bookingId,
      branch_id: CURRENT_BRANCH
    })
  })
  .then(() => {
    closeFutureBookings();   // close modal
    loadDashboard();         // refresh rooms
  });
};

window.openEditFromFuture = function (booking) {
  // 1️⃣ Close future bookings modal FIRST
  closeFutureBookings();

  // 2️⃣ Small delay to allow DOM repaint (important on mobile)
  setTimeout(() => {
    openEditFutureBooking(booking);
  }, 150);
};



/* ===============================
   EDIT FUTURE BOOKING
================================ */

let currentFutureBooking = null;

window.openEditFutureBooking = function (booking) {
  currentFutureBooking = booking;

  $("#editFutureBookingId").val(booking.id);
  $("#editFutureCheckin").val(booking.checkin_date);
  $("#editFutureCheckout").val(booking.checkout_date);
  $("#editFutureTotal").val(booking.total_amount);

  $("#editFutureBookingModal").removeClass("hidden");

  loadFutureEditRooms(booking);
};

window.closeEditFutureBooking = function () {
  $("#editFutureBookingModal").addClass("hidden");
};


function loadFutureEditRooms(booking) {
  fetch(`/api2/rooms?branch_id=${CURRENT_BRANCH}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(rooms => {
      const sel = $("#editFutureRoom").empty();

      rooms.forEach(r => {
        const label = r.room_name || r.room_number;
        sel.append(`<option value="${r.id}">${label}</option>`);

      });

      sel.val(booking.room_id);
      loadFutureEditBeds(booking);
    });
}

$(document).on("change", "#editFutureRoom", function () {
  if (!currentFutureBooking) return;

  currentFutureBooking.room_id = Number($(this).val());
  loadFutureEditBeds(currentFutureBooking);
});

function loadFutureEditBeds(booking) {
  fetch(`/api2/beds?branch_id=${CURRENT_BRANCH}&room_id=${booking.room_id}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(beds => {
      const sel = $("#editFutureBed").empty();

      beds.forEach(b => {
        sel.append(`<option value="${b.id}">${t("bed")} ${b.bed_number}</option>`);
      });

      sel.val(booking.bed_id);
    });
}



function resetFilter() {
    $("#fromDate").val("");
    $("#toDate").val("");
  setTodayDefault()
  loadDashboard();
}

/* ===============================
   ACTIVE BOOKINGS
================================ */
window.openActiveBookings = function () {
  $("#activeBookingsModal").removeClass("hidden");
  loadActiveBookings();
};

window.closeActiveBookings = function () {
  $("#activeBookingsModal").addClass("hidden");
};

function loadActiveBookings() {
  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  loadActiveBookingRoomFilter();
  fetch(`/api2/active-bookings?branch_id=${CURRENT_BRANCH}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(rows => {
      ALL_ACTIVE_BOOKINGS = rows || [];
      applyActiveBookingsFilters();
    })
    .catch(() => {
      $("#activeBookingsTable").html(
        `<p class="text-red-500">${t("failed_to_load_active_bookings")}</p>`
      );
    });
}

function applyActiveBookingsFilters() {
  const searchValue = ($("#activeBookingSearch").val() || "").toLowerCase().trim();
  const roomValue = ($("#activeBookingRoomFilter").val() || "").trim();

  let filtered = ALL_ACTIVE_BOOKINGS.slice();

  if (roomValue) {
    filtered = filtered.filter(b => String(b.room_id) === roomValue);
  }

  if (searchValue) {
    filtered = filtered.filter(b =>
      (b.customer_name || "").toLowerCase().includes(searchValue) ||
      (b.passport_id || "").toLowerCase().includes(searchValue) ||
      (b.room_name || "").toLowerCase().includes(searchValue) ||
      String(b.room_number).includes(searchValue) ||
      String(b.bed_number).includes(searchValue)
    );
  }

  renderActiveBookings(filtered);
}

function loadActiveBookingRoomFilter() {
  fetch(`/api2/rooms?branch_id=${CURRENT_BRANCH}`, { credentials: "include" })
    .then(r => r.json())
    .then(rows => {
      const $sel = $("#activeBookingRoomFilter");
      const lang = (window.CURRENT_LANG || "ru").toLowerCase();
      const allLabel = lang.startsWith("uz") ? "Barcha xonalar" : "Все комнаты";

      $sel.empty();
      $sel.append(`<option value="">${allLabel}</option>`);

      (rows || []).forEach(r => {
        const label = r.room_name || r.room_number || r.number || (`#${r.id}`);
        $sel.append(`<option value="${r.id}">${label}</option>`);
      });

      if (ACTIVE_BOOKING_ROOM_FILTER) {
        $sel.val(ACTIVE_BOOKING_ROOM_FILTER);
      }
    })
    .catch(() => {});
}

$(document).on("input", "#activeBookingSearch", function () {
  applyActiveBookingsFilters();
});

$(document).on("change", "#activeBookingRoomFilter", function () {
  ACTIVE_BOOKING_ROOM_FILTER = ($(this).val() || "").trim();
  applyActiveBookingsFilters();
});


function renderActiveBookings(bookings) {
  const container = $("#activeBookingsTable");
  container.empty();

  bookings.forEach(b => {
  
  const secondGuestName =
    Array.isArray(b.second_guests) && b.second_guests.length > 0
      ? b.second_guests[0].name
      : null;

  container.append(`
    <div class="bg-white rounded-xl shadow p-4 mb-3 space-y-2">

      <!-- CUSTOMER -->
      <div class="flex justify-between items-start">
        <div>
          <div class="font-semibold text-gray-900">
            👤 ${b.customer_name}
          </div>

          ${
            secondGuestName
              ? `<div class="text-xs text-purple-600">
                  👥 ${secondGuestName}
                </div>`
              : ``
          }

          <div class="text-xs text-gray-500">
            🪪 ${b.passport_id}
          </div>
        </div>

        <div class="text-right">
          <div class="text-xs text-gray-500">Total</div>
          <div class="font-bold">
            ${b.total_amount}
          </div>
        </div>
      </div>

      <!-- ROOM / BED -->
      <div class="text-sm text-gray-600">
        🏠 ${b.room_name || b.room_number} • 🛏 ${t("bed")} ${b.bed_number}

      </div>

      <!-- DATES -->
      <div class="text-sm text-gray-600">
        📅 ${b.checkin_date} → ${b.checkout_date}
      </div>

      <!-- ACTIONS -->
      <div class="flex gap-2 pt-2">
        <button
          class="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 rounded-lg text-sm"
          onclick='openEditBooking(${JSON.stringify(b)})'>
          ✏ ${t("edit")}
        </button>

        <button
          class="flex-1 bg-red-500 hover:bg-red-600 text-white py-2 rounded-lg text-sm"
          onclick="cancelBooking(${b.id})">
          ❌ ${t("cancel")}
        </button>
      </div>

    </div>
  `);
});

}


function setTodayDefault() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  const today = `${year}-${month}-${day}`;

  const from = document.getElementById("fromDate");
  const to = document.getElementById("toDate");

  if (from && !from.value) from.value = today;
  if (to && !to.value) to.value = today;
}


/* ===============================
   EDIT BOOKING (FIXED)
================================ */
window.openEditBooking = function (booking) {

  // console.log("EDIT BOOKING RAW:", booking);
  // console.log("bed_type:", booking.bed_type);
  // console.log("second_guests:", booking.second_guests);
  
  currentEditingBooking = booking;

  $("#editBookingId").val(booking.id);
  $("#editCheckout").val(booking.checkout_date);
  $("#editCheckin").val(booking.checkin_date);
  $("#editTotal").val(booking.total_amount);

  $("#editBookingModal").removeClass("hidden");

  loadEditRooms(booking);
};



window.closeEditBooking = function () {
  $("#editBookingModal").addClass("hidden");
};

function loadEditRooms(booking) {
  fetch(`/api2/rooms?branch_id=${CURRENT_BRANCH}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(rooms => {
      const sel = $("#editRoom").empty();

      rooms.forEach(r => {
        const label = r.room_name || r.room_number;
        sel.append(`<option value="${r.id}">${label}</option>`);

      });
    
      // ✅ select first room by default
      sel.val(booking['room_id']);
      loadEditBeds(booking); // 🔥 NOW room_id IS VALID
      
    });
}

$(document).on("change", "#editRoom", function () {
  if (!currentEditingBooking) return;

  // update booking object with new room
  currentEditingBooking.room_id = Number($(this).val());

  // reload beds for selected room
  loadEditBeds(currentEditingBooking);
});





function loadEditBeds(booking) {
  const roomId = $("#editRoom").val();

  fetch(`/api2/beds?branch_id=${CURRENT_BRANCH}&room_id=${roomId}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(beds => {
       
      const sel = $("#editBed").empty();
      beds.forEach(b => {
        sel.append(`<option value="${b.id}">${t("bed")} ${b.bed_number}</option>`);
      });
      
      sel.val(booking["bed_id"]);
    });
}

/* ===============================
   SAVE EDIT
================================ */
$("#editBookingForm").on("submit", function (e) {
  e.preventDefault();

  fetch("/api2/active-bookings/update-admin", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: Number($("#editBookingId").val()),
      room_id: Number($("#editRoom").val()),
      bed_id: Number($("#editBed").val()),
      checkin_date: $("#editCheckin").val(),
      checkout_date: $("#editCheckout").val(),
      total_amount: Number($("#editTotal").val())
    })
  })
  .then(() => {
    closeEditBooking();
    loadActiveBookings();
    loadDashboard();
  });
});

/* ===============================
   CANCEL
================================ */
window.cancelBooking = function (id) {
  if (!confirm("Cancel booking?")) return;

  fetch("/api2/active-bookings/cancel", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: id,
      branch_id: CURRENT_BRANCH
    })
  })
  .then(() => {
    // ✅ reload active bookings modal
    loadActiveBookings();

    // ✅ clear old countdown timers
    countdownTimers.forEach((timerId) => clearInterval(timerId));
    countdownTimers.clear();

    // ✅ reload dashboard grid
    loadDashboard();

    // ✅ optional UX improvement
    closeActiveBookings();
  });
};


/* ===============================
   HELPERS
================================ */
function formatDate(d) {
  return new Date(d).toLocaleDateString();
}

/* ===============================
   INIT
================================ */
$(document).ready(function () {
  setTodayDefault();

  apiGet("/auth/me").done(function (me) {
    CURRENT_BRANCH = me.branch_id;

    localStorage.setItem("CURRENT_BRANCH", CURRENT_BRANCH);

    loadDashboard();

  

  }).fail(function () {
    // fallback
    loadDashboard();
  });

  document.addEventListener("DOMContentLoaded", startWebSocket);

});




$("#editFutureBookingForm").on("submit", function (e) {
  e.preventDefault();

  fetch("/api2/booking/update-future-booking", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: Number($("#editFutureBookingId").val()),
      checkin_date: $("#editFutureCheckin").val(),
      checkout_date: $("#editFutureCheckout").val(),
      room_id: Number($("#editFutureRoom").val()),
      bed_id: Number($("#editFutureBed").val()),
      total_amount: Number($("#editFutureTotal").val())
    })
  })
  .then(() => {
    closeEditFutureBooking();
    loadDashboard();
  });
});




let CURRENT_FUTURE_BOOKING = null;

function openCancelFutureBooking(booking) {
  CURRENT_FUTURE_BOOKING = booking;

  $("#paidAmountLabel").text(
    `${t("paid_amount")}: ${booking.paid_amount}`
  );

  $("#refundAmount").val(0);
  $("#refundReason").val("");

  $("#cancelFutureModal").removeClass("hidden");
}

function confirmCancelFuture() {
  const amount = parseFloat($("#refundAmount").val() || 0);
  const paid = parseFloat(CURRENT_FUTURE_BOOKING.paid_amount);
  const title = $("#refundReason").val().trim();

  if (isNaN(amount)) {
    return alert(t("invalid_amount"));
  }
  if (amount < 0) {
    return alert(t("refund_cannot_be_negative"));
  }
  if (amount > paid) {
    return alert(t("refund_exceeds_paid"));
  }
  if (amount > 0 && !title) {
    return alert(t("refund_title_required"));
  }

  fetch("/api2/booking/future-bookings/cancel", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      booking_id: CURRENT_FUTURE_BOOKING.id,
      branch_id: CURRENT_BRANCH,
      refund_amount: amount,
      refund_title: title
    })
  })
    .then(r => r.json())
    .then(() => {
      closeCancelFuture();
      closeFutureBookings();
      loadDashboard();
 // your existing refresh
    });
}


function closeCancelFuture() {
  $("#cancelFutureModal").addClass("hidden");
}




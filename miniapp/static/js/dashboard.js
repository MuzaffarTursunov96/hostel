/* ===============================
   GLOBAL STATE
================================ */
let rooms = [];
let countdownTimers = {};
let currentEditingBooking = null;

let ALL_ACTIVE_BOOKINGS = [];


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

    Object.values(countdownTimers).forEach(t => clearInterval(t));
     countdownTimers = {};


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
            🏠 ${t("room")} ${room.room_number}
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

                    <span>${t("bed")} ${bed.bed_number}</span>

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

                  <div class="px-2 pb-1 text-[10px] font-semibold">
                    ${
                      isBusy
                        ? `🕒 <span class="text-red-700">${formatDate(bed.checkout_date)}</span>`
                        : `<span class="text-green-700">✔ ${t("free")}</span>`
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
  clearInterval(countdownTimers[container]);

  countdownTimers[container] = setInterval(() => {
    const now = new Date();
    const end = new Date(checkoutDate);
    const diff = end - now;

    if (diff <= 0) {
      clearInterval(countdownTimers[container]);
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
  const c = $("#futureBookingsTable");
  c.empty();

  if (!rows.length) {
    c.html(`<p class="text-center text-gray-500">
      ${t("no_future_bookings")}
    </p>`);
    return;
  }

  rows.forEach(b => {
    c.append(`
      <div class="bg-white rounded-xl border p-3 flex justify-between items-center">

        <div>
          <div class="text-sm font-medium">
            ${b.customer_name}
          </div>
          <div class="text-xs text-gray-500">
            ${b.checkin_date} → ${b.checkout_date}
          </div>
        </div>

        <button
          class="px-3 py-1 text-sm rounded-lg border"
          onclick='openCancelFutureBooking(${JSON.stringify(b)})'>
          ${t("cancel")}
        </button>

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
        sel.append(`<option value="${r.id}">${t("room")} ${r.room_number}</option>`);
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
  fetch(`/api2/active-bookings?branch_id=${CURRENT_BRANCH}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(rows => {
      ALL_ACTIVE_BOOKINGS = rows || [];
      renderActiveBookings(ALL_ACTIVE_BOOKINGS);
    })
    .catch(() => {
      $("#activeBookingsTable").html(
        `<p class="text-red-500">${t("failed_to_load_active_bookings")}</p>`
      );
    });
}

$(document).on("input", "#activeBookingSearch", function () {
  const q = $(this).val().toLowerCase().trim();

  if (!q) {
    renderActiveBookings(ALL_ACTIVE_BOOKINGS);
    return;
  }

  const filtered = ALL_ACTIVE_BOOKINGS.filter(b =>
    (b.customer_name || "").toLowerCase().includes(q) ||
    (b.passport_id || "").toLowerCase().includes(q) ||
    String(b.room_number).includes(q) ||
    String(b.bed_number).includes(q)
  );

  renderActiveBookings(filtered);
});


function renderActiveBookings(bookings) {
  const container = $("#activeBookingsTable");
  container.empty();

  bookings.forEach(b => {
  container.append(`
    <div class="bg-white rounded-xl shadow p-4 mb-3 space-y-2">

      <!-- CUSTOMER -->
      <div class="flex justify-between items-start">
        <div>
          <div class="font-semibold text-gray-900">
            👤 ${b.customer_name}
          </div>

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
        🏠 ${t("room")} ${b.room_number} • 🛏 ${t("bed")} ${b.bed_number}
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
  currentEditingBooking = booking;

  $("#editBookingId").val(booking.id);
  $("#editCheckout").val(booking.checkout_date);
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
        sel.append(`<option value="${r.id}">${t("room")} ${r.room_number}</option>`);
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
    Object.values(countdownTimers).forEach(t => clearInterval(t));
    countdownTimers = {};

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

    // 🔐 SAVE TO FLASK SESSION
    fetch("/api2/auth/save-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        branch_id: CURRENT_BRANCH
      })
    }).then(() => {
      loadDashboard();
      // startWebSocket();
    });

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


function openFutureBookings(bedId) {
  CURRENT_BED_ID = bedId;
  $("#futureBookingsModal").removeClass("hidden");
  loadFutureBookings();
}

function closeFutureBookings() {
  $("#futureBookingsModal").addClass("hidden");
}

function loadFutureBookings() {
  fetch(`/api/dashboard/beds/future-bookings?branch_id=${CURRENT_BRANCH}&bed_id=${CURRENT_BED_ID}`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(renderFutureBookings);
}


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

  fetch("/api/booking/future-bookings/cancel", {
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


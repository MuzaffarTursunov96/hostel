let CURRENT_ROOM = null;
let CURRENT_ROOM_ID = null;
let SELECTED_BED_ID = null;
let CURRENT_BRANCH = null;

$(document).ready(function () {
  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }

  loadRooms();
  document.addEventListener("DOMContentLoaded", startWebSocket);
});

/* ================= ROOMS ================= */

function loadRooms() {
  $("#roomsList").empty();
  $("#bedsList").empty();
  $("#bedsTitle").text(t("beds"));


  apiGet("/rooms", { branch_id: CURRENT_BRANCH })
    .done(function (rooms) {
      if (!rooms.length) return;

      rooms.forEach(room => {
        const btn = $(`
            <button
              class="room-item px-4 py-2 rounded-full border text-sm whitespace-nowrap
                    bg-gray-100 text-gray-700">
              🏠 ${t("room")} ${room.room_number}
            </button>
          `);


        btn.on("click", function () {
          $(".room-item").removeClass("bg-tgButton text-white");
          btn.addClass("bg-tgButton text-white");

          selectRoom(room);
        });

        $("#roomsList").append(btn);
      });

      // auto-select first room
      $(".room-item").first().click();
    });
}

function selectRoom(room) {
  CURRENT_ROOM = room;
  CURRENT_ROOM_ID = room.id;
  SELECTED_BED_ID = null;

  $("#bedsTitle").text(`${t("room")} ${room.room_number} — ${t("beds")}`);
  loadBeds(room.id);
}

/* ================= BEDS ================= */

function loadBeds(roomId) {
  $("#bedsList").empty();
  SELECTED_BED_ID = null;

  // 1️⃣ get all beds
  apiGet("/beds", {
    branch_id: CURRENT_BRANCH,
    room_id: roomId
  }).done(function (beds) {

    // 2️⃣ get busy beds ONCE
    apiGet("/beds/busy-now", {
      branch_id: CURRENT_BRANCH,
      room_id: roomId
    }).done(function (resp) {

      const busyBeds = new Set(resp.busy_beds);

      beds.forEach(bed => {
        const busy = busyBeds.has(bed.id);

        const btn = $(`
          <button
            class="bed-item rounded-xl p-3 border flex flex-col gap-2
              ${busy ? "border-red-400 bg-red-50" : "border-green-400 bg-green-50"}">

            <div class="flex justify-between items-center">
              <span class="font-medium">
                🛏 ${t("bed")} ${bed.bed_number}
              </span>
              <span class="text-xs px-2 py-0.5 rounded-full
                ${busy ? "bg-red-500" : "bg-green-500"} text-white">
                ${busy ? t("busy") : t("free")}
              </span>
            </div>
          </button>
        `);

        btn.on("click", function () {
          $(".bed-item").removeClass("ring-2 ring-tgButton");
          btn.addClass("ring-2 ring-tgButton");
          SELECTED_BED_ID = bed.id;
        });

        $("#bedsList").append(btn);
      });

    });
  });
}


/* ================= ACTIONS ================= */

// function addRoom() {
//   const $btn = $("#addRoomBtn");

//   // ✅ disable immediately
//   $btn.prop("disabled", true).addClass("opacity-50 cursor-not-allowed");

//   apiGet("/rooms", { branch_id: CURRENT_BRANCH })
//     .done(function (rooms) {
//       const nextNumber = getNextRoomNumber(rooms || []);

//       apiPost("/rooms", {
//         branch_id: CURRENT_BRANCH,
//         number: nextNumber
//       }).done(function () {
//         loadRooms();
//       }).always(function () {
//         // ✅ re-enable after everything finishes
//         $btn.prop("disabled", false).removeClass("opacity-50 cursor-not-allowed");
//       });
//     })
//     .fail(function () {
//       $btn.prop("disabled", false).removeClass("opacity-50 cursor-not-allowed");
//     });
// }

function addRoom() {
  $("#roomNameInput").val("");
  $("#roomModal").removeClass("hidden").addClass("flex");
}


function closeRoomModal() {
  $("#roomModal").addClass("hidden").removeClass("flex");
}

function submitRoom() {
  const roomName = $("#roomNameInput").val().trim();

  if (!roomName) {
    alert(t("room_name_required"));
    return;
  }

  // disable button to prevent double submit
  const btn = $("#roomModal button.bg-tgButton");
  btn.prop("disabled", true).addClass("opacity-50");

  apiGet("/rooms", { branch_id: CURRENT_BRANCH })
    .done(function (rooms) {
      const nextNumber = getNextRoomNumber(rooms || []);

      apiPost("/rooms", {
        branch_id: CURRENT_BRANCH,
        number: nextNumber,
        room_name: roomName
      })
      .done(function () {
        closeRoomModal();
        loadRooms();
      })
      .always(function () {
        btn.prop("disabled", false).removeClass("opacity-50");
      });
    });
}



function deleteRoom() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }

  // Check bookings first (desktop logic)
  apiGet(`/rooms/${CURRENT_ROOM_ID}/has-bookings`, {
    branch_id: CURRENT_BRANCH
  }).done(function (resp) {

    if (resp.has_booking) {
      alert(t("this_room_has_active_or_future_bookings"));
      return;
    }

    if (!confirm(t("delete_this_room_and_all_its_beds"))) {
      return;
    }

    apiDelete(`/rooms/${CURRENT_ROOM_ID}`, 
        {
            branch_id: CURRENT_BRANCH
        }
    ).done(function () {
        CURRENT_ROOM_ID = null;
        CURRENT_ROOM = null;
        $("#bedsList").empty();
        loadRooms();
        });

    });
}



function addBed() {
  if (!CURRENT_ROOM_ID) return;

  const $btn = $("#addBedBtn");

  // ✅ disable button immediately
  $btn.prop("disabled", true).addClass("opacity-50 cursor-not-allowed");

  apiPost("/beds", {
    branch_id: CURRENT_BRANCH,
    room_id: CURRENT_ROOM_ID
  }).done(() => loadBeds(CURRENT_ROOM_ID)).always(() => {
    // ✅ re-enable after request finishes
    $btn.prop("disabled", false).removeClass("opacity-50 cursor-not-allowed");
  });;
}

function deleteBed() {
  if (!SELECTED_BED_ID) {
    alert(t("select_a_bed_first"));
    return;
  }

  // 1️⃣ CHECK IF BED IS BUSY
  apiGet(`/beds/${SELECTED_BED_ID}/busy`, {
    branch_id: CURRENT_BRANCH
  }).done(function (resp) {

    if (resp.busy) {
      alert(t("this_room_has_active_or_future_bookings"));
      return;
    }

    // 2️⃣ CONFIRM DELETE
    if (!confirm(t("delete_this_room_and_all_its_beds"))) {
      return;
    }

    // 3️⃣ DELETE
    apiDelete(`/beds/${SELECTED_BED_ID}`)
      .done(function (data) {
        if(data.status == 500){
          alert(t("cannot_delete_bed_reason"));
        }
        SELECTED_BED_ID = null;
        loadBeds(CURRENT_ROOM_ID);
      });

  });
}



function getNextRoomNumber(rooms) {
  let max = 0;
  rooms.forEach(r => {
    const n = parseInt(r.room_number);
    if (!isNaN(n)) max = Math.max(max, n);
  });
  return String(max + 1);
}

let CURRENT_ROOM = null;
let CURRENT_ROOM_ID = null;
// let SELECTED_BED_ID = null;
let CURRENT_BRANCH = null;
let SELECTED_BED = null;


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
              🏠 ${room.room_name || room.room_number}
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
  // SELECTED_BED_ID = null;

  $("#bedsTitle").text(`${room.room_name || room.room_number} — ${t("beds")}`);

  loadBeds(room.id);
}

/* ================= BEDS ================= */

const BED_TYPE_UI = {
  single: {
    icon: "👤",
    title: t("single_bed") || "Одноместная"
  },
  double: {
    icon: "👥",
    title: t("double_bed") || "Двухместная"
  },
  child: {
    icon: "🧸",
    title: t("child_bed") || "Детская"
  }
};






function loadBeds(roomId) {
  $("#bedsList").empty();
  SELECTED_BED = null;


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

        const ui = BED_TYPE_UI[bed.bed_type] || BED_TYPE_UI.single;

        const btn = $(`
              <button
                class="bed-item relative rounded-2xl p-4 border transition
                  flex flex-col items-center text-center gap-2
                  ${busy
                    ? "border-red-300 bg-red-50"
                    : "border-green-300 bg-green-50 hover:bg-green-100"}">

                <!-- STATUS BADGE -->
                <span class="absolute -top-3 right-3
                  text-xs px-3 py-1 rounded-full font-medium shadow
                  ${busy ? "bg-red-500" : "bg-green-500"} text-white">
                  ${busy ? t("busy") : t("free")}
                </span>

                <!-- ICON -->
                <span class="text-3xl mt-2">
                  ${ui.icon}
                </span>

                <!-- TYPE -->
                <div class="font-semibold text-base leading-tight">
                  ${ui.title}
                </div>

                <!-- BED NUMBER -->
                <div class="text-sm text-gray-600">
                  ${t("bed")} <span class="font-semibold">${bed.bed_number}</span>
                </div>

              </button>
            `);

        btn.on("click", function () {
          $(".bed-item")
            .removeClass("ring-2 ring-tgButton scale-[1.02]")
            .addClass("scale-100");

          btn
            .addClass("ring-2 ring-tgButton scale-[1.02]");

          SELECTED_BED = bed;
        });


        $("#bedsList").append(btn);
      });

    });
  });
}


/* ================= ACTIONS ================= */



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
  if (!SELECTED_BED) {
    alert(t("select_a_bed_first"));
    return;
  }

  apiGet(`/beds/${SELECTED_BED.id}/busy`, {
    branch_id: CURRENT_BRANCH
  }).done(function (resp) {

    if (resp.busy) {
      alert(t("this_room_has_active_or_future_bookings"));
      return;
    }

    if (!confirm(t("delete_this_bed"))) {
      return;
    }

    apiDelete(`/beds/${SELECTED_BED.id}`)
      .done(function () {
        SELECTED_BED = null;
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


function openEditBed() {
  if (!SELECTED_BED) {
    alert(t("select_a_bed_first"));
    return;
  }

  $("#editBedType").val(SELECTED_BED.bed_type);
  $("#editBedModal").removeClass("hidden").addClass("flex");
}

function closeEditBedModal() {
  $("#editBedModal").addClass("hidden").removeClass("flex");
}

function saveBedType() {
  const bedType = $("#editBedType").val();

  apiPut(`/beds/${SELECTED_BED.id}`, {
    bed_number: SELECTED_BED.bed_number,
    bed_type: bedType
  }).done(function () {
    closeEditBedModal();
    loadBeds(CURRENT_ROOM_ID);
  });
}

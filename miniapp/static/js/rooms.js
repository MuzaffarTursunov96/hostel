let CURRENT_ROOM = null;
let CURRENT_ROOM_ID = null;
let CURRENT_BRANCH = null;
let SELECTED_BED = null;

function normalizeRoomType(raw) {
  const s = String(raw || "").trim().toLowerCase();
  if (!s) return "other";
  if (s === "family" || s.includes("oilav") || s.includes("family") || s.includes("сем")) return "family";
  if (s === "bed" || s.includes("kravat") || s.includes("кроват") || s.includes("bed")) return "bed";
  if (s === "other" || s.includes("boshqa") || s.includes("друг")) return "other";
  return "other";
}

function roomTypeDbValue(value) {
  const v = normalizeRoomType(value);
  if (v === "family") return "family";
  if (v === "bed") return "bed";
  return "other";
}

function roomTypeLabel(value) {
  const isRu = (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  const v = normalizeRoomType(value);
  if (v === "family") return isRu ? "Семейный" : "Oilaviy";
  if (v === "bed") return isRu ? "Кровати" : "Kravatli";
  return isRu ? "Другое" : "Boshqa";
}

function formatPrice(v) {
  if (v === null || v === undefined || String(v).trim() === "") return t("price_by_agreement");
  const n = Number(v);
  if (Number.isNaN(n)) return t("price_by_agreement");
  return `${n.toLocaleString()} ${t("currency_short")}`;
}

function formatPriceLine(hourly, daily, monthly) {
  const h = formatPrice(hourly);
  const d = formatPrice(daily);
  const m = formatPrice(monthly);
  return `⏱ ${h} | 🗓 ${d} | 📅 ${m}`;
}

function roomStatusText(status) {
  const isRu = (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  const s = String(status || "").toLowerCase();
  if (s === "full") return isRu ? "Полностью занято" : "To'liq band";
  if (s === "partial") return isRu ? "Частично занято" : "Qisman band";
  return isRu ? "Свободно" : "Bo'sh";
}

function roomStatusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "full") return "bg-red-100 text-red-700";
  if (s === "partial") return "bg-amber-100 text-amber-700";
  return "bg-green-100 text-green-700";
}

function bookingModeLabel(mode) {
  const isRu = (document.documentElement.lang || "").toLowerCase().startsWith("ru");
  const m = String(mode || "bed").toLowerCase();
  if (m === "full") return isRu ? "Полная комната" : "To'liq xona";
  return isRu ? "По кроватям" : "Kravat bo'yicha";
}

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
  $("#roomPhotosList").empty();
  $("#bedsTitle").text(t("beds"));

  apiGet("/rooms", { branch_id: CURRENT_BRANCH }).done(function (rooms) {
    if (!rooms.length) {
      $("#roomPhotosList").html(`<div class="text-sm text-tgHint">${t("no_rooms_found")}</div>`);
      return;
    }

    rooms.forEach((room) => {
      const roomLabel = room.room_type
        ? `${room.room_name || room.room_number} (${roomTypeLabel(room.room_type)})`
        : `${room.room_name || room.room_number}`;
      const mode = bookingModeLabel(room.booking_mode);
      const btn = $(`
        <button
          class="room-item px-4 py-2 rounded-full border text-sm whitespace-nowrap bg-gray-100 text-gray-700 flex items-center gap-2"
        >
          <span>${roomLabel}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">${mode}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full ${roomStatusClass(room.occupancy_status)}">${roomStatusText(room.occupancy_status)}</span>
        </button>
      `);

      btn.on("click", function () {
        $(".room-item").removeClass("bg-tgButton text-white");
        btn.addClass("bg-tgButton text-white");
        selectRoom(room);
      });

      $("#roomsList").append(btn);
    });

    $(".room-item").first().click();
  });
}

function selectRoom(room) {
  CURRENT_ROOM = room;
  CURRENT_ROOM_ID = room.id;
  $("#bedsTitle").text(`${room.room_name || room.room_number} - ${t("beds")}`);
  $("#roomFixedPriceInput").val(room.price_daily ?? room.fixed_price ?? "");
  $("#roomHourlyPriceInput").val(room.price_hourly ?? "");
  $("#roomMonthlyPriceInput").val(room.price_monthly ?? "");
  $("#roomTypeInput").val(normalizeRoomType(room.room_type));
  $("#roomBookingModeInput").val((room.booking_mode || "bed").toLowerCase() === "full" ? "full" : "bed");
  loadBeds(room.id);
  loadRoomImages(room.id);
}

/* ================= BEDS ================= */

const BED_TYPE_UI = {
  single: {
    icon: "S",
    title: t("single_bed") || "Single"
  },
  double: {
    icon: "D",
    title: t("double_bed") || "Double"
  },
  child: {
    icon: "C",
    title: t("child_bed") || "Child"
  }
};

function loadBeds(roomId) {
  $("#bedsList").empty();
  SELECTED_BED = null;

  apiGet("/beds", {
    branch_id: CURRENT_BRANCH,
    room_id: roomId
  }).done(function (beds) {
    apiGet("/beds/busy-now", {
      branch_id: CURRENT_BRANCH,
      room_id: roomId
    }).done(function (resp) {
      const busyBeds = new Set(resp.busy_beds || []);

      beds.forEach((bed) => {
        const busy = busyBeds.has(bed.id);
        const ui = BED_TYPE_UI[bed.bed_type] || BED_TYPE_UI.single;

        const btn = $(`
          <button
            class="bed-item relative rounded-2xl p-4 border transition flex flex-col items-center text-center gap-2 ${
              busy ? "border-red-300 bg-red-50" : "border-green-300 bg-green-50 hover:bg-green-100"
            }"
          >
            <span class="absolute -top-3 right-3 text-xs px-3 py-1 rounded-full font-medium shadow ${
              busy ? "bg-red-500" : "bg-green-500"
            } text-white">
              ${busy ? t("busy") : t("free")}
            </span>

            <span class="text-3xl mt-2">${ui.icon}</span>
            <div class="font-semibold text-base leading-tight">${ui.title}</div>
            <div class="text-sm text-gray-600">${t("bed")} <span class="font-semibold">${bed.bed_number}</span></div>
            <div class="text-[11px] text-gray-600">${formatPriceLine(bed.price_hourly, bed.price_daily ?? bed.fixed_price, bed.price_monthly)}</div>
          </button>
        `);

        btn.on("click", function () {
          $(".bed-item").removeClass("ring-2 ring-tgButton scale-[1.02]").addClass("scale-100");
          btn.addClass("ring-2 ring-tgButton scale-[1.02]");
          SELECTED_BED = bed;
        });

        $("#bedsList").append(btn);
      });
    });
  });
}

/* ================= ROOM PHOTOS ================= */

function loadRoomImages(roomId) {
  const $list = $("#roomPhotosList");
  if (!$list.length) return;

  $list.html(`<div class="text-sm text-tgHint">${t("loading")}...</div>`);

  apiGet(`/rooms/${roomId}/images`, { branch_id: CURRENT_BRANCH })
    .done(function (resp) {
      const images = (resp && resp.images) || [];
      if (!images.length) {
        $list.html(`<div class="text-sm text-tgHint">${t("no_room_photos")}</div>`);
        return;
      }

      $list.empty();
      images.forEach((img) => {
        const item = $(`
          <div class="room-photo-card">
            <img class="room-photo-img" src="${img.image_path}" alt="room photo" loading="lazy" />
            <div class="room-photo-actions">
              <button class="room-photo-cover">${img.is_cover ? t("cover_photo") : t("set_as_cover")}</button>
              <button class="room-photo-delete">${t("delete_photo")}</button>
            </div>
          </div>
        `);

        item.find(".room-photo-cover").on("click", function () {
          if (img.is_cover) return;
          apiPut(`/rooms/${roomId}/images/${img.id}/cover`, { branch_id: CURRENT_BRANCH }).done(function () {
            loadRoomImages(roomId);
          });
        });

        item.find(".room-photo-delete").on("click", function () {
          if (!confirm(t("delete_photo_confirm"))) return;
          apiDelete(`/rooms/${roomId}/images/${img.id}`, { branch_id: CURRENT_BRANCH }).done(function () {
            loadRoomImages(roomId);
          });
        });

        $list.append(item);
      });
    })
    .fail(function () {
      $list.html(`<div class="text-sm text-red-500">${t("upload_failed")}</div>`);
    });
}

function uploadRoomPhotos() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }

  const input = document.getElementById("roomPhotoInput");
  if (!input || !input.files || !input.files.length) return;

  const form = new FormData();
  Array.from(input.files).forEach((file) => form.append("files", file));

  fetch(`/api2/rooms/${CURRENT_ROOM_ID}/images?branch_id=${encodeURIComponent(CURRENT_BRANCH)}`, {
    method: "POST",
    body: form,
    credentials: "include"
  })
    .then(async (res) => {
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = payload.detail || payload.error || t("upload_failed");
        throw new Error(msg);
      }
      input.value = "";
      loadRoomImages(CURRENT_ROOM_ID);
    })
    .catch((err) => {
      const message = (window.translateBackendError ? window.translateBackendError(err.message || "") : (err.message || t("upload_failed")));
      alert(message);
    });
}

/* ================= ACTIONS ================= */

function addRoom() {
  $("#roomNameInput").val("");
  $("#roomTypeCreateInput").val("other");
  $("#roomBookingModeCreateInput").val("bed");
  $("#roomPriceInput").val("");
  $("#roomPriceHourlyInput").val("");
  $("#roomPriceMonthlyInput").val("");
  $("#roomModal").removeClass("hidden").addClass("flex");
}

function closeRoomModal() {
  $("#roomModal").addClass("hidden").removeClass("flex");
}

function submitRoom() {
  const roomName = $("#roomNameInput").val().trim();
  const roomType = roomTypeDbValue($("#roomTypeCreateInput").val());
  const roomBookingMode = String($("#roomBookingModeCreateInput").val() || "bed").trim().toLowerCase();
  const roomPriceRaw = String($("#roomPriceInput").val() || "").trim();
  const roomPriceHourlyRaw = String($("#roomPriceHourlyInput").val() || "").trim();
  const roomPriceMonthlyRaw = String($("#roomPriceMonthlyInput").val() || "").trim();

  if (!roomName) {
    alert(t("room_name_required"));
    return;
  }

  const btn = $("#roomModal button.bg-tgButton");
  btn.prop("disabled", true).addClass("opacity-50");

  apiGet("/rooms", { branch_id: CURRENT_BRANCH }).done(function (rooms) {
    const nextNumber = getNextRoomNumber(rooms || []);

    apiPost("/rooms", {
      branch_id: CURRENT_BRANCH,
      number: nextNumber,
      room_name: roomName,
      fixed_price: roomPriceRaw ? Number(roomPriceRaw) : null,
      price_daily: roomPriceRaw ? Number(roomPriceRaw) : null,
      price_hourly: roomPriceHourlyRaw ? Number(roomPriceHourlyRaw) : null,
      price_monthly: roomPriceMonthlyRaw ? Number(roomPriceMonthlyRaw) : null,
      booking_mode: roomBookingMode === "full" ? "full" : "bed",
      room_type: roomType
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

    apiDelete(`/rooms/${CURRENT_ROOM_ID}`, { branch_id: CURRENT_BRANCH }).done(function () {
      CURRENT_ROOM_ID = null;
      CURRENT_ROOM = null;
      $("#bedsList").empty();
      $("#roomPhotosList").empty();
      loadRooms();
    });
  });
}

function addBed() {
  if (!CURRENT_ROOM_ID) return;

  const $btn = $("#addBedBtn");
  $btn.prop("disabled", true).addClass("opacity-50 cursor-not-allowed");

  apiPost("/beds", {
    branch_id: CURRENT_BRANCH,
    room_id: CURRENT_ROOM_ID
  })
    .done(() => loadBeds(CURRENT_ROOM_ID))
    .always(() => {
      $btn.prop("disabled", false).removeClass("opacity-50 cursor-not-allowed");
    });
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

    apiDelete(`/beds/${SELECTED_BED.id}`).done(function () {
      SELECTED_BED = null;
      loadBeds(CURRENT_ROOM_ID);
    });
  });
}

function getNextRoomNumber(rooms) {
  let max = 0;
  rooms.forEach((r) => {
    const n = parseInt(r.room_number, 10);
    if (!isNaN(n)) max = Math.max(max, n);
  });
  return String(max + 1);
}

function saveRoomPrice() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }
  const raw = String($("#roomFixedPriceInput").val() || "").trim();
  const hourlyRaw = String($("#roomHourlyPriceInput").val() || "").trim();
  const monthlyRaw = String($("#roomMonthlyPriceInput").val() || "").trim();
  apiPut(`/rooms/${CURRENT_ROOM_ID}/price`, {
    branch_id: CURRENT_BRANCH,
    fixed_price: raw,
    price_daily: raw,
    price_hourly: hourlyRaw,
    price_monthly: monthlyRaw
  }).done(function () {
    loadRooms();
  });
}

function clearRoomPrice() {
  $("#roomFixedPriceInput").val("");
  $("#roomHourlyPriceInput").val("");
  $("#roomMonthlyPriceInput").val("");
  saveRoomPrice();
}

function saveRoomType() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }
  const roomType = roomTypeDbValue($("#roomTypeInput").val());
  apiPut(`/rooms/${CURRENT_ROOM_ID}/type`, {
    branch_id: CURRENT_BRANCH,
    room_type: roomType
  }).done(function () {
    loadRooms();
  });
}

function saveRoomSettings() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }

  const roomType = roomTypeDbValue($("#roomTypeInput").val());
  const mode = String($("#roomBookingModeInput").val() || "bed").trim().toLowerCase();
  const daily = String($("#roomFixedPriceInput").val() || "").trim();
  const hourly = String($("#roomHourlyPriceInput").val() || "").trim();
  const monthly = String($("#roomMonthlyPriceInput").val() || "").trim();

  const reqType = apiPut(`/rooms/${CURRENT_ROOM_ID}/type`, {
    branch_id: CURRENT_BRANCH,
    room_type: roomType
  });
  const reqMode = apiPut(`/rooms/${CURRENT_ROOM_ID}/booking-mode`, {
    branch_id: CURRENT_BRANCH,
    booking_mode: mode === "full" ? "full" : "bed"
  });
  const reqPrice = apiPut(`/rooms/${CURRENT_ROOM_ID}/price`, {
    branch_id: CURRENT_BRANCH,
    fixed_price: daily,
    price_daily: daily,
    price_hourly: hourly,
    price_monthly: monthly
  });

  $.when(reqType, reqMode, reqPrice).done(function () {
    loadRooms();
  });
}

function saveRoomBookingMode() {
  if (!CURRENT_ROOM_ID) {
    alert(t("select_a_room_first"));
    return;
  }
  const mode = String($("#roomBookingModeInput").val() || "bed").trim().toLowerCase();
  apiPut(`/rooms/${CURRENT_ROOM_ID}/booking-mode`, {
    branch_id: CURRENT_BRANCH,
    booking_mode: mode === "full" ? "full" : "bed"
  }).done(function () {
    loadRooms();
  });
}

function openEditBed() {
  if (!SELECTED_BED) {
    alert(t("select_a_bed_first"));
    return;
  }

  $("#editBedType").val(SELECTED_BED.bed_type);
  $("#editBedPrice").val(SELECTED_BED.price_daily ?? SELECTED_BED.fixed_price ?? "");
  $("#editBedPriceHourly").val(SELECTED_BED.price_hourly ?? "");
  $("#editBedPriceMonthly").val(SELECTED_BED.price_monthly ?? "");
  $("#editBedModal").removeClass("hidden").addClass("flex");
}

function closeEditBedModal() {
  $("#editBedModal").addClass("hidden").removeClass("flex");
}

function saveBedType() {
  const bedType = $("#editBedType").val();
  const bedPrice = String($("#editBedPrice").val() || "").trim();
  const bedPriceHourly = String($("#editBedPriceHourly").val() || "").trim();
  const bedPriceMonthly = String($("#editBedPriceMonthly").val() || "").trim();

  apiPut(`/beds/${SELECTED_BED.id}`, {
    bed_number: SELECTED_BED.bed_number,
    bed_type: bedType,
    fixed_price: bedPrice,
    price_daily: bedPrice,
    price_hourly: bedPriceHourly,
    price_monthly: bedPriceMonthly
  }).done(function () {
    closeEditBedModal();
    loadBeds(CURRENT_ROOM_ID);
  });
}



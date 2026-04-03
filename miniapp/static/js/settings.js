let BRANCHES = [];
let CURRENT_BRANCH = null;
let CURRENT_LANG = "ru";
let SELECTED_USER_ID = null;
let SELECTED_USER_ASSIGNED_BRANCH_IDS = [];
let IS_ROOT_ADMIN = false;
let BRANCH_MAP_MODE = "new";
let BRANCH_MAP_OBJ = null;
let BRANCH_MAP_MARKER = null;
let BRANCH_MAP_POINT = null;
let NEW_BRANCH_CREATED_ID = null;
const REGION_OPTIONS = [
  { id: 6, name: "Андижанская область", normalized_name: "andizhanskaya-oblast" },
  { id: 27, name: "Бухарская область", normalized_name: "buharskaya-oblast" },
  { id: 28, name: "Джизакская область", normalized_name: "dzhizakskaya-oblast" },
  { id: 32, name: "Каракалпакстан", normalized_name: "karakalpakstan" },
  { id: 29, name: "Кашкадарьинская область", normalized_name: "kashkadarinskaya-oblast" },
  { id: 30, name: "Навоийская область", normalized_name: "navoijskaya-oblast" },
  { id: 31, name: "Наманганская область", normalized_name: "namanganskaya-oblast" },
  { id: 33, name: "Самаркандская область", normalized_name: "samarkandskaya-oblast" },
  { id: 34, name: "Сурхандарьинская область", normalized_name: "surhandarinskaya-oblast" },
  { id: 35, name: "Сырдарьинская область", normalized_name: "syrdarinskaya-oblast" },
  { id: 5, name: "Ташкентская область", normalized_name: "toshkent-oblast" },
  { id: 36, name: "Ферганская область", normalized_name: "ferganskaya-oblast" },
  { id: 37, name: "Хорезмская область", normalized_name: "horezmskaya-oblast" }
];
const REGION_CITY_OPTIONS = window.UZ_REGIONS_CITIES || {};
const CITY_DISTRICT_OPTIONS = window.UZ_CITY_DISTRICTS || {};


$(document).ready(function () {


  apiGet("/auth/me").done(function (me) {
    // alert(me)
    CURRENT_BRANCH = me.branch_id;
    // CURRENT_LANG = me.language || "ru";

    // setActiveLangUI(CURRENT_LANG);

    // рџ”ђ SAVE TO FLASK SESSION
    fetch("/auth/save-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        branch_id: CURRENT_BRANCH
      })
    }).then(() => {
      loadBranches();
      // startWebSocket();
    });

    if (me.is_admin) {
      loadUsers();     // already done
      loadBranches();  // new
      loadRootSystemExpiry();
      loadPrepaymentSettings();
    } else {
      $(".admin-only").hide();
      $(".root-only").addClass("hidden");
    }
    

    // if (me.notify_enabled !== undefined) {
    //   $("#myNotifyToggle").prop("checked", me.notify_enabled);
    // }




  }).fail(function () {
    loadBranches();

  });


   // 2пёЏвѓЈ USER PREFERENCES (рџ”Ґ NEW API)
  apiGet("/users/me/preferences").done(function (prefs) {

    CURRENT_LANG = prefs.language || "ru";
    setActiveLangUI(CURRENT_LANG);
    const rootBtn = $("#openRootManagementBtn");
    if (rootBtn.length) {
      const label = CURRENT_LANG === "uz" ? "Root boshqaruvini ochish" : "Открыть Root управление";
      const rootLabel = rootBtn.find(".root-link-label");
      if (rootLabel.length) {
        rootLabel.text(label);
      } else {
        rootBtn.text(label);
      }
    }

    if (prefs.notify_enabled !== undefined) {
      $("#myNotifyToggle").prop("checked", prefs.notify_enabled);
    }

  });

  document.addEventListener("DOMContentLoaded", startWebSocket);

  $("#pickNewBranchMapBtn").on("click", function () {
    openBranchMapPicker("new");
  });
  $("#pickSelectedBranchMapBtn").on("click", function () {
    openBranchMapPicker("selected");
  });
  $("#openNewBranchModalBtn").on("click", function () {
    openNewBranchModal();
  });
  $("#openEditBranchModalBtn").on("click", function () {
    openEditBranchModal();
  });
  $("#closeNewBranchModalBtn").on("click", function () {
    closeNewBranchModal();
  });
  $("#closeEditBranchModalBtn").on("click", function () {
    closeEditBranchModal();
  });
  $("#newBranchModal").on("click", function (e) {
    if (e.target && e.target.id === "newBranchModal") closeNewBranchModal();
  });
  $("#editBranchModal").on("click", function (e) {
    if (e.target && e.target.id === "editBranchModal") closeEditBranchModal();
  });
  $("#branchMapCloseBtn, #branchMapCancelBtn").on("click", closeBranchMapPicker);
  $("#branchMapSaveBtn").on("click", saveBranchMapPoint);
  $("#branchMapModal").on("click", function (e) {
    if (e.target && e.target.id === "branchMapModal") closeBranchMapPicker();
  });
  $("#newBranchRegion").on("change", function () {
    renderCitySelect("new", $(this).val() || "");
    clearBranchValidation("new");
    clearBranchFieldError("new", "Region");
    clearBranchFieldError("new", "City");
    clearBranchFieldError("new", "District");
  });
  $("#editBranchRegion").on("change", function () {
    renderCitySelect("edit", $(this).val() || "");
    clearBranchValidation("edit");
    clearBranchFieldError("edit", "Region");
    clearBranchFieldError("edit", "City");
    clearBranchFieldError("edit", "District");
  });
  $("#newBranchCity").on("change", function () {
    renderDistrictSelect("new", $(this).val() || "");
    clearBranchFieldError("new", "City");
    clearBranchFieldError("new", "District");
  });
  $("#editBranchCity").on("change", function () {
    renderDistrictSelect("edit", $(this).val() || "");
    clearBranchFieldError("edit", "City");
    clearBranchFieldError("edit", "District");
  });
  $("#newBranchDistrict").on("change", function () {
    clearBranchValidation("new");
    clearBranchFieldError("new", "District");
  });
  $("#editBranchDistrict").on("change", function () {
    clearBranchValidation("edit");
    clearBranchFieldError("edit", "District");
  });
  $("#newBranchCity, #newBranchName, #newBranchLatitude, #newBranchLongitude").on("input change", function () {
    clearBranchValidation("new");
    const id = String(this.id || "");
    if (id.includes("Name")) clearBranchFieldError("new", "Name");
    if (id.includes("City")) clearBranchFieldError("new", "City");
    if (id.includes("Latitude") || id.includes("Longitude")) clearBranchFieldError("new", "Location");
  });
  $("#editBranchCity, #editBranchName, #editBranchLatitude, #editBranchLongitude").on("input change", function () {
    clearBranchValidation("edit");
    const id = String(this.id || "");
    if (id.includes("Name")) clearBranchFieldError("edit", "Name");
    if (id.includes("City")) clearBranchFieldError("edit", "City");
    if (id.includes("Latitude") || id.includes("Longitude")) clearBranchFieldError("edit", "Location");
  });
  $("#editBranchImageInput").on("change", function () {
    uploadBranchImages("edit");
  });
  $("#newBranchImageInput").on("change", function () {
    uploadBranchImages("new");
  });


});


$("#myNotifyToggle").on("change", function () {
  const enabled = this.checked;

  apiPost("/users/me/notify", {
    enabled: enabled
  }).done(function () {
    alert(t("settings_saved"));
  });
});

function toggleUserNotifications() {
  const userId = $("#userSelect").val();
  if (!userId) {
    alert(t("select_user"));
    return;
  }

  const enabled = $("#userNotifyToggle").is(":checked");

  apiPost(`/users/admin/users/${userId}/notify`, {
    enabled: enabled
  }).done(function () {
    alert(t("settings_saved"));
  });
}

$(document).on("change", "#userSelect", function () {
  const userId = $(this).val();
  if (!userId) return;

  apiGet(`/users/${userId}`).done(function (u) {
    $("#userNotifyToggle").prop(
      "checked",
      u.notify_enabled === true
    );
  });
});


function loadUsers() {
  apiGet("/users")
    .done(function (users) {
      const $u = $("#userSelect").empty();

      if (!users.length) {
        $u.append(`<option>${t("no_users")}</option>`);
        return;
      }

      users.forEach(u => {
        $u.append(`
          <option value="${u.id}">
            ${u.username}
          </option>
        `);
      });
    });
}



function setActiveLangUI(lang) {
  $(".lang-btn").removeClass("active");
  $("#lang-" + lang).addClass("active");
} 

/* ================= BRANCHES ================= */

function loadBranches() {
  renderRegionSelects();
  apiGet("/branches", {})
    .done(function (rows) {

      BRANCHES = rows || [];

      const $select = $("#branchSelect");
      $select.empty();

      if (!BRANCHES.length) {
        $select.append(`<option>${t("no_branches")}</option>`);
        return;
      }

      BRANCHES.forEach(b => {
        $select.append(`
          <option value="${b.id}">
            ${b.id} - ${b.name}
          </option>
        `);
      });

      // вњ… restore selected branch
      if (CURRENT_BRANCH) {
        $select.val(CURRENT_BRANCH);
      }
      fillBranchContactInputs();
    });
}

function openUserManagerModal() {
  $("#userManageModal").removeClass("hidden");
  loadUsers();
}

function closeUserManagerModal() {
  $("#userManageModal").addClass("hidden");
}

function fillBranchContactInputs() {
  const bid = Number($("#branchSelect").val() || 0);
  const row = BRANCHES.find((b) => Number(b.id) === bid) || {};
  $("#editBranchName").val(row.name || "");
  $("#editBranchAddress").val(row.address || "");
  $("#editBranchLatitude").val(row.latitude ?? "");
  $("#editBranchLongitude").val(row.longitude ?? "");
  $("#editBranchPhone").val(row.contact_phone || "");
  $("#editBranchTelegram").val(row.contact_telegram || "");
  const regionSlug = (row.region_slug || "").trim();
  const cityName = row.city_name || "";
  $("#editBranchRegion").val(regionSlug);
  renderCitySelect("edit", regionSlug, cityName);
  renderDistrictSelect("edit", cityName, row.district_name || "");
}

function branchUiText(key) {
  const uz = CURRENT_LANG === "uz";
  const map = {
    create_first: uz ? "Avval filial yarating." : "Сначала создайте филиал.",
    upload_failed: uz ? "Rasm yuklashda xatolik." : "Ошибка загрузки фото.",
    max_three: uz ? "Maksimal 3 ta rasm ruxsat etiladi." : "Максимум 3 фото.",
    no_images: uz ? "Rasm yo'q." : "Нет фото.",
    set_cover: uz ? "Asosiy qilish" : "Сделать основным",
    cover: uz ? "Asosiy rasm" : "Основное",
    delete: uz ? "O'chirish" : "Удалить",
    delete_confirm: uz ? "Rasmni o'chirasizmi?" : "Удалить фото?",
    created_upload: uz ? "Filial yaratildi. Endi rasmlarni yuklashingiz mumkin." : "Филиал создан. Теперь можно загрузить фото."
  };
  return map[key] || key;
}

function getModalBranchId(mode) {
  if (mode === "edit") {
    return Number($("#branchSelect").val() || 0);
  }
  return Number(NEW_BRANCH_CREATED_ID || 0);
}

function setBranchImageUploaderEnabled(mode, enabled) {
  const inputId = mode === "edit" ? "#editBranchImageInput" : "#newBranchImageInput";
  $(inputId).prop("disabled", !enabled);
  if (mode === "new") {
    $("#newBranchImagesHelp").text(
      enabled
        ? (CURRENT_LANG === "uz" ? "Maksimal 3 ta rasm. 1 tasi asosiy rasm bo'ladi." : "Максимум 3 фото. Одно фото будет основным.")
        : branchUiText("create_first")
    );
  }
}

function renderBranchImages(mode, images) {
  const listId = mode === "edit" ? "#editBranchImagesList" : "#newBranchImagesList";
  const countId = mode === "edit" ? "#editBranchImagesCount" : "#newBranchImagesCount";
  const $list = $(listId);
  const arr = Array.isArray(images) ? images : [];
  $(countId).text(`${arr.length}/3`);

  if (!arr.length) {
    $list.html(`<div class="branch-images-help">${branchUiText("no_images")}</div>`);
    return;
  }

  $list.empty();
  arr.forEach((img) => {
    const coverLabel = img.is_cover ? branchUiText("cover") : branchUiText("set_cover");
    const card = $(`
      <div class="branch-image-card">
        <img src="${img.image_path}" alt="branch image" loading="lazy">
        <div class="branch-image-actions">
          <button type="button" class="branch-image-cover ${img.is_cover ? "is-cover" : ""}">${coverLabel}</button>
          <button type="button" class="branch-image-delete">${branchUiText("delete")}</button>
        </div>
      </div>
    `);
    card.find(".branch-image-cover").on("click", function () {
      if (img.is_cover) return;
      setBranchImageCover(mode, img.id);
    });
    card.find(".branch-image-delete").on("click", function () {
      deleteBranchImage(mode, img.id);
    });
    $list.append(card);
  });
}

function loadBranchImages(mode) {
  const branchId = getModalBranchId(mode);
  const listId = mode === "edit" ? "#editBranchImagesList" : "#newBranchImagesList";
  if (!branchId) {
    setBranchImageUploaderEnabled(mode, false);
    renderBranchImages(mode, []);
    return;
  }
  setBranchImageUploaderEnabled(mode, true);
  $(listId).html(`<div class="branch-images-help">${t("loading")}...</div>`);
  apiGet(`/branches/admin/${branchId}/images`)
    .done(function (resp) {
      const images = (resp && resp.images) || [];
      renderBranchImages(mode, images);
    })
    .fail(function () {
      renderBranchImages(mode, []);
    });
}

function uploadBranchImages(mode) {
  const branchId = getModalBranchId(mode);
  if (!branchId) {
    alert(branchUiText("create_first"));
    return;
  }
  const input = document.getElementById(mode === "edit" ? "editBranchImageInput" : "newBranchImageInput");
  if (!input || !input.files || !input.files.length) return;

  const form = new FormData();
  Array.from(input.files).forEach((file) => form.append("files", file));

  fetch(`/api2/branches/admin/${branchId}/images`, {
    method: "POST",
    body: form,
    credentials: "include"
  })
    .then(async (res) => {
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = payload.detail || payload.error || branchUiText("upload_failed");
        throw new Error(msg);
      }
      input.value = "";
      loadBranchImages(mode);
      loadBranches();
    })
    .catch((err) => {
      const msg = String((err && err.message) || "");
      if (msg.toLowerCase().includes("maximum")) {
        alert(branchUiText("max_three"));
        return;
      }
      alert(window.translateBackendError ? window.translateBackendError(msg) : msg || branchUiText("upload_failed"));
    });
}

function setBranchImageCover(mode, imageId) {
  const branchId = getModalBranchId(mode);
  if (!branchId || !imageId) return;
  apiPut(`/branches/admin/${branchId}/images/${imageId}/cover`, {})
    .done(function () {
      loadBranchImages(mode);
      loadBranches();
    });
}

function deleteBranchImage(mode, imageId) {
  const branchId = getModalBranchId(mode);
  if (!branchId || !imageId) return;
  if (!confirm(branchUiText("delete_confirm"))) return;
  apiDelete(`/branches/admin/${branchId}/images/${imageId}`, {})
    .done(function () {
      loadBranchImages(mode);
      loadBranches();
    });
}

function openNewBranchModal() {
  NEW_BRANCH_CREATED_ID = null;
  clearBranchValidation("new");
  clearBranchFieldErrors("new");
  renderBranchImages("new", []);
  setBranchImageUploaderEnabled("new", false);
  $("#newBranchModal").addClass("show");
}

function closeNewBranchModal() {
  NEW_BRANCH_CREATED_ID = null;
  clearBranchValidation("new");
  clearBranchFieldErrors("new");
  $("#newBranchModal").removeClass("show");
}

function openEditBranchModal() {
  const bid = Number($("#branchSelect").val() || 0);
  if (!bid) {
    alert(t("select_branch"));
    return;
  }
  fillBranchContactInputs();
  clearBranchValidation("edit");
  clearBranchFieldErrors("edit");
  loadBranchImages("edit");
  $("#editBranchModal").addClass("show");
}

function closeEditBranchModal() {
  clearBranchValidation("edit");
  clearBranchFieldErrors("edit");
  $("#editBranchModal").removeClass("show");
}

function renderRegionSelects() {
  const allLabel = CURRENT_LANG === "uz" ? "Barcha viloyatlar" : "Все области";
  const regionLabel = CURRENT_LANG === "uz" ? "Viloyatni tanlang" : "Выберите область";
  const options = [`<option value="">${regionLabel}</option>`]
    .concat(REGION_OPTIONS.map((r) => `<option value="${r.normalized_name}">${r.name}</option>`))
    .join("");
  $("#newBranchRegion").html(options);
  renderCitySelect("new", ($("#newBranchRegion").val() || "").trim(), "");
  renderDistrictSelect("new", "", "");

  const editOptions = [`<option value="">${allLabel}</option>`]
    .concat(REGION_OPTIONS.map((r) => `<option value="${r.normalized_name}">${r.name}</option>`))
    .join("");
  $("#editBranchRegion").html(editOptions);
  renderCitySelect("edit", ($("#editBranchRegion").val() || "").trim(), "");
  renderDistrictSelect("edit", "", "");
}

function renderCitySelect(mode, regionSlug, selectedCity) {
  const target = mode === "edit" ? "#editBranchCity" : "#newBranchCity";
  const cityLabel = CURRENT_LANG === "uz" ? "Shaharni tanlang" : "Выберите город";
  const allCity = CURRENT_LANG === "uz" ? "Barcha shaharlar" : "Все города";
  const region = String(regionSlug || "").trim();
  const cities = region ? (REGION_CITY_OPTIONS[region] || []) : [];
  const base = mode === "edit" ? [`<option value="">${allCity}</option>`] : [`<option value="">${cityLabel}</option>`];
  const options = base.concat(cities.map((c) => `<option value="${c}">${c}</option>`)).join("");
  $(target).html(options);
  if (selectedCity && cities.includes(selectedCity)) {
    $(target).val(selectedCity);
  } else {
    $(target).val("");
  }
  $(target).prop("disabled", !region || !cities.length);
  renderDistrictSelect(mode, $(target).val() || "", "");
}

function renderDistrictSelect(mode, cityName, selectedDistrict) {
  const target = mode === "edit" ? "#editBranchDistrict" : "#newBranchDistrict";
  const city = String(cityName || "").trim();
  const districts = city ? (CITY_DISTRICT_OPTIONS[city] || []) : [];
  const labelAny = CURRENT_LANG === "uz" ? "Barcha tumanlar" : "Все районы";
  const labelPick = CURRENT_LANG === "uz" ? "Tumanni tanlang" : "Выберите район";
  const base = mode === "edit" ? [`<option value="">${labelAny}</option>`] : [`<option value="">${labelPick}</option>`];
  const options = base.concat(districts.map((d) => `<option value="${d}">${d}</option>`)).join("");
  $(target).html(options);
  if (selectedDistrict && districts.includes(selectedDistrict)) {
    $(target).val(selectedDistrict);
  } else {
    $(target).val("");
  }
  $(target).prop("disabled", !city || !districts.length);
}

function showBranchValidation(mode, message) {
  const target = mode === "edit" ? "#editBranchValidation" : "#newBranchValidation";
  const $el = $(target);
  if (!$el.length) return;
  $el.text(String(message || "")).removeClass("hidden");
}

function clearBranchValidation(mode) {
  const target = mode === "edit" ? "#editBranchValidation" : "#newBranchValidation";
  const $el = $(target);
  if (!$el.length) return;
  $el.text("").addClass("hidden");
}

function showBranchFieldError(mode, field, message) {
  const target = `#${mode}Branch${field}Error`;
  const $el = $(target);
  if (!$el.length) return;
  $el.text(String(message || "")).removeClass("hidden");
}

function clearBranchFieldError(mode, field) {
  const target = `#${mode}Branch${field}Error`;
  const $el = $(target);
  if (!$el.length) return;
  $el.text("").addClass("hidden");
}

function clearBranchFieldErrors(mode) {
  $(`#${mode}BranchNameError`).text("").addClass("hidden");
  $(`#${mode}BranchRegionError`).text("").addClass("hidden");
  $(`#${mode}BranchCityError`).text("").addClass("hidden");
  $(`#${mode}BranchDistrictError`).text("").addClass("hidden");
  $(`#${mode}BranchLocationError`).text("").addClass("hidden");
}

function getRegionBySlug(slug) {
  const s = String(slug || "").trim().toLowerCase();
  return REGION_OPTIONS.find((r) => r.normalized_name.toLowerCase() === s) || null;
}

function parseCoord(v) {
  const n = parseFloat(String(v ?? "").trim());
  return Number.isFinite(n) ? n : null;
}

function getMapStartPoint() {
  if (BRANCH_MAP_MODE === "new") {
    const lat = parseCoord($("#newBranchLatitude").val());
    const lon = parseCoord($("#newBranchLongitude").val());
    if (lat !== null && lon !== null) return { lat, lon };
  } else {
    const lat = parseCoord($("#editBranchLatitude").val());
    const lon = parseCoord($("#editBranchLongitude").val());
    if (lat !== null && lon !== null) return { lat, lon };
  }
  return { lat: 41.3111, lon: 69.2797 };
}

function setBranchMapPoint(lat, lon) {
  BRANCH_MAP_POINT = { lat: Number(lat), lon: Number(lon) };
  if (!BRANCH_MAP_OBJ) return;
  if (!BRANCH_MAP_MARKER) {
    BRANCH_MAP_MARKER = L.marker([lat, lon]).addTo(BRANCH_MAP_OBJ);
  } else {
    BRANCH_MAP_MARKER.setLatLng([lat, lon]);
  }
}

function openBranchMapPicker(mode) {
  if (!window.L) {
    alert(CURRENT_LANG === "uz" ? "Xarita yuklanmadi" : "Карта не загрузилась");
    return;
  }
  BRANCH_MAP_MODE = mode === "selected" ? "selected" : "new";
  $("#branchMapModalTitle").text(
    BRANCH_MAP_MODE === "new"
      ? (CURRENT_LANG === "uz" ? "Yangi filial uchun joy tanlang" : "Выберите точку для нового филиала")
      : (CURRENT_LANG === "uz" ? "Tanlangan filial uchun joy tanlang" : "Выберите точку для выбранного филиала")
  );
  $("#branchMapModal").addClass("show");

  const start = getMapStartPoint();
  BRANCH_MAP_POINT = { lat: start.lat, lon: start.lon };

  if (!BRANCH_MAP_OBJ) {
    BRANCH_MAP_OBJ = L.map("branchMapCanvas", { zoomControl: true }).setView([start.lat, start.lon], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap"
    }).addTo(BRANCH_MAP_OBJ);
    BRANCH_MAP_OBJ.on("click", function (e) {
      setBranchMapPoint(e.latlng.lat, e.latlng.lng);
    });
  } else {
    BRANCH_MAP_OBJ.setView([start.lat, start.lon], 13);
    setTimeout(() => BRANCH_MAP_OBJ.invalidateSize(), 50);
  }

  setBranchMapPoint(start.lat, start.lon);
}

function closeBranchMapPicker() {
  $("#branchMapModal").removeClass("show");
}

function saveBranchMapPoint() {
  if (!BRANCH_MAP_POINT) {
    alert(CURRENT_LANG === "uz" ? "Xaritada nuqta tanlang" : "Выберите точку на карте");
    return;
  }
  const lat = Number(BRANCH_MAP_POINT.lat.toFixed(7));
  const lon = Number(BRANCH_MAP_POINT.lon.toFixed(7));

  if (BRANCH_MAP_MODE === "new") {
    $("#newBranchLatitude").val(String(lat));
    $("#newBranchLongitude").val(String(lon));
    closeBranchMapPicker();
    return;
  }
  $("#editBranchLatitude").val(String(lat));
  $("#editBranchLongitude").val(String(lon));
  closeBranchMapPicker();
}

/* вњ… SINGLE change handler (ONLY ONE) */
$(document).on("change", "#branchSelect", function () {
  const branchId = Number($(this).val());
  if (!branchId) return;

  // вњ… update frontend immediately
  CURRENT_BRANCH = branchId;

  $("#branchSelect").val(branchId);

  localStorage.setItem("CURRENT_BRANCH", branchId);
  fillBranchContactInputs();

  // persist backend
  setCurrentBranch(branchId);
});

function createBranch() {
  clearBranchValidation("new");
  clearBranchFieldErrors("new");
  const name = $("#newBranchName").val().trim();
  const address = $("#newBranchAddress").val().trim();
  const latitude = $("#newBranchLatitude").val().trim();
  const longitude = $("#newBranchLongitude").val().trim();
  const regionSlug = ($("#newBranchRegion").val() || "").trim();
  const regionObj = getRegionBySlug(regionSlug);
  const cityName = ($("#newBranchCity").val() || "").trim();
  const districtName = ($("#newBranchDistrict").val() || "").trim();
  const contactPhone = $("#newBranchPhone").val().trim();
  const contactTelegram = $("#newBranchTelegram").val().trim();

  if (!name) {
    showBranchFieldError("new", "Name", t("branch_name_required"));
    return;
  }
  if (!regionSlug || !regionObj) {
    showBranchFieldError("new", "Region", CURRENT_LANG === "uz" ? "Viloyat majburiy." : "Область обязательна.");
    return;
  }
  if (!cityName) {
    showBranchFieldError("new", "City", CURRENT_LANG === "uz" ? "Shahar majburiy." : "Город обязателен.");
    return;
  }

  const latNum = parseFloat(latitude);
  const lonNum = parseFloat(longitude);
  if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) {
    showBranchFieldError("new", "Location", CURRENT_LANG === "uz"
      ? "Filial lokatsiyasi majburiy. Xaritadan joy tanlang."
      : "Локация филиала обязательна. Выберите точку на карте.");
    return;
  }
  if (latNum < -90 || latNum > 90 || lonNum < -180 || lonNum > 180) {
    showBranchFieldError("new", "Location", CURRENT_LANG === "uz"
      ? "Latitude/longitude noto'g'ri."
      : "Неверные latitude/longitude.");
    return;
  }

  apiPost("/branches/branches-admin", { 
      name: name,
      address: address || null,
      latitude: latNum,
      longitude: lonNum,
      region_slug: regionSlug || null,
      region_name: regionObj ? regionObj.name : null,
      city_name: cityName || null,
      city_slug: cityName ? (window.toCitySlug ? window.toCitySlug(cityName) : cityName.toLowerCase()) : null,
      district_name: districtName || null,
      district_slug: districtName ? (window.toCitySlug ? window.toCitySlug(districtName) : districtName.toLowerCase()) : null,
      contact_phone: contactPhone || null,
      contact_telegram: contactTelegram || null
    }).done(function () {
      NEW_BRANCH_CREATED_ID = Number((arguments[0] && arguments[0].branch_id) || 0) || null;
      if (NEW_BRANCH_CREATED_ID) {
        CURRENT_BRANCH = NEW_BRANCH_CREATED_ID;
        $("#branchSelect").val(NEW_BRANCH_CREATED_ID);
      }
      clearBranchValidation("new");
      clearBranchFieldErrors("new");
      loadBranches();
      loadBranchImages("new");
      alert(branchUiText("created_upload"));
    }).fail(function (xhr) {
      const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.message)) || (CURRENT_LANG === "uz" ? "Saqlashda xato." : "Ошибка при сохранении.");
      showBranchValidation("new", msg);
    });
}

function saveBranchContacts() {
  clearBranchValidation("edit");
  clearBranchFieldErrors("edit");
  const branchId = Number($("#branchSelect").val() || 0);
  if (!branchId) {
    alert(t("select_branch"));
    return;
  }

  const name = ($("#editBranchName").val() || "").trim();
  const address = ($("#editBranchAddress").val() || "").trim();
  const regionSlug = ($("#editBranchRegion").val() || "").trim();
  const regionObj = getRegionBySlug(regionSlug);
  const cityName = ($("#editBranchCity").val() || "").trim();
  const districtName = ($("#editBranchDistrict").val() || "").trim();
  const latRaw = ($("#editBranchLatitude").val() || "").trim();
  const lonRaw = ($("#editBranchLongitude").val() || "").trim();
  if (!name) {
    showBranchFieldError("edit", "Name", t("branch_name_required"));
    return;
  }
  if (!regionSlug || !regionObj) {
    showBranchFieldError("edit", "Region", CURRENT_LANG === "uz" ? "Viloyat majburiy." : "Область обязательна.");
    return;
  }
  if (!cityName) {
    showBranchFieldError("edit", "City", CURRENT_LANG === "uz" ? "Shahar majburiy." : "Город обязателен.");
    return;
  }
  const latNum = parseFloat(latRaw);
  const lonNum = parseFloat(lonRaw);
  if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) {
    showBranchFieldError("edit", "Location", CURRENT_LANG === "uz"
      ? "Filial lokatsiyasi majburiy. Xaritadan joy tanlang."
      : "Локация филиала обязательна. Выберите точку на карте.");
    return;
  }

  apiPut(`/branches/admin/${branchId}`, {
    name: name,
    address: address || null,
    latitude: latNum,
    longitude: lonNum,
    region_slug: regionSlug,
    region_name: regionObj.name,
    city_name: cityName,
    city_slug: window.toCitySlug ? window.toCitySlug(cityName) : cityName.toLowerCase(),
    district_name: districtName || null,
    district_slug: districtName ? (window.toCitySlug ? window.toCitySlug(districtName) : districtName.toLowerCase()) : null,
    contact_phone: ($("#editBranchPhone").val() || "").trim() || null,
    contact_telegram: ($("#editBranchTelegram").val() || "").trim() || null
  }).done(function () {
    clearBranchValidation("edit");
    clearBranchFieldErrors("edit");
    alert(t("branch_updated"));
    closeEditBranchModal();
    loadBranches();
  }).fail(function (xhr) {
    const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.message)) || (CURRENT_LANG === "uz" ? "Saqlashda xato." : "Ошибка при сохранении.");
    showBranchValidation("edit", msg);
  });
}



function renameBranch() {
  const branchId = $("#branchSelect").val();
  const name = $("#renameBranchName").val().trim();

  if (!branchId || !name) {
    alert(t("select_a_branch_and_enter_new_name"));
    return;
  }

  apiPut(`/branches/${branchId}`, { name })
    .done(function () {
      $("#renameBranchName").val("");
      loadBranches();
      alert(t("branch_updated"));
    });
}

function deleteBranch() {
  const branchId = $("#branchSelect").val();
  if (!branchId) return;

  if (!confirm(t("delete_branch_confirm"))) return;

  apiDelete(`/branches/admin/${branchId}`)
    .done(function () {
      closeEditBranchModal();
      loadBranches();
      alert(t("branch_deleted"));
    });
}




/* ================= PASSWORD ================= */

function changePassword() {
  const current = $("#oldPassword").val();
  const password = $("#newPassword").val();
  const confirm = $("#confirmPassword").val();

  if (!current || !password || !confirm) {
    alert(t("fill_all_fields"));
    return;
  }

  if (password !== confirm) {
    alert(t("passwords_do_not_match"));
    return;
  }

  apiPost("/settings/change-password", {
    current_password: current,
    new_password: password
  }).done(function () {
    alert(t("password_changed_successfully"));
    $("#oldPassword, #newPassword, #confirmPassword").val("");
  });
}

/* ================= LANGUAGE ================= */

function setLanguage(lang) {

  if (lang === CURRENT_LANG) return;

  // рџ”„ UI feedback
  $(".lang-btn").prop("disabled", true);
  $("#lang-" + lang).text(t("lang_changing") + "...");

  apiPost("/settings/language", { language: lang })
    .done(function (res) {

      // рџ”Ґ replace JWT
      fetch("/auth/replace-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access_token: res.access_token
        })
      }).then(() => {

        const url = window.location.pathname + "?lang=" + lang + "&t=" + Date.now();
        window.location.href = url;


      });

    });
}



function setCurrentBranch(branchId) {
  apiPost("/settings/set-branch", {
    branch_id: branchId
  }).done(function (res) {

    // рџ”Ґ replace JWT in Flask session
    fetch("/auth/replace-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        access_token: res.access_token
      })
    }).then(() => {
      // location.reload();
      window.location.href = "/settings?t=" + Date.now();

    });

  });
}


function createUser() {
  const username = $("#newUsername").val().trim();
  const telegramId = $("#newUserTelegram").val().trim();
  const password = $("#newUserPassword").val().trim();

  if (!username || !password) {
    alert(t("fill_all_fields"));
    return;
  }

  apiPost("/users", {
    username: username,
    password: password,
    telegram_id: telegramId || null   // вњ… optional
  }).done(function () {

    $("#newUsername").val("");
    $("#newUserTelegram").val("");
    $("#newUserPassword").val("");

    alert(t("user_created_successfully"));
    loadUsers();
  });
}


function deleteUser() {
  const userId = $("#userSelect").val();

  if (!userId) {
    alert(t("select_user"));
    return;
  }

  if (!confirm(t("delete_user_confirm"))) return;

  apiDelete(`/users/${userId}`)
    .done(function () {
      alert(t("user_deleted"));

      // рџ”„ reload users
      loadUsers();
    });
}


function openUserBranchModal() {
  const userId = $("#userSelect").val();
  if (!userId) {
    alert(t("select_user"));
    return;
  }

  SELECTED_USER_ID = Number(userId);
  $("#userBranchModal").removeClass("hidden");

  // 1пёЏвѓЈ load assigned branches FIRST
  apiGet(`/users/${SELECTED_USER_ID}/branches`).done(function (assigned) {
    const assignedIds = (assigned || []).map(b => Number(b.id));
    SELECTED_USER_ASSIGNED_BRANCH_IDS = assignedIds.slice();

    // 2пёЏвѓЈ load all branches
    apiGet("/branches").done(function (branches) {
      const box = $("#branchCheckboxList").empty();

      branches.forEach(b => {
        const checked = assignedIds.includes(b.id) ? "checked" : "";

        box.append(`
          <label class="flex items-center gap-2">
            <input type="checkbox"
                   class="branch-check"
                   value="${b.id}"
                   ${checked}>
            <span>${b.name}</span>
          </label>
        `);
      });
    });
  });
}



function saveUserBranches() {
  const checked = $(".branch-check:checked").map(function () {
    return Number(this.value);
  }).get();

  const prev = new Set(SELECTED_USER_ASSIGNED_BRANCH_IDS || []);
  const now = new Set(checked);
  const toAdd = checked.filter(branchId => !prev.has(branchId));
  const toRemove = (SELECTED_USER_ASSIGNED_BRANCH_IDS || []).filter(branchId => !now.has(branchId));

  const requests = [];

  toAdd.forEach(branchId => {
    requests.push(
      apiPost(`/branches/${branchId}/assign-user`, {
        user_id: SELECTED_USER_ID
      })
    );
  });

  toRemove.forEach(branchId => {
    requests.push(
      apiDelete(`/branches/${branchId}/users/${SELECTED_USER_ID}`)
    );
  });

  if (!requests.length) {
    alert(t("saved"));
    closeUserBranchModal();
    return;
  }

  $.when.apply($, requests).done(() => {
    SELECTED_USER_ASSIGNED_BRANCH_IDS = checked.slice();
    alert(t("saved"));
    closeUserBranchModal();
  });
}


function closeUserBranchModal() {
  $("#userBranchModal").addClass("hidden");
}

function loadPrepaymentSettings() {
  apiGet("/settings/booking-prepayment")
    .done(function (cfg) {
      $("#prepayEnabled").prop("checked", !!cfg.enabled);
      $("#prepayMode").val(cfg.mode || "percent");
      $("#prepayValue").val(cfg.value ?? 0);
    })
    .fail(function () {
      // silently ignore for non-admins or older backend
    });
}

function savePrepaymentSettings() {
  const enabled = $("#prepayEnabled").is(":checked");
  const mode = $("#prepayMode").val() || "percent";
  const value = Number($("#prepayValue").val() || 0);

  apiPost("/settings/booking-prepayment", {
    enabled: enabled,
    mode: mode,
    value: value
  }).done(function () {
    alert(t("settings_saved"));
  });
}


function loadRootSystemExpiry() {
  // raw ajax to avoid noisy global errors for non-root admins
  $.ajax({
    url: "/api2/root/system-expiry",
    method: "GET",
    dataType: "json"
  })
    .done(function (res) {
      IS_ROOT_ADMIN = true;
      $(".root-only").removeClass("hidden");

      const raw = res && res.expires_at ? String(res.expires_at) : "";
      if (!raw) {
        $("#appExpiryDate").val("");
        return;
      }

      const d = raw.split("T")[0];
      $("#appExpiryDate").val(d);
    })
    .fail(function () {
      IS_ROOT_ADMIN = false;
      $(".root-only").addClass("hidden");
    });
}

window.saveSystemExpiry = function () {
  if (!IS_ROOT_ADMIN) return;

  const d = ($("#appExpiryDate").val() || "").trim();
  if (!d) {
    alert("Please select expiry date");
    return;
  }

  const expiresAt = `${d}T23:59:59`;

  apiPost("/root/system-expiry", {
    expires_at: expiresAt
  }).done(function () {
    alert("Expiry date saved");
    loadRootSystemExpiry();
  });
};

window.clearSystemExpiry = function () {
  if (!IS_ROOT_ADMIN) return;

  apiPost("/root/system-expiry", {
    expires_at: null
  }).done(function () {
    $("#appExpiryDate").val("");
    alert("Expiry cleared");
    loadRootSystemExpiry();
  });
};



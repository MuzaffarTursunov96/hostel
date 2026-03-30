(function () {
  const tr = {
    uz: {
      title: "Hotel va Hostel katalogi",
      subtitle: "Rasm, reyting va joylashuv bo'yicha mos variantni tanlang.",
      search_ph: "Nom yoki manzil bo'yicha qidirish...",
      all_room_types: "Barcha xona turlari",
      all_ratings: "Barcha reytinglar",
      refresh: "Yangilash",
      clear_filters: "Filterni bekor qilish",
      show_filters: "Filterni ko'rsatish",
      hide_filters: "Filterni yopish",
      photos: "Rasmlar",
      details: "Batafsil",
      rate: "Baholash",
      report: "Xabar yuborish",
      booking: "Bron ariza",
      no_data: "Mos obyekt topilmadi",
      no_photo: "Rasm yo'q",
      reviews: "baho",
      photo_count: "rasm",
      from_price: "Narx",
      by_agreement: "Kelishiladi",
      min_price: "Min narx",
      max_price: "Max narx",
      min_price_ph: "Min narx",
      max_price_ph: "Max narx",
      room_types: "Xona turlari",
      bed_info: "Yotoqlar",
      bed_single: "Bir kishilik",
      bed_double: "Ikki kishilik",
      bed_child: "Bolalar",
      rating_prompt: "1 dan 5 gacha baho kiriting",
      comment_prompt: "Qisqa izoh (ixtiyoriy)",
      saved: "Rahmat, bahoyingiz saqlandi",
      room_label: "Xona/Yotoq",
      room_label_ph: "Masalan: 203 xona, 2-kravat",
      report_message: "Xabar",
      report_message_ph: "Xona holati haqida yozing...",
      booking_message_ph: "Qo'shimcha izoh...",
      contact_optional: "Aloqa (ixtiyoriy)",
      contact_ph: "+998...",
      photo_optional: "Rasm (ixtiyoriy)",
      send_report: "Yuborish",
      report_saved: "Xabar adminlarga yuborildi",
      send_booking_request: "Bron ariza yuborish",
      booking_saved: "Bron arizangiz yuborildi",
      full_name_optional: "Ism (ixtiyoriy)",
      phone_required: "Telefon raqam (majburiy)",
      room_or_bed: "Xona yoki yotoq raqami",
      checkin_date: "Kelish sanasi",
      checkout_date: "Ketish sanasi",
      details_rooms: "Xonalar",
      details_beds: "Kravatlar",
      details_price: "Narx",
      available_beds_label: "Bo'sh o'rin",
      room_status: "Holat",
      status_free: "Bo'sh",
      status_partial: "Qisman band",
      status_full: "To'liq band",
      details_none: "Ma'lumot topilmadi",
      call: "Qo'ng'iroq",
      telegram: "Telegram",
      nearest_by_gps: "GPS bo'yicha yaqinlarini topish",
      any_distance: "Masofa: hammasi",
      location_denied: "Joylashuvga ruxsat berilmadi",
      location_unavailable: "GPS ma'lumoti olinmadi",
      distance_km: "km"
    },
    ru: {
      title: "Каталог Hotel и Hostel",
      subtitle: "Выберите вариант по фото, рейтингу и локации.",
      search_ph: "Поиск по названию или адресу...",
      all_room_types: "Все типы комнат",
      all_ratings: "Все рейтинги",
      refresh: "Обновить",
      clear_filters: "Сбросить фильтры",
      show_filters: "Показать фильтры",
      hide_filters: "Скрыть фильтры",
      photos: "Фото",
      details: "Подробнее",
      rate: "Оценить",
      report: "Отправить сообщение",
      booking: "Заявка на бронь",
      no_data: "Подходящие объекты не найдены",
      no_photo: "Нет фото",
      reviews: "оценок",
      photo_count: "фото",
      from_price: "Цена",
      by_agreement: "Договорная",
      min_price: "Мин цена",
      max_price: "Макс цена",
      min_price_ph: "Мин цена",
      max_price_ph: "Макс цена",
      room_types: "Типы комнат",
      bed_info: "Кровати",
      bed_single: "Одноместные",
      bed_double: "Двухместные",
      bed_child: "Детские",
      rating_prompt: "Введите оценку от 1 до 5",
      comment_prompt: "Короткий комментарий (необязательно)",
      saved: "Спасибо, ваша оценка сохранена",
      room_label: "Комната/Кровать",
      room_label_ph: "Например: комната 203, кровать 2",
      report_message: "Сообщение",
      report_message_ph: "Опишите состояние комнаты...",
      booking_message_ph: "Дополнительный комментарий...",
      contact_optional: "Контакт (необязательно)",
      contact_ph: "+998...",
      photo_optional: "Фото (необязательно)",
      send_report: "Отправить",
      report_saved: "Сообщение отправлено администраторам",
      send_booking_request: "Отправить заявку на бронь",
      booking_saved: "Ваша заявка на бронь отправлена",
      full_name_optional: "Имя (необязательно)",
      phone_required: "Телефон (обязательно)",
      room_or_bed: "Комната или номер кровати",
      checkin_date: "Дата заезда",
      checkout_date: "Дата выезда",
      details_rooms: "Комнаты",
      details_beds: "Кровати",
      details_price: "Цена",
      available_beds_label: "Свободно мест",
      room_status: "Статус",
      status_free: "Свободно",
      status_partial: "Частично занято",
      status_full: "Полностью занято",
      details_none: "Данные не найдены",
      call: "Позвонить",
      telegram: "Telegram",
      nearest_by_gps: "Найти ближайшие по GPS",
      any_distance: "Расстояние: все",
      location_denied: "Нет доступа к геолокации",
      location_unavailable: "Не удалось получить GPS",
      distance_km: "км"
    }
  };

  let lang = localStorage.getItem("hms_lang") === "ru" ? "ru" : "uz";
  let rows = [];
  let userGeo = null;

  const cardsEl = document.getElementById("cards");
  const filtersPanelEl = document.getElementById("filtersPanel");
  const toggleFiltersBtnEl = document.getElementById("toggleFiltersBtn");
  const toggleFiltersTextEl = document.getElementById("toggleFiltersText");
  const toggleFiltersIconEl = toggleFiltersBtnEl ? toggleFiltersBtnEl.querySelector(".filter-toggle-icon") : null;
  const searchEl = document.getElementById("searchInput");
  const roomTypeEl = document.getElementById("roomTypeFilter");
  const ratingEl = document.getElementById("ratingFilter");
  const refreshEl = document.getElementById("refreshBtn");
  const clearFiltersBtnEl = document.getElementById("clearFiltersBtn");
  const findNearestBtnEl = document.getElementById("findNearestBtn");
  const distanceFilterEl = document.getElementById("distanceFilter");
  const priceMinInputEl = document.getElementById("priceMinInput");
  const priceMaxInputEl = document.getElementById("priceMaxInput");
  const priceMinRangeEl = document.getElementById("priceMinRange");
  const priceMaxRangeEl = document.getElementById("priceMaxRange");
  const priceMinLabelEl = document.getElementById("priceMinLabel");
  const priceMaxLabelEl = document.getElementById("priceMaxLabel");
  let priceBounds = { min: 0, max: 10000000 };
  let filtersOpen = false;

  const modalEl = document.getElementById("galleryModal");
  const galleryEl = document.getElementById("galleryGrid");
  const galleryTitleEl = document.getElementById("galleryTitle");
  const closeGalleryEl = document.getElementById("closeGallery");

  const reportModalEl = document.getElementById("reportModal");
  const closeReportEl = document.getElementById("closeReport");
  const reportTitleEl = document.getElementById("reportTitle");
  const reportFormEl = document.getElementById("reportForm");
  const reportBranchIdEl = document.getElementById("reportBranchId");
  const reportRoomLabelEl = document.getElementById("reportRoomLabel");
  const reportMessageEl = document.getElementById("reportMessage");
  const reportContactEl = document.getElementById("reportContact");
  const reportPhotoEl = document.getElementById("reportPhoto");

  const detailsModalEl = document.getElementById("detailsModal");
  const detailsTitleEl = document.getElementById("detailsTitle");
  const detailsBodyEl = document.getElementById("detailsBody");
  const closeDetailsEl = document.getElementById("closeDetails");

  const bookingModalEl = document.getElementById("bookingModal");
  const bookingTitleEl = document.getElementById("bookingTitle");
  const closeBookingEl = document.getElementById("closeBooking");
  const bookingFormEl = document.getElementById("bookingForm");
  const bookingBranchIdEl = document.getElementById("bookingBranchId");
  const bookingNameEl = document.getElementById("bookingName");
  const bookingPhoneEl = document.getElementById("bookingPhone");
  const bookingRoomBedEl = document.getElementById("bookingRoomBed");
  const bookingCheckinEl = document.getElementById("bookingCheckin");
  const bookingCheckoutEl = document.getElementById("bookingCheckout");
  const bookingMessageEl = document.getElementById("bookingMessage");

  function t(key) {
    return (tr[lang] && tr[lang][key]) || key;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function fmtPrice(v) {
    if (v === null || v === undefined || String(v).trim() === "") return t("by_agreement");
    return `${Number(v).toLocaleString()} ${lang === "ru" ? "сум" : "so'm"}`;
  }

  function starsText(avg) {
    const v = Math.max(0, Math.min(5, Number(avg) || 0));
    const full = Math.round(v);
    return "★".repeat(full) + "☆".repeat(5 - full);
  }

  function fmtMinMaxPrice(minPrice, maxPrice) {
    if (minPrice === null || minPrice === undefined) return t("by_agreement");
    if (maxPrice === null || maxPrice === undefined) {
      return `${t("min_price")}: ${fmtPrice(minPrice)}`;
    }
    if (Number(minPrice) === Number(maxPrice)) {
      return `${t("min_price")}: ${fmtPrice(minPrice)} | ${t("max_price")}: ${fmtPrice(maxPrice)}`;
    }
    return `${t("min_price")}: ${fmtPrice(minPrice)} | ${t("max_price")}: ${fmtPrice(maxPrice)}`;
  }

  function fmtBedBreakdown(total, singleCount, doubleCount, childCount) {
    return `${total} (${t("bed_single")}: ${singleCount}, ${t("bed_double")}: ${doubleCount}, ${t("bed_child")}: ${childCount})`;
  }

  function occupancyLabel(status) {
    const s = String(status || "").toLowerCase();
    if (s === "full") return t("status_full");
    if (s === "partial") return t("status_partial");
    return t("status_free");
  }

  function toNum(v) {
    if (v === null || v === undefined) return null;
    const s = String(v).trim();
    if (!s) return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }

  function formatNum(n) {
    const v = Number(n || 0);
    return Number.isFinite(v) ? v.toLocaleString() : "0";
  }

  function getSliderBounds() {
    const priced = rows
      .map((r) => [toNum(r.min_price), toNum(r.max_price)])
      .flat()
      .filter((x) => x !== null);
    if (!priced.length) return { min: 0, max: 10000000 };
    const lo = Math.max(0, Math.floor(Math.min(...priced) / 1000) * 1000);
    const hiRaw = Math.ceil(Math.max(...priced) / 1000) * 1000;
    const hi = Math.max(lo + 1000, hiRaw);
    return { min: lo, max: hi };
  }

  function syncPriceLabels() {
    priceMinLabelEl.textContent = formatNum(toNum(priceMinRangeEl.value) || 0);
    priceMaxLabelEl.textContent = formatNum(toNum(priceMaxRangeEl.value) || 0);
  }

  function syncRangeToInput() {
    let minV = toNum(priceMinRangeEl.value) || 0;
    let maxV = toNum(priceMaxRangeEl.value) || 0;
    if (minV > maxV) {
      const t = minV;
      minV = maxV;
      maxV = t;
      priceMinRangeEl.value = String(minV);
      priceMaxRangeEl.value = String(maxV);
    }
    priceMinInputEl.value = String(minV);
    priceMaxInputEl.value = String(maxV);
    syncPriceLabels();
  }

  function syncInputToRange() {
    const bMin = toNum(priceMinRangeEl.min) || priceBounds.min;
    const bMax = toNum(priceMinRangeEl.max) || priceBounds.max;
    const rawMin = String(priceMinInputEl.value || "").trim();
    const rawMax = String(priceMaxInputEl.value || "").trim();
    if (!rawMin && !rawMax) {
      priceMinRangeEl.value = String(bMin);
      priceMaxRangeEl.value = String(bMax);
      syncPriceLabels();
      return;
    }
    let minV = toNum(priceMinInputEl.value);
    let maxV = toNum(priceMaxInputEl.value);
    if (minV === null) minV = bMin;
    if (maxV === null) maxV = bMax;
    minV = Math.max(bMin, Math.min(bMax, minV));
    maxV = Math.max(bMin, Math.min(bMax, maxV));
    if (minV > maxV) maxV = minV;
    priceMinRangeEl.value = String(minV);
    priceMaxRangeEl.value = String(maxV);
    priceMinInputEl.value = String(minV);
    priceMaxInputEl.value = String(maxV);
    syncPriceLabels();
  }

  function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function rowDistance(r) {
    if (!userGeo) return null;
    const lat = toNum(r.latitude);
    const lon = toNum(r.longitude);
    if (lat === null || lon === null) return null;
    return haversineKm(userGeo.lat, userGeo.lon, lat, lon);
  }

  function applyLang() {
    document.documentElement.lang = lang;
    localStorage.setItem("hms_lang", lang);
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-ph]").forEach((el) => {
      el.placeholder = t(el.dataset.ph);
    });
    updateFiltersToggleUi();
    render();
  }

  function updateFiltersToggleUi() {
    if (!toggleFiltersTextEl || !filtersPanelEl) return;
    toggleFiltersTextEl.textContent = filtersOpen ? t("hide_filters") : t("show_filters");
    filtersPanelEl.hidden = !filtersOpen;
    if (toggleFiltersIconEl) {
      toggleFiltersIconEl.textContent = filtersOpen ? "🔽" : "🔎";
    }
  }

  function refreshRoomTypeOptions(selected) {
    const set = new Set();
    rows.forEach((r) => {
      const raw = String(r.room_types || "");
      raw.split(",").map((x) => x.trim()).filter(Boolean).forEach((x) => set.add(x));
    });
    const vals = Array.from(set).sort((a, b) => a.localeCompare(b));
    const current = selected || "";
    roomTypeEl.innerHTML =
      `<option value="" data-i18n="all_room_types">${t("all_room_types")}</option>` +
      vals.map((v) => `<option value="${escapeHtml(v)}"${v === current ? " selected" : ""}>${escapeHtml(v)}</option>`).join("");
  }

  async function loadBranches() {
    const minRating = Number(ratingEl.value || 0);
    const roomType = String(roomTypeEl.value || "").trim();
    const q = new URLSearchParams();
    if (minRating > 0) q.set("min_rating", String(minRating));
    if (roomType) q.set("room_type", roomType);
    q.set("limit", "200");
    const res = await fetch(`/public-api/branches?${q.toString()}`, { cache: "no-store" });
    rows = await res.json();
    const bounds = getSliderBounds();
    priceBounds = bounds;
    priceMinRangeEl.min = String(bounds.min);
    priceMinRangeEl.max = String(bounds.max);
    priceMaxRangeEl.min = String(bounds.min);
    priceMaxRangeEl.max = String(bounds.max);
    if (!priceMinInputEl.value.trim() && !priceMaxInputEl.value.trim()) {
      priceMinRangeEl.value = String(bounds.min);
      priceMaxRangeEl.value = String(bounds.max);
      syncPriceLabels();
    } else {
      syncInputToRange();
    }
    syncInputToRange();
    refreshRoomTypeOptions(roomType);
    render();
  }

  function filteredRows() {
    const needle = String(searchEl.value || "").trim().toLowerCase();
    const maxDistance = toNum(distanceFilterEl.value || "");
    const typedMin = String(priceMinInputEl.value || "").trim();
    const typedMax = String(priceMaxInputEl.value || "").trim();
    const hasTypedPrice = !!typedMin || !!typedMax;
    const rangeMin = toNum(priceMinRangeEl.value);
    const rangeMax = toNum(priceMaxRangeEl.value);
    const usingDefaultRange = (
      rangeMin === priceBounds.min &&
      rangeMax === priceBounds.max
    );
    const priceFilterActive = hasTypedPrice || !usingDefaultRange;
    const userMinPrice = hasTypedPrice ? (toNum(typedMin) ?? priceBounds.min) : (rangeMin ?? priceBounds.min);
    const userMaxPrice = hasTypedPrice ? (toNum(typedMax) ?? priceBounds.max) : (rangeMax ?? priceBounds.max);

    let list = rows.filter((r) => {
      const name = String(r.name || "").toLowerCase();
      const address = String(r.address || "").toLowerCase();
      const textOk = !needle || name.includes(needle) || address.includes(needle);
      if (!textOk) return false;

      const rowMin = toNum(r.min_price);
      const rowMax = toNum(r.max_price);
      if (priceFilterActive) {
        if (rowMin === null && rowMax === null) return false;
        const a = rowMin ?? rowMax;
        const b = rowMax ?? rowMin;
        const minBound = Math.min(userMinPrice, userMaxPrice);
        const maxBound = Math.max(userMinPrice, userMaxPrice);
        if (a > maxBound || b < minBound) return false;
      }

      if (maxDistance === null) return true;
      const d = rowDistance(r);
      return d !== null && d <= maxDistance;
    });

    if (userGeo) {
      list = list.slice().sort((a, b) => {
        const da = rowDistance(a);
        const db = rowDistance(b);
        if (da === null && db === null) return 0;
        if (da === null) return 1;
        if (db === null) return -1;
        return da - db;
      });
    }
    return list;
  }

  function cardHtml(r) {
    const rating = Number(r.avg_rating || 0).toFixed(1);
    const ratingCount = Number(r.rating_count || 0);
    const photoCount = Number(r.photo_count || 0);
    const photo = r.cover_image || "";
    const minPrice = r.min_price;
    const maxPrice = r.max_price;
    const roomTypes = String(r.room_types || "").trim() || "-";
    const totalBeds = Number(r.total_beds || 0);
    const singleBeds = Number(r.single_beds || 0);
    const doubleBeds = Number(r.double_beds || 0);
    const childBeds = Number(r.child_beds || 0);
    const distance = rowDistance(r);
    const distanceHtml = distance === null
      ? ""
      : `<span class="distance-chip">📍 ${distance.toFixed(1)} ${t("distance_km")}</span>`;

    return `
      <article class="branch-card">
        ${
          photo
            ? `<img class="branch-photo" src="${escapeHtml(photo)}" alt="${escapeHtml(r.name)}" loading="lazy" />`
            : `<div class="branch-photo" style="display:grid;place-items:center;color:#64748b">${t("no_photo")}</div>`
        }
        <div class="branch-body">
          <h3 class="branch-title">${escapeHtml(r.name)}</h3>
          <p class="branch-address">${escapeHtml(r.address || "")}</p>
          <div class="branch-meta">
            <span class="rating-stars">${starsText(r.avg_rating)} <b>${rating}</b> (${ratingCount} ${t("reviews")})</span>
            <span>${photoCount} ${t("photo_count")}</span>
          </div>
          <div class="branch-meta">
            <span>${fmtMinMaxPrice(minPrice, maxPrice)}</span>
            ${distanceHtml}
          </div>
          <div class="branch-meta">
            <span>${t("room_types")}: ${escapeHtml(roomTypes)}</span>
          </div>
          <div class="branch-meta">
            <span>${t("bed_info")}: ${fmtBedBreakdown(totalBeds, singleBeds, doubleBeds, childBeds)}</span>
          </div>
          <div class="branch-actions">
            <button class="ghost-btn small-btn" data-open-photos="${r.id}">📷 ${t("photos")}</button>
            <button class="ghost-btn small-btn" data-open-details="${r.id}">ℹ ${t("details")}</button>
            <button class="solid-btn small-btn" data-book="${r.id}">🛏 ${t("booking")}</button>
            <button class="solid-btn small-btn" data-rate="${r.id}">⭐ ${t("rate")}</button>
            <button class="ghost-btn small-btn" data-report="${r.id}">✉ ${t("report")}</button>
          </div>
        </div>
      </article>
    `;
  }

  function render() {
    const list = filteredRows();
    if (!list.length) {
      cardsEl.innerHTML = `<div class="empty">${t("no_data")}</div>`;
      return;
    }
    cardsEl.innerHTML = list.map(cardHtml).join("");
  }

  async function openGallery(branchId, branchName) {
    modalEl.classList.remove("hidden");
    galleryTitleEl.textContent = `${branchName} - ${t("photos")}`;
    galleryEl.innerHTML = `<div class="empty">${t("refresh")}...</div>`;

    const res = await fetch(`/public-api/branches/${branchId}/photos?limit=80`, { cache: "no-store" });
    const payload = await res.json();
    const items = (payload && payload.items) || [];

    if (!items.length) {
      galleryEl.innerHTML = `<div class="empty">${t("no_photo")}</div>`;
      return;
    }

    galleryEl.innerHTML = items
      .map((i) => `<img src="${escapeHtml(i.image_path)}" alt="${escapeHtml(i.room_name || "")}" loading="lazy" />`)
      .join("");
  }

  async function openDetails(branchId, branchName) {
    detailsModalEl.classList.remove("hidden");
    detailsTitleEl.textContent = `${branchName} - ${t("details")}`;
    detailsBodyEl.innerHTML = `<div class="empty">${t("refresh")}...</div>`;

    const res = await fetch(`/public-api/branches/${branchId}/details`, { cache: "no-store" });
    const payload = await res.json();
    const branch = payload && payload.branch;
    const rooms = (payload && payload.rooms) || [];

    if (!branch) {
      detailsBodyEl.innerHTML = `<div class="empty">${t("details_none")}</div>`;
      return;
    }

    const tgRaw = String(branch.contact_telegram || "").trim();
    const tgHandle = tgRaw.startsWith("@") ? tgRaw.slice(1) : tgRaw;
    const tgLink = tgHandle ? `https://t.me/${encodeURIComponent(tgHandle)}` : "";
    const phone = String(branch.contact_phone || "").trim();
    const actions = `
      <div class="branch-actions" style="margin-top:8px;">
        ${phone ? `<a class="solid-btn" href="tel:${escapeHtml(phone)}">${t("call")}</a>` : ""}
        ${tgLink ? `<a class="ghost-btn" target="_blank" rel="noopener" href="${tgLink}">${t("telegram")}</a>` : ""}
      </div>
    `;

    const top = `
      <div class="details-top">
        <div><b>${escapeHtml(branch.name || "")}</b></div>
        <div>${escapeHtml(branch.address || "")}</div>
        <div class="rating-stars">${starsText(branch.avg_rating)} <b>${Number(branch.avg_rating || 0).toFixed(1)}</b> (${Number(branch.rating_count || 0)} ${t("reviews")})</div>
        ${actions}
      </div>
    `;

    const visibleRooms = rooms.filter((r) => Number(r.available_beds || 0) > 0);
    const roomCards = visibleRooms.length
      ? visibleRooms.map((r) => {
          const img = r.cover_image
            ? `<img src="${escapeHtml(r.cover_image)}" alt="${escapeHtml(r.room_name || "")}" loading="lazy" />`
            : `<img alt="no photo" />`;
          const priceLine = fmtMinMaxPrice(r.min_effective_price, r.max_effective_price);

          return `
            <div class="details-room">
              <div class="details-room-top">
                ${img}
                <div class="details-room-meta">
                  <div class="details-room-title">${escapeHtml(r.room_name || r.room_number || "")}</div>
                  <div>${t("room_types")}: ${escapeHtml(r.room_type || "-")}</div>
                  <div>${t("details_beds")}: ${fmtBedBreakdown(
                    Number(r.bed_count || 0),
                    Number(r.single_count || 0),
                    Number(r.double_count || 0),
                    Number(r.child_count || 0)
                  )}</div>
                  <div>${t("available_beds_label")}: ${Number(r.available_beds || 0)}</div>
                  <div>${t("room_status")}: ${occupancyLabel(r.occupancy_status)}</div>
                  <div>${t("details_price")}: ${priceLine}</div>
                </div>
              </div>
            </div>
          `;
        }).join("")
      : `<div class="empty">${t("details_none")}</div>`;

    detailsBodyEl.innerHTML = top + roomCards;
  }

  async function submitRating(branchId) {
    const raw = window.prompt(t("rating_prompt"), "5");
    if (raw == null) return;
    const value = Math.max(1, Math.min(5, parseInt(raw, 10) || 0));
    if (!value) return;
    const comment = window.prompt(t("comment_prompt"), "") || "";

    const res = await fetch(`/public-api/branches/${branchId}/ratings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: value, comment: comment })
    });
    if (!res.ok) return;
    alert(t("saved"));
    await loadBranches();
  }

  function openReport(branchId, branchName) {
    reportBranchIdEl.value = String(branchId);
    reportTitleEl.textContent = `${branchName} - ${t("report")}`;
    reportRoomLabelEl.value = "";
    reportMessageEl.value = "";
    reportContactEl.value = "";
    reportPhotoEl.value = "";
    reportModalEl.classList.remove("hidden");
  }

  function openBooking(branchId, branchName) {
    bookingBranchIdEl.value = String(branchId);
    bookingTitleEl.textContent = `${branchName} - ${t("booking")}`;
    bookingNameEl.value = "";
    bookingPhoneEl.value = "";
    bookingRoomBedEl.value = "";
    bookingCheckinEl.value = "";
    bookingCheckoutEl.value = "";
    bookingMessageEl.value = "";
    bookingModalEl.classList.remove("hidden");
  }

  function findNearest() {
    if (!navigator.geolocation) {
      alert(t("location_unavailable"));
      return;
    }

    findNearestBtnEl.disabled = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userGeo = {
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        };
        findNearestBtnEl.disabled = false;
        render();
      },
      () => {
        findNearestBtnEl.disabled = false;
        alert(t("location_denied"));
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 300000,
      }
    );
  }

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      lang = btn.dataset.lang === "ru" ? "ru" : "uz";
      applyLang();
    });
  });

  refreshEl.addEventListener("click", () => loadBranches());
  toggleFiltersBtnEl.addEventListener("click", () => {
    filtersOpen = !filtersOpen;
    filtersPanelEl.classList.toggle("collapsed", !filtersOpen);
    updateFiltersToggleUi();
  });
  clearFiltersBtnEl.addEventListener("click", () => {
    searchEl.value = "";
    roomTypeEl.value = "";
    ratingEl.value = "0";
    distanceFilterEl.value = "";
    priceMinInputEl.value = "";
    priceMaxInputEl.value = "";
    userGeo = null;
    priceMinRangeEl.value = String(priceBounds.min);
    priceMaxRangeEl.value = String(priceBounds.max);
    syncPriceLabels();
    loadBranches();
  });
  findNearestBtnEl.addEventListener("click", findNearest);
  distanceFilterEl.addEventListener("change", render);
  priceMinInputEl.addEventListener("input", () => {
    syncInputToRange();
    render();
  });
  priceMaxInputEl.addEventListener("input", () => {
    syncInputToRange();
    render();
  });
  priceMinRangeEl.addEventListener("input", () => {
    syncRangeToInput();
    render();
  });
  priceMaxRangeEl.addEventListener("input", () => {
    syncRangeToInput();
    render();
  });
  searchEl.addEventListener("input", render);
  roomTypeEl.addEventListener("change", () => loadBranches());
  ratingEl.addEventListener("change", () => loadBranches());
  closeGalleryEl.addEventListener("click", () => modalEl.classList.add("hidden"));
  closeReportEl.addEventListener("click", () => reportModalEl.classList.add("hidden"));
  closeDetailsEl.addEventListener("click", () => detailsModalEl.classList.add("hidden"));
  closeBookingEl.addEventListener("click", () => bookingModalEl.classList.add("hidden"));
  modalEl.addEventListener("click", (e) => {
    if (e.target === modalEl) modalEl.classList.add("hidden");
  });
  reportModalEl.addEventListener("click", (e) => {
    if (e.target === reportModalEl) reportModalEl.classList.add("hidden");
  });
  detailsModalEl.addEventListener("click", (e) => {
    if (e.target === detailsModalEl) detailsModalEl.classList.add("hidden");
  });
  bookingModalEl.addEventListener("click", (e) => {
    if (e.target === bookingModalEl) bookingModalEl.classList.add("hidden");
  });

  cardsEl.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-open-photos]");
    if (openBtn) {
      const id = Number(openBtn.getAttribute("data-open-photos"));
      const row = rows.find((x) => Number(x.id) === id) || {};
      openGallery(id, row.name || "Branch");
      return;
    }
    const detailsBtn = e.target.closest("[data-open-details]");
    if (detailsBtn) {
      const id = Number(detailsBtn.getAttribute("data-open-details"));
      const row = rows.find((x) => Number(x.id) === id) || {};
      openDetails(id, row.name || "Branch");
      return;
    }
    const bookBtn = e.target.closest("[data-book]");
    if (bookBtn) {
      const id = Number(bookBtn.getAttribute("data-book"));
      const row = rows.find((x) => Number(x.id) === id) || {};
      openBooking(id, row.name || "Branch");
      return;
    }
    const rateBtn = e.target.closest("[data-rate]");
    if (rateBtn) {
      const id = Number(rateBtn.getAttribute("data-rate"));
      submitRating(id);
      return;
    }
    const reportBtn = e.target.closest("[data-report]");
    if (reportBtn) {
      const id = Number(reportBtn.getAttribute("data-report"));
      const row = rows.find((x) => Number(x.id) === id) || {};
      openReport(id, row.name || "Branch");
    }
  });

  reportFormEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const branchId = Number(reportBranchIdEl.value || 0);
    const message = String(reportMessageEl.value || "").trim();
    if (!branchId || !message) return;

    const form = new FormData();
    form.append("branch_id", String(branchId));
    form.append("message", message);
    if (reportRoomLabelEl.value.trim()) form.append("room_label", reportRoomLabelEl.value.trim());
    if (reportContactEl.value.trim()) form.append("contact", reportContactEl.value.trim());
    if (reportPhotoEl.files && reportPhotoEl.files[0]) form.append("file", reportPhotoEl.files[0]);

    const res = await fetch("/public-api/feedback/room-report", {
      method: "POST",
      body: form
    });
    if (!res.ok) return;
    reportModalEl.classList.add("hidden");
    alert(t("report_saved"));
  });

  bookingFormEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const branchId = Number(bookingBranchIdEl.value || 0);
    const phone = String(bookingPhoneEl.value || "").trim();
    if (!branchId || !phone) return;

    const payload = {
      branch_id: branchId,
      full_name: String(bookingNameEl.value || "").trim() || null,
      phone,
      room_or_bed: String(bookingRoomBedEl.value || "").trim() || null,
      checkin: String(bookingCheckinEl.value || "").trim() || null,
      checkout: String(bookingCheckoutEl.value || "").trim() || null,
      message: String(bookingMessageEl.value || "").trim() || null,
    };

    const res = await fetch("/public-api/booking-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return;
    bookingModalEl.classList.add("hidden");
    alert(t("booking_saved"));
  });

  applyLang();
  filtersPanelEl.hidden = !filtersOpen;
  filtersPanelEl.classList.toggle("collapsed", !filtersOpen);
  loadBranches();
})();

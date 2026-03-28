window.t = function (key) {
  const lang = window.CURRENT_LANG || "ru";
  return (
    (window.TRANSLATIONS &&
      window.TRANSLATIONS[lang] &&
      window.TRANSLATIONS[lang][key]) ||
    key
  );
};

let __expiryAlertShown = false;

function isExpiryErrorMessage(msg) {
  const m = String(msg || "").toLowerCase();
  return (
    m.includes("expired") ||
    m.includes("access expired") ||
    m.includes("application access expired") ||
    m.includes("истек") ||
    m.includes("срок") ||
    m.includes("доступ")
  );
}

function buildExpiryContactMessage(baseMessage) {
  const tg = window.ROOT_ADMIN_TELEGRAM || "muzaffar_developer";
  const phone = window.ROOT_ADMIN_PHONE || "+998991422110";
  return (
    (baseMessage || "Срок доступа к приложению истек.") +
    "\n\nСвяжитесь с администратором:\n" +
    "Telegram: @" + tg + "\n" +
    "Телефон: " + phone
  );
}

function translateBackendError(msg) {
  const raw = String(msg || "").trim();
  const lang = (window.CURRENT_LANG || "ru").toLowerCase();
  const isUz = lang.startsWith("uz");
  const byExact = {
    "Username already exists": isUz
      ? "Bu foydalanuvchi nomi allaqachon mavjud"
      : "Это имя пользователя уже существует",
    "Password must be different from username": isUz
      ? "Parol foydalanuvchi nomidan farq qilishi kerak"
      : "Пароль должен отличаться от имени пользователя",
    "New password must be different from username": isUz
      ? "Yangi parol foydalanuvchi nomidan farq qilishi kerak"
      : "Новый пароль должен отличаться от имени пользователя",
    "Telegram ID already linked to another user": isUz
      ? "Bu Telegram ID allaqachon boshqa foydalanuvchiga biriktirilgan"
      : "Этот Telegram ID уже привязан к другому пользователю",
    "Username or Telegram ID already exists": isUz
      ? "Foydalanuvchi nomi yoki Telegram ID allaqachon mavjud"
      : "Имя пользователя или Telegram ID уже существует",
    "Old password is incorrect": isUz
      ? "Eski parol noto'g'ri"
      : "Старый пароль неверный",
  };

  return byExact[raw] || raw;
}

function openPage(id) {
  document.querySelectorAll(".page").forEach(p => {
    p.classList.remove("active");
  });

  document.getElementById(id).classList.add("active");
}

if (window.Telegram && Telegram.WebApp) {
  Telegram.WebApp.expand();
}

function apiGet(path, params = {}) {
  return $.ajax({
    url: "/api2" + path,
    method: "GET",
    data: params,
    dataType: "json"
  }).fail(handleApiError);
}

function apiPost(path, body = {}) {
  return $.ajax({
    url: "/api2" + path,
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(body),
    dataType: "json"
  }).fail(handleApiError);
}

function apiDelete(path, params = {}) {
  const query = $.param(params);
  const url = query ? `/api2${path}?${query}` : `/api2${path}`;

  return $.ajax({
    url: url,
    method: "DELETE",
    dataType: "json"
  }).fail(handleApiError);
}

function apiPut(path, params = {}) {
  const query = $.param(params);
  const url = query ? `/api2${path}?${query}` : `/api2${path}`;

  return $.ajax({
    url: url,
    method: "PUT",
    dataType: "json"
  }).fail(handleApiError);
}

function handleApiError(xhr) {
  let msg = t("request_failed");

  try {
    const data = JSON.parse(xhr.responseText);
    msg = data.detail || data.error || msg;
  } catch (e) {
    if (xhr.responseText) {
      msg = xhr.responseText;
    }
  }

  msg = translateBackendError(msg);

  console.error(t("api_error"), msg);

  if ((xhr && xhr.status === 403 && isExpiryErrorMessage(msg)) || isExpiryErrorMessage(msg)) {
    if (!__expiryAlertShown) {
      __expiryAlertShown = true;
      alert(buildExpiryContactMessage(msg));
      window.location.href = "/login";
    }
    return;
  }

  alert(msg);
}

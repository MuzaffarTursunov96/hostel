window.t = function (key) {
  const lang = window.CURRENT_LANG || "ru";
  return (
    (window.TRANSLATIONS &&
      window.TRANSLATIONS[lang] &&
      window.TRANSLATIONS[lang][key]) ||
    key
  );
};

function openPage(id) {
  document.querySelectorAll(".page").forEach(p => {
    p.classList.remove("active");
  });

  document.getElementById(id).classList.add("active");
}

// Telegram UX improvement
if (window.Telegram && Telegram.WebApp) {
  Telegram.WebApp.expand();
}


/**
 * WEB API CLIENT
 * Equivalent to desktop api_client.py
 * Uses Flask proxy: /api/...
 */

function normalizePath(path) {
  // 🔥 remove leading /api if user passed it by mistake
  if (path.startsWith("/api/")) {
    return path.slice(4); // remove "/api"
  }
  return path;
}

/* ---------- GET ---------- */
function apiGet(path, params = {}) {
  path = normalizePath(path);
  return $.ajax({
    url: "/api" + path,          // 🔥 Flask proxy
    method: "GET",
    data: params,
    dataType: "json"
  }).fail(handleApiError);
}

/* ---------- POST ---------- */
function apiPost(path, body = {}) {
  path = normalizePath(path);
  return $.ajax({
    url: "/api" + path,          // 🔥 Flask proxy
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(body),
    dataType: "json"
  }).fail(handleApiError);
}

/* ---------- DELETE ---------- */
function apiDelete(path, params = {}) {
  path = normalizePath(path);
  
  const query = $.param(params);   // 🔥 convert to query string
  const url = query
    ? `/api${path}?${query}`
    : `/api${path}`;

  return $.ajax({
    url: url,
    method: "DELETE",
    dataType: "json"
  }).fail(handleApiError);
}


/* ---------- ERROR HANDLER (same as desktop) ---------- */
function handleApiError(xhr) {
  let msg = t("request_failed");

  try {
    const data = JSON.parse(xhr.responseText);
    msg = data.detail || msg;
  } catch (e) {
    if (xhr.responseText) {
      msg = xhr.responseText;
    }
  }

  console.error(t("api_error"), msg);
  alert(msg);   // 🔥 same behavior as desktop Exception
}




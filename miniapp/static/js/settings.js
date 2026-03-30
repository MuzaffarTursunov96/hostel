let BRANCHES = [];
let CURRENT_BRANCH = null;
let CURRENT_LANG = "ru";
let SELECTED_USER_ID = null;
let SELECTED_USER_ASSIGNED_BRANCH_IDS = [];
let IS_ROOT_ADMIN = false;


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
      rootBtn.text(CURRENT_LANG === "uz" ? "Root boshqaruvini ochish" : "РћС‚РєСЂС‹С‚СЊ Root СѓРїСЂР°РІР»РµРЅРёРµ");
    }

    if (prefs.notify_enabled !== undefined) {
      $("#myNotifyToggle").prop("checked", prefs.notify_enabled);
    }

  });

  document.addEventListener("DOMContentLoaded", startWebSocket);


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

function fillBranchContactInputs() {
  const bid = Number($("#branchSelect").val() || 0);
  const row = BRANCHES.find((b) => Number(b.id) === bid) || {};
  $("#editBranchPhone").val(row.contact_phone || "");
  $("#editBranchTelegram").val(row.contact_telegram || "");
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
  const name = $("#newBranchName").val().trim();
  const address = $("#newBranchAddress").val().trim();
  const latitude = $("#newBranchLatitude").val().trim();
  const longitude = $("#newBranchLongitude").val().trim();
  const contactPhone = $("#newBranchPhone").val().trim();
  const contactTelegram = $("#newBranchTelegram").val().trim();

  if (!name) {
    alert(t("branch_name_required"));
    return;
  }

  apiPost("/branches/branches-admin", { 
      name: name,
      address: address || null,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null,
      contact_phone: contactPhone || null,
      contact_telegram: contactTelegram || null
    }).done(function () {
      $("#newBranchName").val("");
      $("#newBranchAddress").val("");
      $("#newBranchLatitude").val("");
      $("#newBranchLongitude").val("");
      $("#newBranchPhone").val("");
      $("#newBranchTelegram").val("");
      alert(t("branch_created"));
      loadBranches();
    })
    .fail(function (err) {
      if (err.responseJSON && err.responseJSON.detail) {
        alert(err.responseJSON.detail);
      } else {
        alert(t("api_error"));
      }
    });
}

function saveBranchContacts() {
  const branchId = Number($("#branchSelect").val() || 0);
  if (!branchId) {
    alert(t("select_branch"));
    return;
  }

  const row = BRANCHES.find((b) => Number(b.id) === branchId);
  if (!row) return;

  apiPut(`/branches/admin/${branchId}`, {
    name: row.name,
    address: row.address || null,
    latitude: row.latitude ?? null,
    longitude: row.longitude ?? null,
    contact_phone: ($("#editBranchPhone").val() || "").trim() || null,
    contact_telegram: ($("#editBranchTelegram").val() || "").trim() || null
  }).done(function () {
    alert(t("branch_updated"));
    loadBranches();
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



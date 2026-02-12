let BRANCHES = [];
let CURRENT_BRANCH = null;
let CURRENT_LANG = "ru";
let SELECTED_USER_ID = null;


$(document).ready(function () {


  apiGet("/auth/me").done(function (me) {
    // alert(me)
    CURRENT_BRANCH = me.branch_id;
    // CURRENT_LANG = me.language || "ru";

    // setActiveLangUI(CURRENT_LANG);

    // 🔐 SAVE TO FLASK SESSION
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
      loadBranches();  // 🔥 new
    } else {
      $(".admin-only").hide();
    }
    

    // if (me.notify_enabled !== undefined) {
    //   $("#myNotifyToggle").prop("checked", me.notify_enabled);
    // }




  }).fail(function () {
    loadBranches();

  });


   // 2️⃣ USER PREFERENCES (🔥 NEW API)
  apiGet("/users/me/preferences").done(function (prefs) {

    CURRENT_LANG = prefs.language || "ru";
    setActiveLangUI(CURRENT_LANG);

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

      // ✅ restore selected branch
      if (CURRENT_BRANCH) {
        $select.val(CURRENT_BRANCH);
      }
    });
}

/* ✅ SINGLE change handler (ONLY ONE) */
$(document).on("change", "#branchSelect", function () {
  const branchId = Number($(this).val());
  if (!branchId) return;

  // ✅ update frontend immediately
  CURRENT_BRANCH = branchId;

  $("#branchSelect").val(branchId);

  localStorage.setItem("CURRENT_BRANCH", branchId);


  // ✅ persist backend
  setCurrentBranch(branchId);
});

function createBranch() {
  const name = $("#newBranchName").val().trim();
  const address = $("#newBranchAddress").val().trim();
  const latitude = $("#newBranchLatitude").val().trim();
  const longitude = $("#newBranchLongitude").val().trim();

  if (!name) {
    alert(t("branch_name_required"));
    return;
  }

  apiPost("/branches/branches-admin", { 
      name: name,
      address: address || null,
      latitude: latitude ? parseFloat(latitude) : null,
      longitude: longitude ? parseFloat(longitude) : null 
    }).done(function () {
      $("#newBranchName").val("");
      $("#newBranchAddress").val("");
      $("#newBranchLatitude").val("");
      $("#newBranchLongitude").val("");
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

  // 🔄 UI feedback
  $(".lang-btn").prop("disabled", true);
  $("#lang-" + lang).text(t("lang_changing") + "...");

  apiPost("/settings/language", { language: lang })
    .done(function (res) {

      // 🔥 replace JWT
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

    // 🔥 replace JWT in Flask session
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
    telegram_id: telegramId || null   // ✅ optional
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

      // 🔄 reload users
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

  // 1️⃣ load assigned branches FIRST
  apiGet(`/users/${SELECTED_USER_ID}/branches`).done(function (assigned) {
    const assignedIds = assigned.map(b => b.id);

    // 2️⃣ load all branches
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

  const unchecked = $(".branch-check:not(:checked)").map(function () {
    return Number(this.value);
  }).get();

  const requests = [];

  checked.forEach(branchId => {
    requests.push(
      apiPost(`/branches/${branchId}/assign-user`, {
        user_id: SELECTED_USER_ID
      })
    );
  });

  unchecked.forEach(branchId => {
    requests.push(
      apiDelete(`/branches/${branchId}/users/${SELECTED_USER_ID}`)
      .catch(() => null)
    );
  });

  Promise.all(requests).then(() => {
    alert(t("saved"));
    closeUserBranchModal();
  });
}


function closeUserBranchModal() {
  $("#userBranchModal").addClass("hidden");
}

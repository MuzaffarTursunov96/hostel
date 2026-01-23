let BRANCHES = [];
let CURRENT_BRANCH = null;
let CURRENT_LANG = "ru";

$(document).ready(function () {


  apiGet("/auth/me").done(function (me) {
    // alert(me)
    CURRENT_BRANCH = me.branch_id;
    CURRENT_LANG = me.language || "ru";

    setActiveLangUI(CURRENT_LANG);

    // 🔐 SAVE TO FLASK SESSION
    fetch("/auth/save-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        branch_id: CURRENT_BRANCH
      })
    }).then(() => {
      loadBranches();
      startWebSocket();
    });

  }).fail(function () {
    loadBranches();
  });

});


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

  // ✅ persist backend
  setCurrentBranch(branchId);
});

function addBranch() {
  const name = $("#newBranchName").val().trim();
  if (!name) {
    alert(t("branch_name_cannot_be_empty"));
    return;
  }

  apiPost("/branches", { name })
    .done(function () {
      $("#newBranchName").val("");
      loadBranches();
      alert(t("branch_added_successfully"));
    });
}

function renameBranch() {
  const branchId = $("#branchSelect").val();
  const name = $("#renameBranchName").val().trim();

  if (!branchId || !name) {
    alert(t("select_a_branch_and_enter_new_name"));
    return;
  }

  apiPost("/branches/update", {
    branch_id: Number(branchId),
    name: name
  }).done(function () {
    $("#renameBranchName").val("");
    loadBranches();
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

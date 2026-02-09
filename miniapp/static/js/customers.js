let ALL_CUSTOMERS = [];
let searchTimer = null;

let CURRENT_CUSTOMER_ID = null;
let CURRENT_IMAGE_COUNT = 0;
let CURRENT_BRANCH = null;

$(document).ready(function () {
  loadCustomers();
  CURRENT_BRANCH = localStorage.getItem("CURRENT_BRANCH");
  if (!CURRENT_BRANCH) {
    console.warn("Branch not set yet");
  }

  $("#searchCustomer").on("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applyFilter, 300);
  });
});

/* ===============================
   LOAD CUSTOMERS
================================ */
function loadCustomers() {
  $("#customersTable").html(`
    <div class="text-center text-tgHint py-6">
      ${t("loading_customers")}…
    </div>
  `);

  apiGet("/customers/", { branch_id: CURRENT_BRANCH })
    .done(function (rows) {
      ALL_CUSTOMERS = rows || [];
      alert("Customers loaded: " + ALL_CUSTOMERS.length);
      renderCustomers(ALL_CUSTOMERS);
    });
}

function renderCustomers(customers) {
  const $list = $("#customersTable").empty();

  if (!customers.length) {
    $list.html(`
      <div class="text-center text-tgHint py-6">
        ${t("no_customers_found")}
      </div>
    `);
    return;
  }

  customers.forEach(c => {
    $list.append(`
      <div class="p-4 flex justify-between items-center gap-3">

        <div>
          <div class="font-semibold text-lg">
            👤 ${c.name}
          </div>

          <div class="text-sm text-gray-600">
            🪪 ${c.passport_id || "—"} <br>
            📞 ${c.contact || "—"}
          </div>
        </div>

      </div>
    `);
  });
}


// function renderCustomers(customers) {
//   const $list = $("#customersTable").empty();

//   if (!customers.length) {
//     $list.html(`
//       <div class="text-center text-tgHint py-6">
//         ${t("no_customers_found")}
//       </div>
//     `);
//     return;
//   }

//   customers.forEach(c => {
//     const hasImages = (c.passport_image_count || 0) > 0;

//     $list.append(`
//       <div class="p-4 flex justify-between items-center gap-3">

//         <div>
//           <div class="font-semibold text-lg">👤 ${c.name}</div>

//           <div class="text-sm text-gray-600">
//             🪪 ${c.passport_id || "—"}  <br>
//             📞 ${c.contact || "—"}
//           </div>
//         </div>

//         <div class="flex gap-2">
//           ${
//             hasImages
//               ? `
//                 <button
//                   class="px-3 py-1 rounded-lg border text-sm"
//                   onclick="openPassportImages(${c.id}, ${c.passport_image_count})">
//                   👁 ${t("see")}
//                 </button>

//                 <button
//                   class="px-3 py-1 rounded-lg border text-sm"
//                   onclick="editPassportImages(${c.id}, ${c.passport_image_count})">
//                   ✏️ ${t("edit")}
//                 </button>
//               `
//               : `
//                 <button
//                   class="px-3 py-1 rounded-lg bg-tgButton text-white text-sm"
//                   onclick="uploadPassportImages(${c.id})">
//                   ⬆️ ${t("upload_images")}
//                 </button>
//               `
//           }
//         </div>

//       </div>
//     `);
//   });
// }

/* ===============================
   FILTER
================================ */
function applyFilter() {
  const q = $("#searchCustomer").val().trim().toLowerCase();

  if (!q) {
    renderCustomers(ALL_CUSTOMERS);
    return;
  }

  const filtered = ALL_CUSTOMERS.filter(c =>
    (c.name || "").toLowerCase().includes(q) ||
    (c.passport_id || "").toLowerCase().includes(q) ||
    (c.contact || "").toLowerCase().includes(q)
  );

  renderCustomers(filtered);
}

/* ===============================
   PASSPORT MODAL
================================ */
function openPassportImages(customerId, count) {
  CURRENT_CUSTOMER_ID = customerId;
  CURRENT_IMAGE_COUNT = count;

  $("#passportModal").removeClass("hidden");
  $("#passportImages").html(t("loading") + "...");
  $("#passportUploadBtn").addClass("hidden");

  loadPassportImages(customerId);
}

function editPassportImages(customerId, count) {
  openPassportImages(customerId, count);
  $("#passportUploadBtn").removeClass("hidden");
}

function uploadPassportImages(customerId) {
  CURRENT_CUSTOMER_ID = customerId;
  CURRENT_IMAGE_COUNT = 0;

  $("#passportModal").removeClass("hidden");
  $("#passportImages").html(`
    <div class="col-span-2 text-center text-gray-500">
      ${t("no_passport_images")}
    </div>
  `);
  $("#passportUploadBtn").removeClass("hidden");
}

function closePassportModal() {
  $("#passportModal").addClass("hidden");
  $("#passportUploadInput").val("");
}

/* ===============================
   LOAD IMAGES
================================ */
function loadPassportImages(customerId) {
  fetch(`/api2/customers/${customerId}/passport-images`, {
    credentials: "include"
  })
    .then(r => r.json())
    .then(res => {
      const images = res.images || [];
      const c = $("#passportImages").empty();

      CURRENT_IMAGE_COUNT = images.length;

      if (!images.length) {
        c.html(`
          <div class="col-span-2 text-center text-gray-500">
            ${t("no_passport_images")}
          </div>
        `);
        $("#passportUploadBtn").removeClass("hidden");
        return;
      }

      images.forEach(img => {
        c.append(`
          <div class="relative">
            <img
              src="${img.path}"
              class="w-full rounded-xl border cursor-pointer"
              onclick="window.open('${img.path}', '_blank')"
            />

            <button
              onclick="deletePassportImage(${img.id})"
              class="absolute top-1 right-1 w-7 h-7 bg-red-500 text-white
                     rounded-full flex items-center justify-center text-xs">
              🗑
            </button>
          </div>
        `);
      });
    });
}


function deletePassportImage(imageId) {
  if (!confirm("Delete this passport image?")) return;

  fetch(`/api2/customers/passport-images/${imageId}`, {
    method: "DELETE",
    credentials: "include"
  })
    .then(r => {
      if (!r.ok) throw new Error(t("delete_failed"));
      return r.json();
    })
    .then(() => {
      // reload modal + customers list
      loadPassportImages(CURRENT_CUSTOMER_ID);
      loadCustomers();
    })
    .catch(() => alert(t("failed_to_delete_image")));
}

/* ===============================
   UPLOAD
================================ */
function triggerPassportUpload(e) {
  if (e) e.preventDefault();

  const input = document.getElementById("passportUploadInput");
  input.click();
}


document
  .getElementById("passportUploadInput")
  .addEventListener("change", function () {

    const files = Array.from(this.files || []);

    if (!files.length) return;

    if (CURRENT_IMAGE_COUNT + files.length > 4) {
      alert(t("maximum_4_images_allowed"));
      this.value = "";
      return;
    }

    const fd = new FormData();
    files.forEach(f => fd.append("files", f));

    // 🔥 START LOADING
    setUploadLoading(true);

    fetch(`/api2/customers/${CURRENT_CUSTOMER_ID}/passport-images`, {
      method: "POST",
      credentials: "include",
      body: fd
    })
      .then(async r => {
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      })
      .then(() => {
        closePassportModal();
        loadCustomers();
      })
      .catch(err => {
        console.error(err);
        alert(t("upload_failed"));
      })
      .finally(() => {
        // 🔥 STOP LOADING
        setUploadLoading(false);
        this.value = "";
      });
  });



function setUploadLoading(isLoading) {
  const btn = document.getElementById("passportUploadBtn");
  const text = document.getElementById("uploadBtnText");
  const icon = document.getElementById("uploadBtnIcon");
  const spinner = document.getElementById("uploadSpinner");

  if (isLoading) {
    btn.disabled = true;
    btn.classList.add("opacity-60", "cursor-not-allowed");
    text.innerText = t("uploading") + "…";
    icon.classList.add("hidden");
    spinner.classList.remove("hidden");
  } else {
    btn.disabled = false;
    btn.classList.remove("opacity-60", "cursor-not-allowed");
    text.innerText = t("upload_images");
    icon.classList.remove("hidden");
    spinner.classList.add("hidden");
  }
}

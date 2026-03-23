let ROOT_ADMINS = [];
let ROOT_BRANCHES = [];
let CURRENT_ADMIN_ID = null;

$(function () {
  loadRootManagement();
});

function loadRootManagement() {
  $.when(
    apiGet('/root/admins'),
    apiGet('/root/branches')
  ).done(function (adminsRes, branchesRes) {
    ROOT_ADMINS = adminsRes[0] || [];
    ROOT_BRANCHES = branchesRes[0] || [];
    renderAdminRows();
  });
}

function branchNames(branchIds) {
  const map = new Map((ROOT_BRANCHES || []).map(b => [b.id, b.name]));
  return (branchIds || []).map(id => map.get(id) || ('#' + id)).join(', ');
}

function toDateInputValue(iso) {
  if (!iso) return '';
  return String(iso).slice(0, 10);
}

function renderAdminRows() {
  const $tb = $('#rootAdminTable').empty();

  ROOT_ADMINS.forEach(a => {
    const row = `
      <tr class="border-b align-top">
        <td class="py-2">${a.id}</td>
        <td class="py-2">${a.username || ''}</td>
        <td class="py-2">${a.telegram_id || ''}</td>
        <td class="py-2">${branchNames(a.branches)}</td>
        <td class="py-2">
          <input type="date" id="exp_${a.id}" value="${toDateInputValue(a.admin_expires_at)}" class="px-2 py-1 rounded border">
          <div class="flex gap-1 mt-2">
            <button class="px-2 py-1 text-xs rounded bg-blue-600 text-white" onclick="saveAdminExpiry(${a.id})">Save</button>
            <button class="px-2 py-1 text-xs rounded bg-gray-500 text-white" onclick="clearAdminExpiry(${a.id})">Clear</button>
          </div>
        </td>
        <td class="py-2">
          <label class="inline-flex items-center gap-2">
            <input type="checkbox" ${a.is_active ? 'checked' : ''} onchange="toggleAdminActive(${a.id}, this.checked)">
            <span>${a.is_active ? 'Active' : 'Blocked'}</span>
          </label>
        </td>
        <td class="py-2">
          <div class="flex flex-wrap gap-1">
            <button class="px-2 py-1 text-xs rounded bg-indigo-600 text-white" onclick="openBranches(${a.id})">Filials</button>
            <button class="px-2 py-1 text-xs rounded bg-yellow-600 text-white" onclick="resetAdminPassword(${a.id})">Reset Pass</button>
            <button class="px-2 py-1 text-xs rounded bg-red-600 text-white" onclick="deleteAdmin(${a.id})">Delete</button>
          </div>
        </td>
      </tr>
    `;
    $tb.append(row);
  });
}

function saveAdminExpiry(userId) {
  const d = $(`#exp_${userId}`).val();
  if (!d) {
    alert('Select expiry date first');
    return;
  }
  apiPost(`/root/admins/${userId}/expiry`, { expires_at: `${d}T23:59:59` })
    .done(() => {
      alert('Expiry saved');
      loadRootManagement();
    });
}

function clearAdminExpiry(userId) {
  apiPost(`/root/admins/${userId}/expiry`, { expires_at: null })
    .done(() => {
      alert('Expiry cleared');
      loadRootManagement();
    });
}

function toggleAdminActive(userId, active) {
  apiPost(`/root/admins/${userId}/set-active`, { is_active: !!active })
    .done(() => loadRootManagement());
}

function deleteAdmin(userId) {
  if (!confirm('Delete this admin?')) return;
  apiDelete(`/root/admins/${userId}`)
    .done(() => {
      alert('Admin deleted');
      loadRootManagement();
    });
}

function resetAdminPassword(userId) {
  const pwd = prompt('Enter new password:');
  if (!pwd) return;

  apiPost(`/root/admins/${userId}/password`, { password: pwd })
    .done(() => alert('Password updated'));
}

function openBranches(userId) {
  CURRENT_ADMIN_ID = userId;
  const admin = ROOT_ADMINS.find(x => x.id === userId);
  const selected = new Set((admin && admin.branches) || []);

  const $list = $('#branchModalList').empty();
  ROOT_BRANCHES.forEach(b => {
    $list.append(`
      <label class="flex items-center gap-2 p-2 rounded border">
        <input type="checkbox" class="rm-branch" value="${b.id}" ${selected.has(b.id) ? 'checked' : ''}>
        <span>${b.name}</span>
      </label>
    `);
  });

  $('#branchModal').removeClass('hidden').addClass('flex');
}

function closeBranchModal() {
  $('#branchModal').addClass('hidden').removeClass('flex');
}

function saveAdminBranches() {
  if (!CURRENT_ADMIN_ID) return;

  const ids = $('.rm-branch:checked').map(function () {
    return Number($(this).val());
  }).get();

  apiPost(`/root/admins/${CURRENT_ADMIN_ID}/branches`, { branch_ids: ids })
    .done(() => {
      closeBranchModal();
      alert('Filials updated');
      loadRootManagement();
    });
}

function openCreateAdmin() {
  $('#createAdminModal').removeClass('hidden').addClass('flex');
}

function closeCreateAdmin() {
  $('#createAdminModal').addClass('hidden').removeClass('flex');
}

function createAdmin() {
  const username = $('#newAdminUsername').val().trim();
  const telegram = $('#newAdminTelegram').val().trim();
  const password = $('#newAdminPassword').val().trim();

  if (!telegram || !password) {
    alert('Telegram ID and password required');
    return;
  }

  apiPost('/root/admins', {
    username,
    telegram_id: Number(telegram),
    password
  }).done(() => {
    closeCreateAdmin();
    alert('Admin created');
    loadRootManagement();
  });
}

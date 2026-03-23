let ROOT_ADMINS = [];
let ROOT_BRANCHES = [];
let CURRENT_ADMIN_ID = null;

const RM_I18N = {
  ru: {
    title: 'Управление Root Admin',
    back: 'Назад в настройки',
    add_admin: '+ Добавить админа',
    id: 'ID',
    username: 'Имя пользователя',
    telegram_id: 'Telegram ID',
    filials: 'Филиалы',
    expiry: 'Дата окончания',
    active: 'Активность',
    actions: 'Действия',
    save: 'Сохранить',
    clear: 'Очистить',
    active_state: 'Активен',
    blocked_state: 'Заблокирован',
    filials_btn: 'Филиалы',
    reset_pass: 'Сброс пароля',
    delete: 'Удалить',
    assign_filials: 'Назначить филиалы',
    cancel: 'Отмена',
    create_admin: 'Создать админа',
    password: 'Пароль',
    select_expiry: 'Сначала выберите дату окончания',
    expiry_saved: 'Срок действия сохранен',
    expiry_cleared: 'Срок действия очищен',
    delete_confirm: 'Удалить этого админа?',
    admin_deleted: 'Админ удален',
    enter_new_password: 'Введите новый пароль:',
    password_updated: 'Пароль обновлен',
    filials_updated: 'Филиалы обновлены',
    telegram_password_required: 'Нужны Telegram ID и пароль',
    admin_created: 'Админ создан'
  },
  uz: {
    title: 'Root Admin boshqaruvi',
    back: 'Sozlamalarga qaytish',
    add_admin: '+ Admin qo\'shish',
    id: 'ID',
    username: 'Foydalanuvchi nomi',
    telegram_id: 'Telegram ID',
    filials: 'Filiallar',
    expiry: 'Amal qilish sanasi',
    active: 'Holat',
    actions: 'Amallar',
    save: 'Saqlash',
    clear: 'Tozalash',
    active_state: 'Faol',
    blocked_state: 'Bloklangan',
    filials_btn: 'Filiallar',
    reset_pass: 'Parolni tiklash',
    delete: 'O\'chirish',
    assign_filials: 'Filiallarni biriktirish',
    cancel: 'Bekor qilish',
    create_admin: 'Admin yaratish',
    password: 'Parol',
    select_expiry: 'Avval amal qilish sanasini tanlang',
    expiry_saved: 'Amal qilish muddati saqlandi',
    expiry_cleared: 'Amal qilish muddati tozalandi',
    delete_confirm: 'Ushbu adminni o\'chirasizmi?',
    admin_deleted: 'Admin o\'chirildi',
    enter_new_password: 'Yangi parolni kiriting:',
    password_updated: 'Parol yangilandi',
    filials_updated: 'Filiallar yangilandi',
    telegram_password_required: 'Telegram ID va parol kerak',
    admin_created: 'Admin yaratildi'
  }
};

function rt(k) {
  const lang = window.CURRENT_LANG || 'ru';
  return (RM_I18N[lang] && RM_I18N[lang][k]) || RM_I18N.ru[k] || k;
}

$(function () {
  applyRootTexts();
  loadRootManagement();
});

function applyRootTexts() {
  $('#rmTitle').text(rt('title'));
  $('#rmBackBtn').text(rt('back'));
  $('#rmAddBtn').text(rt('add_admin'));

  $('#rmThId').text(rt('id'));
  $('#rmThUsername').text(rt('username'));
  $('#rmThTelegram').text(rt('telegram_id'));
  $('#rmThFilials').text(rt('filials'));
  $('#rmThExpiry').text(rt('expiry'));
  $('#rmThActive').text(rt('active'));
  $('#rmThActions').text(rt('actions'));

  $('#rmBranchTitle').text(rt('assign_filials'));
  $('#rmBranchSave').text(rt('save'));
  $('#rmBranchCancel').text(rt('cancel'));

  $('#rmCreateTitle').text(rt('create_admin'));
  $('#newAdminUsername').attr('placeholder', rt('username'));
  $('#newAdminTelegram').attr('placeholder', rt('telegram_id'));
  $('#newAdminPassword').attr('placeholder', rt('password'));
  $('#rmCreateSave').text(rt('create_admin'));
  $('#rmCreateCancel').text(rt('cancel'));
}

function loadRootManagement() {
  $.when(apiGet('/root/admins'), apiGet('/root/branches')).done(function (adminsRes, branchesRes) {
    ROOT_ADMINS = adminsRes[0] || [];
    ROOT_BRANCHES = branchesRes[0] || [];
    renderAdminRows();
  });
}

function branchNames(branchIds) {
  const map = new Map((ROOT_BRANCHES || []).map((b) => [b.id, b.name]));
  return (branchIds || []).map((id) => map.get(id) || ('#' + id)).join(', ');
}

function toDateInputValue(iso) {
  if (!iso) return '';
  return String(iso).slice(0, 10);
}

function renderAdminRows() {
  const $tb = $('#rootAdminTable').empty();

  ROOT_ADMINS.forEach((a) => {
    const row = `
      <tr class="border-b align-top">
        <td class="py-2">${a.id}</td>
        <td class="py-2">${a.username || ''}</td>
        <td class="py-2">${a.telegram_id || ''}</td>
        <td class="py-2">${branchNames(a.branches)}</td>
        <td class="py-2">
          <input type="date" id="exp_${a.id}" value="${toDateInputValue(a.admin_expires_at)}" class="px-2 py-1 rounded border">
          <div class="flex gap-1 mt-2">
            <button class="px-2 py-1 text-xs rounded bg-blue-600 text-white" onclick="saveAdminExpiry(${a.id})">${rt('save')}</button>
            <button class="px-2 py-1 text-xs rounded bg-gray-500 text-white" onclick="clearAdminExpiry(${a.id})">${rt('clear')}</button>
          </div>
        </td>
        <td class="py-2">
          <label class="inline-flex items-center gap-2">
            <input type="checkbox" ${a.is_active ? 'checked' : ''} onchange="toggleAdminActive(${a.id}, this.checked)">
            <span>${a.is_active ? rt('active_state') : rt('blocked_state')}</span>
          </label>
        </td>
        <td class="py-2">
          <div class="flex flex-wrap gap-1">
            <button class="px-2 py-1 text-xs rounded bg-indigo-600 text-white" onclick="openBranches(${a.id})">${rt('filials_btn')}</button>
            <button class="px-2 py-1 text-xs rounded bg-yellow-600 text-white" onclick="resetAdminPassword(${a.id})">${rt('reset_pass')}</button>
            <button class="px-2 py-1 text-xs rounded bg-red-600 text-white" onclick="deleteAdmin(${a.id})">${rt('delete')}</button>
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
    alert(rt('select_expiry'));
    return;
  }
  apiPost(`/root/admins/${userId}/expiry`, { expires_at: `${d}T23:59:59` }).done(() => {
    alert(rt('expiry_saved'));
    loadRootManagement();
  });
}

function clearAdminExpiry(userId) {
  apiPost(`/root/admins/${userId}/expiry`, { expires_at: null }).done(() => {
    alert(rt('expiry_cleared'));
    loadRootManagement();
  });
}

function toggleAdminActive(userId, active) {
  apiPost(`/root/admins/${userId}/set-active`, { is_active: !!active }).done(() => loadRootManagement());
}

function deleteAdmin(userId) {
  if (!confirm(rt('delete_confirm'))) return;
  apiDelete(`/root/admins/${userId}`).done(() => {
    alert(rt('admin_deleted'));
    loadRootManagement();
  });
}

function resetAdminPassword(userId) {
  const pwd = prompt(rt('enter_new_password'));
  if (!pwd) return;

  apiPost(`/root/admins/${userId}/password`, { password: pwd }).done(() => alert(rt('password_updated')));
}

function openBranches(userId) {
  CURRENT_ADMIN_ID = userId;
  const admin = ROOT_ADMINS.find((x) => x.id === userId);
  const selected = new Set((admin && admin.branches) || []);

  const $list = $('#branchModalList').empty();
  ROOT_BRANCHES.forEach((b) => {
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

  apiPost(`/root/admins/${CURRENT_ADMIN_ID}/branches`, { branch_ids: ids }).done(() => {
    closeBranchModal();
    alert(rt('filials_updated'));
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
    alert(rt('telegram_password_required'));
    return;
  }

  apiPost('/root/admins', {
    username,
    telegram_id: Number(telegram),
    password
  }).done(() => {
    closeCreateAdmin();
    alert(rt('admin_created'));
    loadRootManagement();
  });
}

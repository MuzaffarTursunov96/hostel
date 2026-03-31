let ROOT_ADMINS = [];
let ROOT_BRANCHES = [];
let CURRENT_ADMIN_ID = null;
let CURRENT_SEARCH = '';

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
    admin_created: 'Админ создан',
    search_placeholder: 'Поиск по ID, имени, Telegram или филиалу...',
    marketing_title: 'Маркетинг контент (сайт)',
    marketing_reload: 'Обновить',
    marketing_save: 'Сохранить контент',
    marketing_help: 'Редактируйте JSON с ценами, видео и карточками контента для hmsuz.com',
    marketing_loading: 'Загрузка контента...',
    marketing_loaded: 'Контент загружен',
    marketing_saved: 'Контент сохранен',
    marketing_invalid_json: 'Некорректный JSON',
    marketing_save_error: 'Ошибка при сохранении контента',
    leads_title: 'Заявки клиентов',
    leads_reload: 'Обновить',
    leads_date: 'Дата',
    leads_name: 'Имя',
    leads_phone: 'Телефон',
    leads_property: 'Объект',
    leads_city: 'Город',
    leads_rooms: 'Комнаты',
    leads_time: 'Удобное время',
    leads_note: 'Комментарий',
    leads_loading: 'Загрузка заявок...',
    leads_loaded: 'Заявки загружены',
    leads_empty: 'Пока нет заявок',
    leads_error: 'Ошибка загрузки заявок',
    branch_publish_title: 'Публикация филиалов (клиент каталог)',
    branch_label: 'Филиал',
    published: 'Опубликован',
    hidden: 'Скрыт',
    publish_updated: 'Статус публикации обновлен'
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
    admin_created: 'Admin yaratildi',
    search_placeholder: 'ID, ism, Telegram yoki filial bo\'yicha qidirish...',
    marketing_title: 'Marketing kontent (sayt)',
    marketing_reload: 'Qayta yuklash',
    marketing_save: 'Kontentni saqlash',
    marketing_help: 'hmsuz.com uchun narxlar, videolar va kontent kartalari JSON faylini tahrir qiling',
    marketing_loading: 'Kontent yuklanmoqda...',
    marketing_loaded: 'Kontent yuklandi',
    marketing_saved: 'Kontent saqlandi',
    marketing_invalid_json: 'JSON formati noto\'g\'ri',
    marketing_save_error: 'Kontentni saqlashda xatolik',
    leads_title: 'Mijoz arizalari',
    leads_reload: 'Qayta yuklash',
    leads_date: 'Sana',
    leads_name: 'Ism',
    leads_phone: 'Telefon',
    leads_property: 'Obyekt',
    leads_city: 'Shahar',
    leads_rooms: 'Xonalar',
    leads_time: 'Qulay vaqt',
    leads_note: 'Izoh',
    leads_loading: 'Arizalar yuklanmoqda...',
    leads_loaded: 'Arizalar yuklandi',
    leads_empty: 'Hozircha arizalar yo\'q',
    leads_error: 'Arizalarni yuklashda xatolik',
    branch_publish_title: 'Filial nashri (mijoz katalogi)',
    branch_label: 'Filial',
    published: 'E’lon qilingan',
    hidden: 'Yashirilgan',
    publish_updated: 'Nashr holati yangilandi'
  }
};

function rt(k) {
  const lang = window.CURRENT_LANG || 'ru';
  return (RM_I18N[lang] && RM_I18N[lang][k]) || RM_I18N.ru[k] || k;
}

$(function () {
  applyRootTexts();
  loadRootManagement();
  loadMarketingContentEditor();
  loadLeadsTable();
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
  $('#rmSearch').attr('placeholder', rt('search_placeholder'));

  $('#rmMarketingTitle').text(rt('marketing_title'));
  $('#rmMarketingReload').text(rt('marketing_reload'));
  $('#rmMarketingSave').text(rt('marketing_save'));
  $('#rmMarketingHelp').text(rt('marketing_help'));

  $('#rmLeadsTitle').text(rt('leads_title'));
  $('#rmLeadsReload').text(rt('leads_reload'));
  $('#rmLeadDate').text(rt('leads_date'));
  $('#rmLeadName').text(rt('leads_name'));
  $('#rmLeadPhone').text(rt('leads_phone'));
  $('#rmLeadProperty').text(rt('leads_property'));
  $('#rmLeadCity').text(rt('leads_city'));
  $('#rmLeadRooms').text(rt('leads_rooms'));
  $('#rmLeadTime').text(rt('leads_time'));
  $('#rmLeadNote').text(rt('leads_note'));

  $('#rmBranchPublishTitle').text(rt('branch_publish_title'));
  $('#rmBrThId').text(rt('id'));
  $('#rmBrThName').text(rt('branch_label'));
  $('#rmBrThPublished').text(rt('published'));
}

function loadRootManagement() {
  $.when(apiGet('/root/admins'), apiGet('/root/branches')).done(function (adminsRes, branchesRes) {
    ROOT_ADMINS = adminsRes[0] || [];
    ROOT_BRANCHES = branchesRes[0] || [];
    renderAdminRows();
    renderBranchPublishRows();
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
  const q = (CURRENT_SEARCH || '').trim().toLowerCase();

  ROOT_ADMINS.forEach((a) => {
    const filialsText = branchNames(a.branches);
    const searchable = `${a.id} ${a.username || ''} ${a.telegram_id || ''} ${filialsText}`.toLowerCase();
    if (q && !searchable.includes(q)) return;

    const row = `
      <tr class="border-b align-top">
        <td class="py-2">${a.id}</td>
        <td class="py-2">${a.username || ''}</td>
        <td class="py-2">${a.telegram_id || ''}</td>
        <td class="py-2">${filialsText}</td>
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

function renderBranchPublishRows() {
  const $tb = $('#rootBranchPublishTable').empty();
  const q = (CURRENT_SEARCH || '').trim().toLowerCase();
  (ROOT_BRANCHES || []).forEach((b) => {
    const searchable = `${b.id} ${b.name || ''}`.toLowerCase();
    if (q && !searchable.includes(q)) return;
    const isPublished = !!b.is_published;
    const row = `
      <tr class="border-b align-top">
        <td class="py-2">${b.id}</td>
        <td class="py-2">${b.name || ''}</td>
        <td class="py-2">
          <label class="inline-flex items-center gap-2">
            <input type="checkbox" ${isPublished ? 'checked' : ''} onchange="toggleBranchPublish(${b.id}, this.checked)">
            <span>${isPublished ? rt('published') : rt('hidden')}</span>
          </label>
        </td>
      </tr>
    `;
    $tb.append(row);
  });
}

function onRootSearch(value) {
  CURRENT_SEARCH = value || '';
  renderAdminRows();
  renderBranchPublishRows();
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

function toggleBranchPublish(branchId, isPublished) {
  apiPost(`/root/branches/${branchId}/publish`, { is_published: !!isPublished }).done(() => {
    alert(rt('publish_updated'));
    loadRootManagement();
  });
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

function loadMarketingContentEditor() {
  $('#rmMarketingStatus').text(rt('marketing_loading'));
  $.ajax({
    url: '/root-marketing-content',
    method: 'GET',
    dataType: 'json'
  }).done((res) => {
    const content = (res && res.content) || {};
    $('#rmMarketingJson').val(JSON.stringify(content, null, 2));
    $('#rmMarketingStatus').text(rt('marketing_loaded'));
  }).fail(() => {
    $('#rmMarketingStatus').text(rt('marketing_save_error'));
  });
}

function saveMarketingContentEditor() {
  let content;
  try {
    content = JSON.parse($('#rmMarketingJson').val() || '{}');
  } catch (_) {
    $('#rmMarketingStatus').text(rt('marketing_invalid_json'));
    return;
  }

  $('#rmMarketingStatus').text(rt('marketing_loading'));
  $.ajax({
    url: '/root-marketing-content',
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ content }),
    dataType: 'json'
  }).done((res) => {
    if (res && res.ok) {
      $('#rmMarketingStatus').text(rt('marketing_saved'));
      return;
    }
    $('#rmMarketingStatus').text((res && res.error) || rt('marketing_save_error'));
  }).fail((xhr) => {
    let msg = rt('marketing_save_error');
    try {
      const data = JSON.parse(xhr.responseText || '{}');
      msg = data.error || msg;
    } catch (_) {}
    $('#rmMarketingStatus').text(msg);
  });
}

function esc(v) {
  return String(v == null ? '' : v)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('\"', '&quot;');
}

function loadLeadsTable() {
  $('#rmLeadsStatus').text(rt('leads_loading'));
  $.ajax({
    url: '/root-leads',
    method: 'GET',
    dataType: 'json'
  }).done((res) => {
    const leads = (res && res.leads) || [];
    const $tb = $('#rmLeadsTable').empty();
    if (!leads.length) {
      $tb.append(`<tr><td colspan=\"8\" class=\"py-2 text-gray-500\">${rt('leads_empty')}</td></tr>`);
      $('#rmLeadsStatus').text(rt('leads_loaded'));
      return;
    }

    leads.forEach((lead) => {
      const row = `
        <tr class=\"border-b align-top\">
          <td class=\"py-2\">${esc(lead.created_at || '')}</td>
          <td class=\"py-2\">${esc(lead.manager_name || '')}</td>
          <td class=\"py-2\">${esc(lead.phone || '')}</td>
          <td class=\"py-2\">${esc(lead.property_name || '')}</td>
          <td class=\"py-2\">${esc(lead.city || '')}</td>
          <td class=\"py-2\">${esc(lead.rooms || '')}</td>
          <td class=\"py-2\">${esc(lead.preferred_time || '')}</td>
          <td class=\"py-2\">${esc(lead.note || '')}</td>
        </tr>
      `;
      $tb.append(row);
    });

    $('#rmLeadsStatus').text(rt('leads_loaded'));
  }).fail(() => {
    $('#rmLeadsStatus').text(rt('leads_error'));
  });
}

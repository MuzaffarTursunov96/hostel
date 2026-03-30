(function () {
  const translations = {
    uz: {
      catalog: "Katalog",
      catalog_view: "Katalogni ko'rish",
      login: "Telegram Login",
      prices: "Narxlar",
      apply: "Ariza Qoldirish",
      for_hostel: "Hostel va Hotel uchun",
      hero_title: "Bronlardan hisobotgacha hammasi bitta tizimda",
      hero_copy: "HMSUZ menejer va egalar uchun kundalik boshqaruvni yengillashtiradi: xonalar holati, tolovlar, qarzdorlik va mijoz tarixi real vaqtda korinadi.",
      call: "Qongiroq: +998 99 142 21 10",
      m1: "ichida ishga tushirish",
      m2: "texnik yordam",
      m3: "uzbekcha interfeys",
      f1t: "Bron va xona nazorati",
      f1d: "Bo'sh va band xonalar, kirish/chiqish, muddatni uzaytirish va bekor qilish jarayonlari tez boshqariladi.",
      f2t: "Moliya aniq korinadi",
      f2d: "Tolovlar, qarzlar, qaytarimlar va kunlik/yillik hisobotlar avtomatik shakllanadi.",
      f3t: "Xodimlar uchun qulay",
      f3d: "Bir necha klik bilan asosiy amallar bajariladi, xatolar kamayadi va vaqt tejaladi.",
      offer_t: "Nima uchun egalar HMSUZni tanlaydi?",
      offer_d: "Excel va qogozdan chiqib, barcha jarayonlarni yagona platformada boshqarish mumkin. Natija: tezroq servis, toza hisobot, kuchli nazorat.",
      write_tg: "Telegram orqali yozish",
      content_title: "Mahsulot kontenti",
      content_sub: "Rasmlar va matnlar marketing uchun dinamik yuklanadi.",
      video_title: "Video taqdimotlar",
      video_sub: "YouTube videolarni sahifaga bemalol joylashingiz mumkin.",
      pricing_title: "Narxlar (so'm)",
      pricing_sub: "Narxlar dinamik va konfiguratsiya faylidan olinadi.",
      monthly: "oyiga",
      setup: "ulanish",
      included: "Nimalar kiradi:",
      empty_content: "Kontent hozircha qo'shilmagan.",
      empty_video: "Videolar hozircha qo'shilmagan.",
      empty_pricing: "Narxlar hozircha qo'shilmagan.",
      form_title: "Ariza qoldiring",
      form_sub: "Ism va telefon raqamingizni qoldiring. Muzaffar siz bilan tez orada boglanadi.",
      l_name: "Ism va familiya",
      l_phone: "Telefon raqam",
      l_property: "Hostel/Hotel nomi",
      l_city: "Shahar",
      l_rooms: "Xonalar soni (ixtiyoriy)",
      l_time: "Qulay boglanish vaqti (ixtiyoriy)",
      l_note: "Izoh (ixtiyoriy)",
      send: "Ariza yuborish",
      sending: "Yuborilmoqda...",
      submit_ok: "Ariza qabul qilindi. Muzaffar siz bilan tez orada boglanadi.",
      submit_err: "Xatolik yuz berdi, iltimos qayta urinib koring.",
      net_err: "Internet xatosi. Iltimos yana bir bor yuboring.",
      ph_name: "Masalan: Azizbek Karimov",
      ph_phone: "+998 90 123 45 67",
      ph_property: "Masalan: City Nest Hostel",
      ph_city: "Masalan: Toshkent",
      ph_rooms: "Masalan: 18",
      ph_time: "Masalan: 10:00 - 12:00",
      ph_note: "Hozir qaysi tizimdan foydalanyapsiz?"
    },
    ru: {
      catalog: "Каталог",
      catalog_view: "Смотреть каталог",
      login: "Вход через Telegram",
      prices: "Цены",
      apply: "Оставить заявку",
      for_hostel: "Для hostel и hotel",
      hero_title: "Все управление: от брони до отчетов в одной системе",
      hero_copy: "HMSUZ упрощает ежедневную работу менеджера и владельца: статус номеров, оплаты, долги и история гостей всегда под рукой.",
      call: "Звонок: +998 99 142 21 10",
      m1: "запуск за 1 день",
      m2: "техподдержка",
      m3: "интерфейс на узбекском и русском",
      f1t: "Контроль брони и номеров",
      f1d: "Быстро управляйте свободными и занятыми номерами, заездами, выездами, продлениями и отменами.",
      f2t: "Финансы под контролем",
      f2d: "Оплаты, долги, возвраты и отчеты формируются автоматически.",
      f3t: "Удобно для персонала",
      f3d: "Основные действия выполняются в несколько кликов, ошибок меньше, скорость выше.",
      offer_t: "Почему владельцы выбирают HMSUZ?",
      offer_d: "Переходите от Excel и бумаги к единой системе. Результат: быстрее сервис, прозрачные отчеты, полный контроль.",
      write_tg: "Написать в Telegram",
      content_title: "Маркетинговый контент",
      content_sub: "Картинки и тексты загружаются динамически.",
      video_title: "Видео презентации",
      video_sub: "Вы можете легко добавить YouTube-видео на страницу.",
      pricing_title: "Цены (сум)",
      pricing_sub: "Цены динамические и берутся из конфигурационного файла.",
      monthly: "в месяц",
      setup: "подключение",
      included: "Что включено:",
      empty_content: "Контент пока не добавлен.",
      empty_video: "Видео пока не добавлены.",
      empty_pricing: "Цены пока не добавлены.",
      form_title: "Оставьте заявку",
      form_sub: "Оставьте имя и номер телефона. Музаффар свяжется с вами в ближайшее время.",
      l_name: "Имя и фамилия",
      l_phone: "Номер телефона",
      l_property: "Название hostel/hotel",
      l_city: "Город",
      l_rooms: "Количество комнат (необязательно)",
      l_time: "Удобное время для связи (необязательно)",
      l_note: "Комментарий (необязательно)",
      send: "Отправить заявку",
      sending: "Отправка...",
      submit_ok: "Заявка принята. Музаффар скоро с вами свяжется.",
      submit_err: "Произошла ошибка, попробуйте еще раз.",
      net_err: "Ошибка сети. Пожалуйста, отправьте еще раз.",
      ph_name: "Например: Азизбек Каримов",
      ph_phone: "+998 90 123 45 67",
      ph_property: "Например: City Nest Hostel",
      ph_city: "Например: Ташкент",
      ph_rooms: "Например: 18",
      ph_time: "Например: 10:00 - 12:00",
      ph_note: "Какую систему вы используете сейчас?"
    }
  };

  let currentLang = "uz";
  let marketingContent = { pricing: [], videos: [], content_cards: [], updated_at: "" };

  const form = document.getElementById("leadForm");
  const status = document.getElementById("leadStatus");
  const langInput = document.getElementById("leadLang");
  const langButtons = document.querySelectorAll(".lang-btn");
  const contentGrid = document.getElementById("contentGrid");
  const videoGrid = document.getElementById("videoGrid");
  const pricingGrid = document.getElementById("pricingGrid");
  const pricingNote = document.getElementById("pricingNote");

  function getText(lang, key) {
    return (translations[lang] && translations[lang][key]) || key;
  }

  function formatSom(value, lang) {
    const amount = Number(value || 0);
    const formatted = new Intl.NumberFormat(lang === "ru" ? "ru-RU" : "uz-UZ").format(amount);
    return lang === "ru" ? `${formatted} сум` : `${formatted} so'm`;
  }

  function renderContentCards(lang) {
    if (!contentGrid) return;
    const cards = Array.isArray(marketingContent.content_cards) ? marketingContent.content_cards : [];

    if (!cards.length) {
      contentGrid.innerHTML = `<p class="empty-state">${getText(lang, "empty_content")}</p>`;
      return;
    }

    contentGrid.innerHTML = cards.map((card) => {
      const title = lang === "ru" ? (card.title_ru || card.title_uz || "") : (card.title_uz || card.title_ru || "");
      const text = lang === "ru" ? (card.text_ru || card.text_uz || "") : (card.text_uz || card.text_ru || "");
      const image = card.image_url || "";
      return `
        <article class="content-card">
          ${image ? `<img src="${image}" alt="${title.replace(/"/g, "&quot;")}" loading="lazy" />` : ""}
          <div class="content-card-body">
            <h3>${title}</h3>
            <p>${text}</p>
          </div>
        </article>
      `;
    }).join("");
  }

  function renderVideos(lang) {
    if (!videoGrid) return;
    const videos = Array.isArray(marketingContent.videos) ? marketingContent.videos : [];

    if (!videos.length) {
      videoGrid.innerHTML = `<p class="empty-state">${getText(lang, "empty_video")}</p>`;
      return;
    }

    videoGrid.innerHTML = videos.map((video) => {
      const title = lang === "ru" ? (video.title_ru || video.title_uz || "") : (video.title_uz || video.title_ru || "");
      const id = (video.youtube_id || "").trim();
      if (!id) return "";
      return `
        <article class="video-card">
          <div class="video-frame">
            <iframe src="https://www.youtube.com/embed/${id}" title="${title.replace(/"/g, "&quot;")}" loading="lazy" allowfullscreen></iframe>
          </div>
          <p>${title}</p>
        </article>
      `;
    }).join("");
  }

  function renderPricing(lang) {
    if (!pricingGrid) return;
    const pricing = Array.isArray(marketingContent.pricing) ? marketingContent.pricing : [];

    if (!pricing.length) {
      pricingGrid.innerHTML = `<p class="empty-state">${getText(lang, "empty_pricing")}</p>`;
      return;
    }

    pricingGrid.innerHTML = pricing.map((plan) => {
      const name = lang === "ru" ? (plan.name_ru || plan.name_uz || "") : (plan.name_uz || plan.name_ru || "");
      const description = lang === "ru" ? (plan.description_ru || plan.description_uz || "") : (plan.description_uz || plan.description_ru || "");
      const features = lang === "ru" ? (plan.features_ru || plan.features_uz || []) : (plan.features_uz || plan.features_ru || []);
      const monthly = formatSom(plan.monthly_uzs, lang);
      const setup = formatSom(plan.setup_uzs, lang);
      return `
        <article class="price-card">
          <h3>${name}</h3>
          <p class="price-amount">${monthly} <span>${getText(lang, "monthly")}</span></p>
          <p class="price-setup">${setup} ${getText(lang, "setup")}</p>
          <p class="price-desc">${description}</p>
          <p class="price-inc">${getText(lang, "included")}</p>
          <ul>${features.map((item) => `<li>${item}</li>`).join("")}</ul>
        </article>
      `;
    }).join("");

    if (pricingNote && marketingContent.updated_at) {
      const base = getText(lang, "pricing_sub");
      pricingNote.textContent = `${base} (${marketingContent.updated_at})`;
    }
  }

  function renderDynamicSections(lang) {
    renderContentCards(lang);
    renderVideos(lang);
    renderPricing(lang);
  }

  async function loadMarketingContent() {
    try {
      const response = await fetch("/marketing-content", { cache: "no-store" });
      const body = await response.json();
      if (body && typeof body === "object") {
        marketingContent = body;
      }
    } catch (_) {
      marketingContent = { pricing: [], videos: [], content_cards: [], updated_at: "" };
    }
    renderDynamicSections(currentLang);
  }

  function applyLang(lang) {
    currentLang = lang;
    document.documentElement.lang = lang;
    if (langInput) langInput.value = lang;
    localStorage.setItem("hms_lang", lang);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      el.textContent = getText(lang, key);
    });

    document.querySelectorAll("[data-ph]").forEach((el) => {
      const key = el.getAttribute("data-ph");
      el.placeholder = getText(lang, key);
    });

    langButtons.forEach((btn) => {
      const active = btn.getAttribute("data-lang") === lang;
      btn.classList.toggle("active", active);
    });

    renderDynamicSections(lang);
  }

  const initialLang = localStorage.getItem("hms_lang") || "uz";
  applyLang(initialLang === "ru" ? "ru" : "uz");
  loadMarketingContent();

  langButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const lang = btn.getAttribute("data-lang") === "ru" ? "ru" : "uz";
      applyLang(lang);
      if (status) status.textContent = "";
    });
  });

  if (!form || !status) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const lang = (langInput && langInput.value === "ru") ? "ru" : "uz";
    status.textContent = getText(lang, "sending");

    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      const response = await fetch("/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const body = await response.json().catch(() => ({}));

      if (!response.ok || !body.ok) {
        status.textContent = body.error || getText(lang, "submit_err");
        return;
      }

      form.reset();
      if (langInput) langInput.value = lang;
      status.textContent = getText(lang, "submit_ok");
    } catch (_) {
      status.textContent = getText(lang, "net_err");
    }
  });
})();

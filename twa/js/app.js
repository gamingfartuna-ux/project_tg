/* VideoVeoBot TWA — talks to /api/* on the aiohttp backend.
 *
 * Auth: every non-/api/health request carries
 *   Authorization: tma <initData>
 * where ``initData`` comes from ``window.Telegram.WebApp.initData`` and is
 * validated server-side via HMAC-SHA256 against the bot token
 * (see bot/services/twa_auth.py).
 *
 * State: balance / history / profile live on the server. The only piece of
 * state we keep client-side is the wizard (model/format/mode/duration/sound/
 * image/prompt) — that's per-session UI, not data.
 */

(function () {
  'use strict';

  // -------- Telegram SDK --------

  const tg = (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp)
    ? window.Telegram.WebApp
    : null;

  if (tg) {
    try { tg.ready(); tg.expand(); } catch (e) { /* SDK not fully wired */ }
  }

  function isInTelegram() {
    return !!tg && typeof tg.initData === 'string' && tg.initData.length > 0;
  }

  // -------- API client --------

  // Same origin as the page by default; tweak here for staging/prod.
  const API_BASE = (function () {
    if (typeof window === 'undefined') return '';
    return window.location.origin || '';
  })();

  function authHeader() {
    if (!isInTelegram()) return null;
    return 'tma ' + tg.initData;
  }

  async function api(path, options = {}) {
    const opts = Object.assign({ method: 'GET', headers: {} }, options);
    opts.headers = Object.assign({}, opts.headers);
    const auth = authHeader();
    if (auth) opts.headers['Authorization'] = auth;
    if (opts.body && typeof opts.body !== 'string') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    let res;
    try {
      res = await fetch(API_BASE + path, opts);
    } catch (e) {
      throw new Error('Сеть недоступна: ' + e.message);
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* leave null */ }
    if (!res.ok) {
      const msg = (data && data.error) ? data.error : ('HTTP ' + res.status);
      const err = new Error(msg);
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  }

  // -------- Models / wizard state --------

  const MODELS = {
    kling:    { name: 'Kling 3.0',    desc: 'генерация видео' },
    veo:      { name: 'VEO 3',        desc: 'нативный звук, физика' },
    seedance: { name: 'Seedance 2.0', desc: 'реалистичное видео' },
    lipsync:  { name: 'Lipsync',      desc: 'оживление фото + аудио' },
  };

  const EXAMPLES = [
    {
      title: 'Ведущий и бабушка',
      prompt: 'Ведущий с микрофоном спрашивает у бабушки на улицах на русском языке. (оператор) - "вы понимаете, что вы нейросеть?" (бабушка) - "да, внучок, ты ведь тоже нейронка, ахаха" (смеётся). Бабушка прыгает вверх.',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
    },
    {
      title: 'Эпическое уклонение',
      prompt: 'Мужчина в чёрном плаще эпически уклоняется от пули, словно в замедленной съёмке. Видео начинается с близкого плана на лицо мужчины, он в чёрных узких очках. Далее — замедленная съёмка: мужчина наклоняется назад, его тело изгибается в воздухе. Вокруг летят частицы пыли, искры и обломки. Сцена кинематографична, в тёмных тонах, глубоких зелёных и чёрных.',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
    },
    {
      title: 'Утренний кофе',
      prompt: 'Девушка в уютной кухне наливает кофе в чашку. Мягкий утренний свет, крупный план, замедленная съёмка пара. Стиль — lifestyle, тёплые тона, уютная атмосфера.',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4',
    },
    {
      title: 'Город ночью',
      prompt: 'Ночной мегаполис, неоновые вывески, отражения в мокром асфальте. Камера медленно скользит между зданий. Киберпанк-стиль, фиолетовые и голубые тона, лёгкий дождь.',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4',
    },
    {
      title: 'Собака на прогулке',
      prompt: 'Золотистый ретривер бежит по осеннему парку, листья под ногами, счастливая морда крупным планом. Тёплый дневной свет, лёгкая замедленная съёмка.',
      videoUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4',
    },
  ];

  // Wizard state (kept client-side — it's UI state).
  const wizard = {
    model: 'kling',
    fmt: 'vertical',
    mode: 'standard',
    duration: 5,
    sound: true,
    imageFile: null,
    prompt: '',
    exampleIdx: 0,
    screen: 'main',
  };

  // Server-driven state (mirror of /api/me + /api/generations).
  const server = {
    user: null,
    balance: 0,
    history: [],
  };

  // -------- Helpers --------

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function toast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('is-show'));
    setTimeout(() => {
      t.classList.remove('is-show');
      setTimeout(() => t.remove(), 250);
    }, 1600);
  }

  function flash(el) {
    if (!el) return;
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');
  }

  function computeCost() {
    const base = { standard: 1, pro: 2, '4k': 4 }[wizard.mode] || 1;
    return base + (wizard.duration >= 10 ? 1 : 0);
  }

  function modelLabel(key) {
    return MODELS[key] ? MODELS[key].name : key;
  }

  function pad2(n) { return String(n).padStart(2, '0'); }
  function formatDate(d) {
    let dt;
    if (d instanceof Date) dt = d;
    else if (typeof d === 'string') { dt = new Date(d); if (isNaN(dt.getTime())) return d; }
    else return String(d);
    return `${pad2(dt.getDate())}.${pad2(dt.getMonth() + 1)} ${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // -------- Section visibility --------

  function showScreen(name) {
    wizard.screen = name;
    $$('.card[data-screen]').forEach((card) => {
      const screen = card.dataset.screen;
      const keep = (name === 'all') ||
                   (screen === name) ||
                   (name === 'main' && screen !== 'balance' && screen !== 'history' && screen !== 'profile');
      card.classList.toggle('is-hidden', !keep);
    });
  }

  // -------- Renderers --------

  function renderModelCard() {
    const m = MODELS[wizard.model];
    $('#modelName').textContent = m.name;
    $('#modelDesc').textContent = m.desc;
  }

  function renderFormat() {
    $$('.option-row[data-field="fmt"]').forEach((row) => {
      row.classList.toggle('is-selected', row.dataset.value === wizard.fmt);
    });
  }

  function renderMode() {
    $$('.seg__btn[data-field="mode"]').forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.value === wizard.mode);
      const disabled = btn.dataset.value === '4k' && wizard.fmt === 'horizontal';
      btn.style.opacity = disabled ? '0.45' : '';
      btn.style.pointerEvents = disabled ? 'none' : '';
    });
    if (wizard.fmt === 'horizontal' && wizard.mode === '4k') {
      wizard.mode = 'pro';
    }
  }

  function renderDuration() {
    $$('.seg__btn[data-field="duration"]').forEach((btn) => {
      btn.classList.toggle('is-active', Number(btn.dataset.value) === wizard.duration);
    });
  }

  function renderSound() {
    const btn = $('#soundToggle');
    const lbl = $('#soundState');
    const on = wizard.sound && wizard.mode !== '4k';
    btn.classList.toggle('is-on', on);
    lbl.textContent = on ? '🔊 включён' : '🔇 выключен';
  }

  function renderCost() {
    const cost = computeCost();
    $('#costValue').textContent = cost;
    $('#balanceValue').textContent = server.balance;
    const after = server.balance - cost;
    const afterEl = $('#balanceAfter');
    afterEl.textContent = `останется ${after}`;
    afterEl.classList.toggle('is-low', after < 0);
    $('#runBtn').disabled = after < 0;
    $('#runBtn').textContent = after < 0 ? '💰 Пополнить баланс' : 'Сгенерировать';
  }

  function renderPromptCounter() {
    const len = wizard.prompt.length;
    $('#promptCounter').textContent = `${len} / 2500`;
  }

  function renderExample() {
    const ex = EXAMPLES[wizard.exampleIdx];
    const vid = $('#exampleVideo');
    vid.src = ex.videoUrl;
    $('#exampleTitle').textContent = ex.title;
    $('#examplePrompt').textContent = ex.prompt;
    $('#examplePos').textContent = `${wizard.exampleIdx + 1} / ${EXAMPLES.length}`;
  }

  function renderBalanceScreen() {
    $('#balanceBig').textContent = server.balance;
    const pct = Math.min(100, Math.max(0, (server.balance / 50) * 100));
    $('#balanceBarFill').style.width = `${pct}%`;
  }

  function renderHistory() {
    const list = $('#historyList');
    list.innerHTML = '';
    if (!server.history.length) {
      const li = document.createElement('li');
      li.className = 'history__empty';
      li.textContent = 'Пока пусто. Сгенерируйте первое видео.';
      list.appendChild(li);
      return;
    }
    server.history.slice(0, 10).forEach((item, i) => {
      const li = document.createElement('li');
      li.className = 'history__item';
      const promptShort = (item.prompt || '(без промпта)').slice(0, 40);
      li.innerHTML = `
        <span class="history__num">${i + 1}</span>
        <div class="history__main">
          <span class="history__title">${escapeHtml(modelLabel(item.model))} · ${escapeHtml(formatDate(item.created_at))}</span>
          <span class="history__prompt">${escapeHtml(promptShort)}${item.prompt && item.prompt.length > 40 ? '…' : ''}</span>
        </div>
        <span class="history__cost">−${item.cost}</span>
      `;
      list.appendChild(li);
    });
  }

  function renderProfile() {
    const u = server.user;
    if (!u) {
      $('#profileName').textContent = '—';
      $('#profileHandle').textContent = '—';
      $('#profileId').textContent = '—';
      $('#profileAvatar').textContent = '👤';
      return;
    }
    const fullName = [u.first_name, u.last_name].filter(Boolean).join(' ') || 'Без имени';
    $('#profileName').textContent = fullName;
    $('#profileHandle').textContent = u.username ? '@' + u.username : '—';
    $('#profileId').textContent = 'id: ' + u.id;
    $('#profileAvatar').textContent = u.photo_url
      ? ''
      : (u.first_name ? u.first_name.slice(0, 1).toUpperCase() : '👤');
    if (u.photo_url) {
      $('#profileAvatar').innerHTML = `<img src="${escapeHtml(u.photo_url)}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover">`;
    }
  }

  function renderAll() {
    renderModelCard();
    renderFormat();
    renderMode();
    renderDuration();
    renderSound();
    renderCost();
    renderPromptCounter();
    renderExample();
    renderBalanceScreen();
    renderHistory();
    renderProfile();
    showScreen(wizard.screen || 'main');
  }

  // -------- Wire-up --------

  function wireFormat() {
    $$('.option-row[data-field="fmt"]').forEach((row) => {
      row.addEventListener('click', () => {
        wizard.fmt = row.dataset.value;
        renderFormat();
        renderMode();
        renderSound();
        renderCost();
        flash(row);
      });
    });
  }

  function wireMode() {
    $$('.seg__btn[data-field="mode"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        wizard.mode = btn.dataset.value;
        renderMode();
        renderSound();
        renderCost();
        flash(btn);
      });
    });
  }

  function wireDuration() {
    $$('.seg__btn[data-field="duration"]').forEach((btn) => {
      btn.addEventListener('click', () => {
        wizard.duration = Number(btn.dataset.value);
        renderDuration();
        renderCost();
        flash(btn);
      });
    });
  }

  function wireSound() {
    $('#soundToggle').addEventListener('click', () => {
      if (wizard.mode === '4k') {
        toast('В режиме 4K звук недоступен');
        return;
      }
      wizard.sound = !wizard.sound;
      renderSound();
    });
  }

  function wireImage() {
    const dz = $('#dropzone');
    const fi = $('#fileInput');
    const fname = $('#fileName');

    fi.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      wizard.imageFile = f.name;
      fname.textContent = f.name;
      fname.hidden = false;
      toast('Изображение прикреплено');
    });

    ['dragenter', 'dragover'].forEach((evt) =>
      dz.addEventListener(evt, (e) => {
        e.preventDefault();
        dz.classList.add('is-drag');
      })
    );
    ['dragleave', 'drop'].forEach((evt) =>
      dz.addEventListener(evt, (e) => {
        e.preventDefault();
        dz.classList.remove('is-drag');
      })
    );
    dz.addEventListener('drop', (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!f) return;
      fi.files = e.dataTransfer.files;
      fi.dispatchEvent(new Event('change'));
    });
  }

  function wirePrompt() {
    const ta = $('#prompt');
    ta.addEventListener('input', () => {
      wizard.prompt = ta.value;
      renderPromptCounter();
    });
  }

  function wireRun() {
    $('#runBtn').addEventListener('click', async () => {
      const cost = computeCost();
      if (cost > server.balance) {
        toast(`Нужно ещё ${cost - server.balance} генераций`);
        return;
      }
      if (!wizard.prompt.trim()) {
        toast('Опишите промпт');
        $('#prompt').focus();
        return;
      }
      $('#runBtn').disabled = true;
      try {
        const result = await api('/api/generations', {
          method: 'POST',
          body: {
            model: wizard.model,
            fmt: wizard.fmt,
            mode: wizard.mode,
            duration: wizard.duration,
            sound: wizard.sound,
            prompt: wizard.prompt,
          },
        });
        server.balance = result.balance;
        await refreshHistory();
        renderCost();
        renderBalanceScreen();
        renderHistory();
        toast(`Списано ${result.cost}. Остаток: ${result.balance}`);
      } catch (e) {
        toast(e.message || 'Не удалось запустить генерацию');
      } finally {
        $('#runBtn').disabled = false;
      }
    });
  }

  function wireTopup() {
    const apply = async (amount) => {
      try {
        const r = await api('/api/topup', { method: 'POST', body: { amount } });
        server.balance = r.balance;
        renderBalanceScreen();
        renderCost();
        renderHistory();
        toast(`+${amount} генераций`);
      } catch (e) {
        toast(e.message || 'Не удалось пополнить');
      }
    };
    $('#topupBtn').addEventListener('click', () => apply(100));
    $('#topup100').addEventListener('click', () => apply(100));
    $('#topup500').addEventListener('click', () => apply(500));
  }

  function wireModelChange() {
    const keys = Object.keys(MODELS);
    let idx = keys.indexOf(wizard.model);
    $('[data-action="change-model"]').addEventListener('click', () => {
      idx = (idx + 1) % keys.length;
      wizard.model = keys[idx];
      renderModelCard();
      toast(`Модель: ${MODELS[wizard.model].name}`);
    });
  }

  function wireExamples() {
    $('#prevBtn').addEventListener('click', () => {
      wizard.exampleIdx = (wizard.exampleIdx - 1 + EXAMPLES.length) % EXAMPLES.length;
      renderExample();
    });
    $('#nextBtn').addEventListener('click', () => {
      wizard.exampleIdx = (wizard.exampleIdx + 1) % EXAMPLES.length;
      renderExample();
    });
  }

  function wireNav() {
    $$('.app-bar__nav-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        showScreen(btn.dataset.nav);
      });
    });
    const close = () => {
      if (tg && typeof tg.close === 'function') tg.close();
    };
    const closeBtn = $('#closeBtnAppBar');
    if (closeBtn) closeBtn.addEventListener('click', close);
    const closeBtn2 = $('#closeBtn');
    if (closeBtn2) closeBtn2.addEventListener('click', close);
  }

  function wireReload() {
    const btn = $('#reloadBtn');
    if (btn) btn.addEventListener('click', () => loadServerState());
  }

  // -------- Help screen --------

  // Map doc key → API endpoint suffix
  const DOC_MAP = {
    'wizard-flow':     '/api/docs/wizard-flow',
    'bot-commands':    '/api/docs/bot-commands',
    'miniapp-api':     '/api/docs/miniapp-api',
    'init-data-auth':  '/api/docs/init-data-auth',
    'config':          '/api/docs/config',
  };

  function wireHelp() {
    $$('.help-topic').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const docKey = btn.dataset.doc;
        const url = API_BASE + (DOC_MAP[docKey] || '/api/docs');
        $('#helpTopics').hidden = true;
        $('#helpContent').hidden = false;
        $('#helpBody').textContent = 'Загрузка…';
        try {
          const r = await fetch(url);
          const d = r.ok ? await r.json() : { source: 'Ошибка загрузки: HTTP ' + r.status };
          // Collapse the text for display (don't show raw 50 KB of source)
          let text = d.source || String(d);
          if (text.length > 3000) text = text.slice(0, 3000) + '\n\n… (текст обрезан)';
          $('#helpBody').textContent = text;
        } catch (e) {
          $('#helpBody').textContent = 'Не удалось загрузить: ' + e.message;
        }
      });
    });

    $('#helpBackBtn').addEventListener('click', () => {
      $('#helpContent').hidden = true;
      $('#helpTopics').hidden = false;
    });
  }

  // -------- Server state --------

  async function refreshHistory() {
    try {
      const r = await api('/api/generations?limit=10');
      server.history = r.items || [];
    } catch (e) {
      // history is best-effort; don't blow up the screen
      console.warn('history refresh failed', e);
    }
  }

  async function loadServerState() {
    if (!isInTelegram()) {
      showFallback();
      return;
    }
    try {
      const me = await api('/api/me');
      server.user = me;
      server.balance = me.balance;
      await refreshHistory();
      renderAll();
    } catch (e) {
      toast('Не удалось загрузить профиль: ' + (e.message || e));
    }
  }

  function showFallback() {
    const fb = $('#fallback');
    if (fb) fb.hidden = false;
  }

  // -------- Init --------

  document.addEventListener('DOMContentLoaded', () => {
    renderAll();
    wireFormat();
    wireMode();
    wireDuration();
    wireSound();
    wireImage();
    wirePrompt();
    wireRun();
    wireTopup();
    wireModelChange();
    wireExamples();
    wireNav();
    wireReload();
    wireHelp();
    // Support ?screen=help (or any screen name) from URL param —
    // lets the bot's «❓ Справка» button deep-link into the right screen.
    const params = new URLSearchParams(window.location.search);
    const screenParam = params.get('screen');
    if (screenParam) {
      wizard.screen = screenParam;
    }
    loadServerState();
  });
})();
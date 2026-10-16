/**
 * WhisperJAV Web GUI - UI language switching (i18n engine)
 *
 * Design notes:
 * - Locale packs are plain JS files (locales/en.js, locales/zh-CN.js) that
 *   assign into window.I18N_STRINGS.  They are loaded with <script> tags
 *   BEFORE this file, so no fetch()/CORS is needed and the engine also works
 *   when the page is opened over file:// (dev_server.py).
 * - Static markup is translated through data-* attributes:
 *       data-i18n="key"               -> element.textContent
 *       data-i18n-html="key"          -> element.innerHTML (trusted packs only)
 *       data-i18n-title="key"         -> element.title
 *       data-i18n-placeholder="key"   -> element.placeholder
 *       data-i18n-aria="key"          -> element.setAttribute('aria-label')
 * - Dynamic strings in app.js use the global t(key, vars) with {name}
 *   placeholders, e.g. t('run.running').
 * - Persistence: the choice is saved through the backend
 *   (pywebview.api.save_gui_settings({uiLanguage: code})) because the GUI
 *   runs with private_mode=True (localStorage does not survive a session,
 *   see webview_gui/main.py).  localStorage is only a same-session cache.
 * - Fallback chain: current pack -> English pack -> the key itself, so a
 *   missing translation degrades to English instead of showing a raw key.
 */
window.I18N_STRINGS = window.I18N_STRINGS || {};

const I18N = {
    LANGS: [
        { code: 'en',    label: 'English' },
        { code: 'zh-CN', label: '中文（简体）' }
    ],
    DEFAULT: 'en',
    STORAGE_KEY: 'wj_ui_language',
    current: 'en',

    /** Translate a key. vars is an optional {name: value} map for {name} slots. */
    t(key, vars) {
        const pack = window.I18N_STRINGS[this.current] || {};
        let str = Object.prototype.hasOwnProperty.call(pack, key)
            ? pack[key]
            : (window.I18N_STRINGS[this.DEFAULT] || {})[key];
        if (str === undefined) return key;
        if (vars) {
            str = str.replace(/\{(\w+)\}/g, (m, name) =>
                (Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : m));
        }
        return str;
    },

    /** Apply the current language to every [data-i18n*] element under root. */
    apply(root) {
        const scope = root || document;
        scope.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const v = this.t(key);
            if (v === key) return;
            if (el.tagName === 'OPTGROUP') {
                // <optgroup> shows its `label` attribute, not its text content
                el.setAttribute('label', v);
            } else {
                el.textContent = v;
            }
        });
        scope.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            const v = this.t(key);
            if (v !== key) el.innerHTML = v;
        });
        scope.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            const v = this.t(key);
            if (v !== key) el.title = v;
        });
        scope.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const v = this.t(key);
            if (v !== key) el.placeholder = v;
        });
        scope.querySelectorAll('[data-i18n-aria]').forEach(el => {
            const key = el.getAttribute('data-i18n-aria');
            const v = this.t(key);
            if (v !== key) el.setAttribute('aria-label', v);
        });
        document.documentElement.setAttribute('lang',
            this.current === 'zh-CN' ? 'zh-CN' : 'en');
    },

    /** Resolve the best initial language without the backend. */
    detect() {
        try {
            const cached = localStorage.getItem(this.STORAGE_KEY);
            if (cached && this.isSupported(cached)) return cached;
        } catch (e) { /* private mode / storage disabled */ }
        const nav = (navigator.language || '').toLowerCase();
        if (nav.startsWith('zh')) return 'zh-CN';
        return this.DEFAULT;
    },

    isSupported(code) {
        return this.LANGS.some(l => l.code === code);
    },

    /** Switch language, re-translate the DOM and persist through the backend. */
    async setLang(code, opts = {}) {
        if (!this.isSupported(code)) code = this.DEFAULT;
        const changed = code !== this.current;
        this.current = code;
        try { localStorage.setItem(this.STORAGE_KEY, code); } catch (e) { /* ignore */ }
        this.apply();
        this._syncMenu();
        if (changed && opts.persist !== false) {
            try {
                if (window.pywebview?.api?.save_gui_settings) {
                    await pywebview.api.save_gui_settings({ uiLanguage: code });
                }
            } catch (e) {
                console.warn('Could not persist UI language:', e);
            }
        }
        return changed;
    },

    /** Reflect the active language in the header menu (aria-checked + check). */
    _syncMenu() {
        document.querySelectorAll('#langMenu .lang-option').forEach(opt => {
            const active = opt.dataset.lang === this.current;
            opt.classList.toggle('checked', active);
            opt.setAttribute('aria-checked', active ? 'true' : 'false');
        });
    },

    init() {
        this.current = this.detect();
        this.apply();
        this._syncMenu();
    }
};

// Global shorthand for dynamic strings in app.js: t('key', {name: value})
function t(key, vars) { return I18N.t(key, vars); }

// ============================================================
// Language Manager (header menu wiring, mirrors ThemeManager)
// ============================================================
const LanguageManager = {
    init() {
        // Apply the best guess immediately (localStorage cache / navigator) so
        // a Chinese user does not see an English flash before pywebviewready.
        // The persisted backend choice overrides this in applyBackendLanguage().
        I18N.init();

        const btn = document.getElementById('langBtn');
        const menu = document.getElementById('langMenu');
        if (btn && menu) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const themeMenu = document.getElementById('themeMenu');
                if (themeMenu) themeMenu.classList.remove('active');
                menu.classList.toggle('active');
                if (menu.classList.contains('active')) {
                    const first = menu.querySelector('.lang-option');
                    if (first) first.focus();
                }
            });

            document.addEventListener('click', (e) => {
                if (menu.classList.contains('active')) menu.classList.remove('active');
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && menu.classList.contains('active')) {
                    menu.classList.remove('active');
                }
            });

            menu.querySelectorAll('.lang-option').forEach(opt => {
                opt.addEventListener('click', async () => {
                    menu.classList.remove('active');
                    await I18N.setLang(opt.dataset.lang);
                });
            });
        }
        I18N._syncMenu();
    },

    /** Called from the pywebviewready handler once backend settings arrive. */
    async applyBackendLanguage(savedCode) {
        if (savedCode && I18N.isSupported(savedCode)) {
            await I18N.setLang(savedCode);
        } else {
            I18N.init();
        }
    }
};

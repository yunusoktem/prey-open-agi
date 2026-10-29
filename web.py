import os
import logging
from flask import Flask, request, render_template_string
from markupsafe import Markup, escape
import markdown
import bleach

from analiz import (
    LANGUAGES,
    webde_ara,
    kayitli_proje_getir,
    ai_analizi,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union({
    "p", "h1", "h2", "h3", "h4", "hr", "pre", "code",
    "blockquote", "ul", "ol", "li", "strong", "em",
    "table", "thead", "tbody", "tr", "th", "td",
    "del", "input", "sup", "sub",
})

ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "target", "rel"],
    "code": ["class"],
    "input": ["type", "checked", "disabled"],
}


def render_report(text):
    """Markdown raporunu güvenli HTML'e dönüştürür."""
    html = markdown.markdown(
        text or "",
        extensions=["extra", "nl2br", "sane_lists"],
    )
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
    )
    return Markup(clean_html)


HTML = r"""
<!DOCTYPE html>
<html lang="tr" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0b1020">
    <title>Prey Open AGI — AI Research</title>
    <style>
        :root {
            color-scheme: dark;
            --bg: #0b1020;
            --surface: #11182b;
            --surface-2: #172039;
            --surface-3: #1d2945;
            --text: #edf1ff;
            --muted: #a0abc5;
            --border: #293552;
            --accent: #9385ff;
            --accent-2: #65b8ff;
            --button-text: #0b1020;
            --input-bg: #0d1426;
            --shadow: 0 18px 50px rgba(0, 0, 0, .18);
        }

        html[data-theme="light"] {
            color-scheme: light;
            --bg: #f4f6fb;
            --surface: #ffffff;
            --surface-2: #f0f2fa;
            --surface-3: #e6e9f5;
            --text: #182039;
            --muted: #626d86;
            --border: #dce1ee;
            --accent: #6654dc;
            --accent-2: #267acb;
            --button-text: #ffffff;
            --input-bg: #ffffff;
            --shadow: 0 15px 40px rgba(29, 42, 75, .07);
        }

        * { box-sizing: border-box; }

        html {
            scroll-behavior: smooth;
        }

        body {
            margin: 0;
            min-height: 100vh;
            background:
                radial-gradient(
                    ellipse at 50% -15%,
                    color-mix(in srgb, var(--accent) 13%, transparent),
                    transparent 55%
                ),
                var(--bg);
            color: var(--text);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                         BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.65;
            transition: background-color .2s, color .2s;
        }

        button, input, select { font: inherit; }

        button, a, input, select {
            -webkit-tap-highlight-color: transparent;
        }

        .container {
            width: min(1080px, calc(100% - 36px));
            margin: 0 auto;
        }

        header {
            border-bottom: 1px solid var(--border);
            background: color-mix(in srgb, var(--bg) 88%, transparent);
        }

        .nav {
            min-height: 76px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .brand-icon {
            width: 42px;
            height: 42px;
            flex-shrink: 0;
            display: grid;
            place-items: center;
            border: 1px solid color-mix(in srgb, var(--accent) 55%, var(--border));
            border-radius: 14px;
            background: color-mix(in srgb, var(--accent) 13%, var(--surface));
            color: var(--accent);
            font-size: 22px;
            font-weight: 800;
        }

        .brand-name {
            font-weight: 800;
            font-size: 17px;
            letter-spacing: -.45px;
            line-height: 1.25;
        }

        .brand-subtitle {
            margin-top: 4px;
            font-size: 11px;
            color: var(--muted);
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .theme-toggle {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 9px;
            min-height: 42px;
            padding: 9px 14px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
            white-space: nowrap;
            transition: background .2s, border-color .2s, transform .2s;
        }

        .theme-toggle:hover {
            background: var(--surface-2);
            border-color: var(--accent);
        }

        .theme-toggle:active { transform: scale(.98); }

        .nav-actions {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 10px;
            flex-shrink: 0;
        }

        .language-menu {
            position: relative;
        }

        .language-toggle {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            min-height: 42px;
            padding: 9px 12px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
            white-space: nowrap;
        }

        .language-toggle:hover,
        .language-toggle[aria-expanded="true"] {
            border-color: var(--accent);
            background: var(--surface-2);
        }

        .language-dropdown {
            position: absolute;
            z-index: 20;
            top: calc(100% + 10px);
            right: 0;
            width: 210px;
            padding: 6px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: var(--shadow);
        }

        .language-dropdown[hidden] { display: none; }

        .language-option {
            display: flex;
            align-items: center;
            gap: 10px;
            width: 100%;
            padding: 10px 12px;
            border: 0;
            border-radius: 9px;
            background: transparent;
            color: var(--text);
            text-align: left;
            cursor: pointer;
            font-size: 13px;
        }

        .language-option:hover,
        .language-option[aria-checked="true"] {
            background: var(--surface-2);
        }

        .language-option .language-check {
            margin-left: auto;
            color: var(--accent);
            font-weight: 800;
        }

        main { padding: 58px 0 80px; }

        .hero {
            text-align: center;
            max-width: 760px;
            margin: 0 auto 36px;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface);
            color: var(--accent);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .4px;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #39c99a;
            box-shadow: 0 0 12px rgba(57, 201, 154, .45);
        }

        h1 {
            margin: 22px 0 12px;
            font-size: clamp(34px, 6vw, 55px);
            line-height: 1.1;
            letter-spacing: -2px;
        }

        .gradient-text {
            background: linear-gradient(110deg, var(--accent), var(--accent-2));
            background-clip: text;
            -webkit-background-clip: text;
            color: transparent;
        }

        .hero p {
            max-width: 620px;
            margin: 0 auto;
            color: var(--muted);
            font-size: 16px;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 26px;
            box-shadow: var(--shadow);
        }

        .panel-heading {
            margin: 0 0 6px;
            font-size: 19px;
            letter-spacing: -.3px;
        }

        .panel-description {
            margin: 0 0 22px;
            color: var(--muted);
            font-size: 13px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 190px;
            gap: 16px;
            align-items: end;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: var(--text);
            font-size: 13px;
            font-weight: 700;
        }

        input[type="text"], select {
            width: 100%;
            min-height: 48px;
            padding: 12px 14px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--input-bg);
            color: var(--text);
            outline: none;
        }

        input::placeholder { color: var(--muted); opacity: .8; }

        input:focus, select:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 17%, transparent);
        }

        .submit-button {
            display: flex;
            width: 100%;
            min-height: 49px;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 18px;
            padding: 13px 18px;
            border: 0;
            border-radius: 12px;
            background: linear-gradient(110deg, var(--accent), var(--accent-2));
            color: #fff;
            font-weight: 800;
            cursor: pointer;
            transition: filter .2s, transform .2s;
        }

        .submit-button:hover { filter: brightness(1.08); }
        .submit-button:active { transform: scale(.99); }

        .hint {
            margin: 12px 0 0;
            color: var(--muted);
            font-size: 12px;
        }

        .results { margin-top: 28px; }

        .section-title {
            margin: 0 0 16px;
            font-size: 22px;
            letter-spacing: -.5px;
        }

        .report {
            padding: clamp(20px, 4vw, 36px);
            overflow-wrap: anywhere;
        }

        .report h1, .report h2, .report h3, .report h4 {
            text-align: left;
            letter-spacing: -.4px;
            line-height: 1.35;
            margin: 1.6em 0 .6em;
        }

        .report h1 { font-size: 28px; }
        .report h2 {
            font-size: 23px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }
        .report h3 { font-size: 18px; }
        .report h4 { font-size: 16px; }

        .report h1:first-child, .report h2:first-child { margin-top: 0; }

        .report p, .report li { color: var(--text); }

        .report a {
            color: var(--accent-2);
            overflow-wrap: anywhere;
        }

        .report blockquote {
            margin: 18px 0;
            padding: 12px 18px;
            border-left: 3px solid var(--accent);
            background: var(--surface-2);
            color: var(--muted);
        }

        .report pre {
            overflow-x: auto;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--input-bg);
        }

        .report code {
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            font-size: .9em;
        }

        .report :not(pre) > code {
            padding: 2px 5px;
            border-radius: 5px;
            background: var(--surface-3);
        }

        .report table {
            width: 100%;
            display: block;
            overflow-x: auto;
            border-collapse: collapse;
        }

        .report th, .report td {
            padding: 10px 12px;
            border: 1px solid var(--border);
            text-align: left;
        }

        .report th { background: var(--surface-2); }

        .sources {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .source-card {
            min-width: 0;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--surface);
            transition: border-color .2s, background .2s;
        }

        .source-card:hover {
            border-color: var(--accent);
            background: var(--surface-2);
        }

        .source-card a {
            color: var(--text);
            font-weight: 750;
            text-decoration: none;
            overflow-wrap: anywhere;
        }

        .source-card a:hover { color: var(--accent); }

        .source-card p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 13px;
            overflow-wrap: anywhere;
        }

        .source-url {
            display: block;
            margin-top: 8px;
            color: var(--accent-2);
            font-size: 11px;
            overflow-wrap: anywhere;
        }

        .error {
            margin-top: 20px;
            padding: 15px 18px;
            border: 1px solid #d46b78;
            border-radius: 12px;
            background: color-mix(in srgb, #d46b78 10%, var(--surface));
            color: var(--text);
        }

        .count {
            display: inline-flex;
            padding: 4px 10px;
            margin-left: 6px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface-2);
            color: var(--accent);
            font-size: 12px;
            font-weight: 750;
            vertical-align: middle;
        }

        footer {
            padding: 22px 0;
            border-top: 1px solid var(--border);
            color: var(--muted);
            text-align: center;
            font-size: 12px;
        }

        @media (max-width: 640px) {
            .container { width: min(100% - 24px, 1080px); }
            .nav { min-height: 68px; gap: 10px; }
            .brand-icon { width: 36px; height: 36px; }
            .brand-name { font-size: 14px; }
            .brand-subtitle { font-size: 9px; letter-spacing: 1px; }
            .nav-actions { gap: 6px; }
            .theme-toggle { padding: 9px 10px; font-size: 12px; }
            .language-toggle { padding: 9px 10px; font-size: 12px; }
            .language-dropdown { width: 190px; }
            main { padding-top: 38px; }
            .hero p { font-size: 14px; }
            .panel { padding: 18px; border-radius: 17px; }
            .form-grid, .sources { grid-template-columns: 1fr; }
            .form-grid { gap: 14px; }
            .submit-button { margin-top: 16px; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }
        }
    </style>

    <script>
        (function () {
            try {
                const saved = localStorage.getItem("prey-theme");
                const theme = saved === "light" ? "light" : "dark";
                document.documentElement.dataset.theme = theme;
            } catch (e) {
                document.documentElement.dataset.theme = "dark";
            }
        })();
    </script>
</head>

<body>
<header>
    <div class="container nav">
        <div class="brand">
            <div class="brand-icon" aria-hidden="true">P</div>
            <div>
                <div class="brand-name">Prey Open AGI</div>
                <div class="brand-subtitle">Open Research Intelligence</div>
            </div>
        </div>

        <div class="nav-actions">
            <div class="language-menu" id="languageMenu">
                <button
                    type="button"
                    class="language-toggle"
                    id="languageToggle"
                    aria-haspopup="true"
                    aria-expanded="false"
                    aria-controls="languageDropdown"
                >
                    <span aria-hidden="true">◎</span>
                    <span id="currentLanguageLabel">{{ languages.get(dil, "Türkçe") }}</span>
                    <span aria-hidden="true">⌄</span>
                </button>
                <div class="language-dropdown" id="languageDropdown" role="group" aria-label="Rapor dili" hidden>
                    {% for code, name in languages.items() %}
                    <button
                        type="button"
                        class="language-option"
                        data-language="{{ code }}"
                        data-language-name="{{ name }}"
                        role="radio"
                        aria-checked="{{ 'true' if code == dil else 'false' }}"
                    >
                        <span aria-hidden="true">{% if code == 'tr' %}🇹🇷{% elif code == 'en' %}🇬🇧{% elif code == 'es' %}🇪🇸{% elif code == 'pt' %}🇵🇹{% elif code == 'zh' %}🇨🇳{% elif code == 'ru' %}🇷🇺{% else %}🌐{% endif %}</span>
                        <span>{{ name }}</span>
                        <span class="language-check">{% if code == dil %}✓{% endif %}</span>
                    </button>
                    {% endfor %}
                </div>
            </div>
            <button
                type="button"
                class="theme-toggle"
                id="themeToggle"
                aria-label="Gündüz moduna geç"
                aria-pressed="false"
            >
                <span id="themeIcon" aria-hidden="true">☀</span>
                <span id="themeLabel">Gündüz</span>
            </button>
        </div>
    </div>
</header>

<main class="container">
    <section class="hero">
        <div class="eyebrow">
            <span class="status-dot"></span>
            Open-source AI research
        </div>
        <h1>Explore the <span class="gradient-text">Open Intelligence</span></h1>
        <p>
            Projeleri araştır, teknik kaynakları keşfet ve yapay zekâ
            destekli analiz raporlarını tek bir yerde oluştur.
        </p>
    </section>

    <section class="panel" aria-labelledby="searchTitle">
        <h2 class="panel-heading" id="searchTitle">Proje araştırması</h2>
        <p class="panel-description">
            Projenin adını gir ve araştırma raporunu oluştur.
        </p>

        <form method="POST" action="/" id="researchForm">
            <div class="form-grid">
                <div>
                    <label for="proje_adi">Proje adı veya araştırma konusu</label>
                    <input
                        type="text"
                        id="proje_adi"
                        name="proje_adi"
                        placeholder="Örn. Sentient Foundation"
                        value="{{ proje_adi }}"
                        required
                        maxlength="200"
                        autocomplete="off"
                    >
                </div>

                <input type="hidden" id="dil" name="dil" value="{{ dil }}">
            </div>

            <button type="submit" class="submit-button" id="submitButton">
                <span aria-hidden="true">⌕</span>
                <span id="submitLabel">Araştırmayı başlat</span>
            </button>
            <p class="hint">
                Analiz, erişilebilen kaynaklara dayanır. Doğrulanamayan
                bilgiler raporda ayrıca belirtilmelidir.
            </p>
        </form>
    </section>

    {% if hata %}
        <div class="error" role="alert">{{ hata }}</div>
    {% endif %}

    {% if rapor %}
        <section class="results" aria-labelledby="reportTitle">
            <h2 class="section-title" id="reportTitle">
                Araştırma raporu
                <span class="count">{{ kaynaklar|length }} kaynak</span>
            </h2>
            <article class="panel report">
                {{ rapor }}
            </article>
        </section>
    {% endif %}

    {% if kaynaklar %}
        <section class="results" aria-labelledby="sourcesTitle">
            <h2 class="section-title" id="sourcesTitle">
                Araştırma kaynakları
                <span class="count">{{ kaynaklar|length }}</span>
            </h2>

            <div class="sources">
                {% for kaynak in kaynaklar %}
                    <article class="source-card">
                        <a href="{{ kaynak.url }}"
                           target="_blank"
                           rel="noopener noreferrer">
                            {{ kaynak.baslik or kaynak.url }}
                        </a>

                        {% if kaynak.aciklama %}
                            <p>{{ kaynak.aciklama }}</p>
                        {% endif %}

                        <span class="source-url">{{ kaynak.url }}</span>
                    </article>
                {% endfor %}
            </div>
        </section>
    {% endif %}
</main>

<footer>
    <div class="container">
        Prey Open AGI · Open-source research intelligence
    </div>
</footer>

<script>
    (function () {
        const root = document.documentElement;
        const button = document.getElementById("themeToggle");
        const icon = document.getElementById("themeIcon");
        const label = document.getElementById("themeLabel");
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        const languageMenu = document.getElementById("languageMenu");
        const languageToggle = document.getElementById("languageToggle");
        const languageDropdown = document.getElementById("languageDropdown");
        const currentLanguageLabel = document.getElementById("currentLanguageLabel");
        const languageInput = document.getElementById("dil");
        const languageOptions = Array.from(
            document.querySelectorAll(".language-option")
        );

        function closeLanguageMenu() {
            languageDropdown.hidden = true;
            languageToggle.setAttribute("aria-expanded", "false");
        }

        languageToggle.addEventListener("click", function () {
            const willOpen = languageDropdown.hidden;
            languageDropdown.hidden = !willOpen;
            languageToggle.setAttribute("aria-expanded", String(willOpen));
        });

        languageOptions.forEach(function (option) {
            option.addEventListener("click", function () {
                const selectedCode = option.dataset.language;
                languageInput.value = selectedCode;
                currentLanguageLabel.textContent = option.dataset.languageName;

                languageOptions.forEach(function (item) {
                    const selected = item === option;
                    item.setAttribute("aria-checked", String(selected));
                    item.querySelector(".language-check").textContent =
                        selected ? "✓" : "";
                });

                closeLanguageMenu();
            });
        });

        document.addEventListener("click", function (event) {
            if (!languageMenu.contains(event.target)) {
                closeLanguageMenu();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeLanguageMenu();
                languageToggle.focus();
            }
        });

        function updateThemeButton(theme) {
            const isDark = theme === "dark";
            icon.textContent = isDark ? "☀" : "☾";
            label.textContent = isDark ? "Gündüz" : "Gece";
            button.setAttribute(
                "aria-label",
                isDark ? "Gündüz moduna geç" : "Gece moduna geç"
            );
            button.setAttribute("aria-pressed", String(!isDark));

            if (metaTheme) {
                metaTheme.setAttribute(
                    "content",
                    isDark ? "#0b1020" : "#f4f6fb"
                );
            }
        }

        function setTheme(theme) {
            root.dataset.theme = theme;
            updateThemeButton(theme);

            try {
                localStorage.setItem("prey-theme", theme);
            } catch (e) {
                // Depolama kapalıysa tema geçişi yine çalışır.
            }
        }

        updateThemeButton(root.dataset.theme || "dark");

        button.addEventListener("click", function () {
            const current = root.dataset.theme || "dark";
            setTheme(current === "dark" ? "light" : "dark");
        });

        const form = document.getElementById("researchForm");
        const submitButton = document.getElementById("submitButton");
        const submitLabel = document.getElementById("submitLabel");

        form.addEventListener("submit", function () {
            submitButton.disabled = true;
            submitButton.style.opacity = ".75";
            submitLabel.textContent = "Araştırılıyor...";
        });
    })();
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    proje_adi = ""
    dil = "tr"
    rapor = None
    kaynaklar = []
    hata = None

    if request.method == "POST":
        proje_adi = request.form.get("proje_adi", "").strip()
        dil = request.form.get("dil", "tr").strip()

        if dil not in LANGUAGES:
            dil = "tr"

        if not proje_adi:
            hata = "Lütfen bir proje adı veya araştırma konusu gir."
        else:
            try:
                proje_verisi = kayitli_proje_getir(proje_adi)

                try:
                    kaynaklar = webde_ara(proje_adi)
                    if not isinstance(kaynaklar, list):
                        kaynaklar = []
                except Exception:
                    logger.exception("Web araştırması başarısız.")
                    kaynaklar = []

                try:
                    rapor_metni = ai_analizi(
                        proje_adi,
                        proje_verisi=proje_verisi,
                        arama_sonuclari=kaynaklar,
                        dil=dil,
                    )
                    rapor = render_report(rapor_metni)
                except Exception:
                    logger.exception("AI analizi başarısız.")
                    hata = (
                        "Analiz oluşturulamadı. Fortytwo API anahtarını, "
                        "bağlantıyı ve sunucu günlüklerini kontrol et."
                    )

                if not kaynaklar and not hata:
                    hata = (
                        "Arama sonuçları alınamadı. İnternet bağlantısını "
                        "ve ücretsiz arama sağlayıcısını kontrol et."
                    )

            except Exception:
                logger.exception("Araştırma isteği işlenemedi.")
                hata = "İstek işlenirken bir hata oluştu. Sunucu günlüklerini kontrol et."

    return render_template_string(
        HTML,
        proje_adi=proje_adi,
        dil=dil,
        languages=LANGUAGES,
        rapor=rapor,
        kaynaklar=kaynaklar,
        hata=hata,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

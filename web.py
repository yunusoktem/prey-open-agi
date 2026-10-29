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
    github_gelisim_verisi,
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
            --bg: #08131d;
            --surface: #0f202c;
            --surface-2: #142b39;
            --surface-3: #1b3948;
            --text: #edf1ff;
            --muted: #a0abc5;
            --border: #254252;
            --accent: #39d6c4;
            --accent-2: #65aaff;
            --button-text: #0b1020;
            --input-bg: #0b1a25;
            --shadow: 0 18px 50px rgba(0, 0, 0, .18);
        }

        html[data-theme="light"] {
            color-scheme: light;
            --bg: #f3f7f8;
            --surface: #ffffff;
            --surface-2: #eaf2f4;
            --surface-3: #dcebed;
            --text: #182039;
            --muted: #626d86;
            --border: #d4e2e5;
            --accent: #087f8c;
            --accent-2: #245fbd;
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

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 0 0 28px;
        }
        .feature-card {
            padding: 19px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: linear-gradient(145deg, var(--surface), var(--surface-2));
        }
        .feature-icon {
            display: grid; place-items: center; width: 38px; height: 38px;
            margin-bottom: 12px; border-radius: 12px;
            background: color-mix(in srgb, var(--accent) 14%, var(--surface));
            color: var(--accent); font-size: 18px; font-weight: 800;
        }
        .feature-card h3 { margin: 0 0 6px; font-size: 14px; }
        .feature-card p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.6; }
        .hero { padding: 10px 0 4px; }
        .hero h1 { max-width: 800px; margin-left: auto; margin-right: auto; }
        .hero p { max-width: 650px; }

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


        .github-panel { margin-top: 28px; }
        .github-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: wrap;
            margin-bottom: 18px;
        }
        .github-repo-link { color: var(--accent-2); text-decoration: none; font-weight: 800; }
        .github-repo-link:hover { text-decoration: underline; }
        .github-description { margin: 6px 0 0; color: var(--muted); font-size: 13px; }
        .github-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 18px 0;
        }
        .github-metric {
            min-width: 0;
            padding: 14px;
            border: 1px solid var(--border);
            border-radius: 13px;
            background: var(--surface-2);
        }
        .github-metric-label { color: var(--muted); font-size: 11px; }
        .github-metric-value { margin-top: 4px; font-size: 20px; font-weight: 800; overflow-wrap: anywhere; }
        .github-meta { color: var(--muted); font-size: 12px; }
        .commit-list { display: grid; gap: 9px; margin-top: 14px; }
        .commit-item {
            padding: 12px 14px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--input-bg);
        }
        .commit-item a { color: var(--text); text-decoration: none; font-weight: 650; }
        .commit-item a:hover { color: var(--accent-2); }
        .commit-date { color: var(--muted); font-size: 11px; margin-top: 4px; }
        .github-note { color: var(--muted); font-size: 12px; margin: 14px 0 0; }

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
            .form-grid, .sources, .feature-grid { grid-template-columns: 1fr; }
            .github-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
                <div class="brand-subtitle" id="brandSubtitle">Open Research Intelligence</div>
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
                <div class="language-dropdown" id="languageDropdown" role="group" aria-label="Site ve rapor dili" hidden>
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
            <span id="heroEyebrow">OPEN-SOURCE AI RESEARCH</span>
        </div>
        <h1 id="heroTitle">Explore the <span class="gradient-text">Open Intelligence</span></h1>
        <p id="heroDescription">Open AGI projelerini; teknik kaynaklar, gerçek geliştirme sinyalleri ve kaynak gösteren AI analiziyle tek yerde araştır.</p>
    </section>

    <section class="feature-grid" aria-label="Platform özellikleri">
        <article class="feature-card"><div class="feature-icon" aria-hidden="true">⌕</div><h3 id="featureResearchTitle">Canlı kaynak araştırması</h3><p id="featureResearchText">Resmî siteler, dokümantasyon, duyurular ve kaynak bağlantıları tek raporda.</p></article>
        <article class="feature-card"><div class="feature-icon" aria-hidden="true">↗</div><h3 id="featureGithubTitle">GitHub geliştirme sinyalleri</h3><p id="featureGithubText">Stars, forks, son commitler ve sürüm bilgileriyle açık geliştirme etkinliğini incele.</p></article>
        <article class="feature-card"><div class="feature-icon" aria-hidden="true">◎</div><h3 id="featureEvidenceTitle">Kanıta dayalı analiz</h3><p id="featureEvidenceText">Teknik yapı, ürün ilerlemesi, token ekonomisi ve riskleri kaynaklarla birlikte değerlendir.</p></article>
    </section>

    <section class="panel" aria-labelledby="searchTitle">
        <h2 class="panel-heading" id="searchTitle">Proje araştırması</h2>
        <p class="panel-description" id="searchDescription">Proje adını gir; web kaynaklarını, GitHub geliştirme verilerini ve AI analizini bir arada incele.</p>

        <form method="POST" action="/" id="researchForm">
            <div class="form-grid">
                <div>
                    <label for="proje_adi" id="projectLabel">Proje adı veya araştırma konusu</label>
                    <input
                        type="text"
                        id="proje_adi"
                        name="proje_adi"
                        placeholder="Örn. Sentient Foundation" id="projectInput"
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
            <p class="hint" id="researchHint">Analiz erişilebilen kaynaklara dayanır. Proje adıyla eşleşmeyen GitHub depoları olası eşleşme olarak işaretlenir.</p>
        </form>
    </section>

    {% if hata %}
        <div class="error" role="alert">{{ hata }}</div>
    {% endif %}

    {% if github_veri %}
        <section class="panel github-panel results" aria-labelledby="githubTitle">
            <div class="github-head">
                <div>
                    <h2 class="panel-heading" id="githubTitle">GitHub gelişim özeti</h2>
                    <a class="github-repo-link" href="{{ github_veri.url }}" target="_blank" rel="noopener noreferrer">
                        {{ github_veri.name }} ↗
                    </a>
                    <p class="github-description">{{ github_veri.description }}</p>
                </div>
                <div class="github-meta">
                    {% if github_veri.is_exact_match %}
                        Depo adı proje adıyla eşleşiyor
                    {% else %}
                        Olası eşleşme — doğruluğunu kontrol et
                    {% endif %}
                </div>
            </div>

            <div class="github-metrics">
                <div class="github-metric">
                    <div class="github-metric-label" id="githubStarsLabel">Stars</div>
                    <div class="github-metric-value">{{ "{:,}".format(github_veri.stars).replace(",", " ") }}</div>
                </div>
                <div class="github-metric">
                    <div class="github-metric-label" id="githubForksLabel">Forks</div>
                    <div class="github-metric-value">{{ "{:,}".format(github_veri.forks).replace(",", " ") }}</div>
                </div>
                <div class="github-metric">
                    <div class="github-metric-label" id="githubIssuesLabel">Açık issue / PR sayacı*</div>
                    <div class="github-metric-value">{{ "{:,}".format(github_veri.open_issues).replace(",", " ") }}</div>
                </div>
                <div class="github-metric">
                    <div class="github-metric-label" id="githubLanguageLabel">Ana dil</div>
                    <div class="github-metric-value" style="font-size:16px">{{ github_veri.language }}</div>
                </div>
            </div>

            <div class="github-meta">
                Oluşturulma: {{ github_veri.created_at or "Bilinmiyor" }} ·
                Son push: {{ github_veri.pushed_at or "Bilinmiyor" }} ·
                GitHub kayıt güncellemesi: {{ github_veri.updated_at or "Bilinmiyor" }}
                {% if github_veri.latest_release %}
                    <br>Son sürüm:
                    <a class="github-repo-link" href="{{ github_veri.latest_release.url }}" target="_blank" rel="noopener noreferrer">
                        {{ github_veri.latest_release.tag or github_veri.latest_release.name }}
                    </a>
                    ({{ github_veri.latest_release.date or "tarih yok" }})
                {% else %}
                    <br>Son sürüm: GitHub Releases üzerinden doğrulanamadı.
                {% endif %}
            </div>

            {% if github_veri.commits %}
                <h3 class="panel-heading" id="commitsTitle" style="margin-top:24px">Son commitler</h3>
                <div class="commit-list">
                    {% for commit in github_veri.commits %}
                        <div class="commit-item">
                            <a href="{{ commit.url }}" target="_blank" rel="noopener noreferrer">{{ commit.message }}</a>
                            <div class="commit-date">{{ commit.date or "Tarih yok" }} · {{ commit.author }}</div>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <p class="github-note">Son commit bilgileri alınamadı veya depo herkese açık değil.</p>
            {% endif %}

            <p class="github-note">
                * GitHub'ın open_issues_count alanı bazı depolarda açık pull request'leri de içerebilir.
                Aktivite göstergeleri tek başına yazılım kalitesini veya projenin sürdürülebilirliğini kanıtlamaz.
                Veriler GitHub API'sinden araştırma sırasında alınır; bu ilk sürüm geçmiş ölçümleri henüz saklamaz.
            </p>
        </section>
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
        Prey Open AGI · <span id="footerText">Open-source research intelligence</span>
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

        const UI_TEXT = {
            tr: { stars:"Stars", forks:"Forks", issues:"Açık issue / PR sayacı*", mainLanguage:"Ana dil", commits:"Son commitler", brandSubtitle:"Açık Araştırma Zekâsı", eyebrow:"AÇIK KAYNAKLI AI ARAŞTIRMASI", heroTitle:"Açık Zekâyı Keşfet", heroDescription:"Open AGI projelerini; teknik kaynaklar, gerçek geliştirme sinyalleri ve kaynak gösteren AI analiziyle tek yerde araştır.", featureResearchTitle:"Canlı kaynak araştırması", featureResearchText:"Resmî siteler, dokümantasyon, duyurular ve kaynak bağlantıları tek raporda.", featureGithubTitle:"GitHub geliştirme sinyalleri", featureGithubText:"Stars, forks, son commitler ve sürüm bilgileriyle açık geliştirme etkinliğini incele.", featureEvidenceTitle:"Kanıta dayalı analiz", featureEvidenceText:"Teknik yapı, ürün ilerlemesi, token ekonomisi ve riskleri kaynaklarla birlikte değerlendir.", searchTitle:"Proje araştırması", searchDescription:"Proje adını gir; web kaynaklarını, GitHub geliştirme verilerini ve AI analizini bir arada incele.", projectLabel:"Proje adı veya araştırma konusu", placeholder:"Örn. Sentient Foundation", submit:"Araştırmayı başlat", loading:"Araştırılıyor...", hint:"Analiz erişilebilen kaynaklara dayanır. Proje adıyla eşleşmeyen GitHub depoları olası eşleşme olarak işaretlenir.", reportTitle:"Araştırma raporu", sourcesTitle:"Araştırma kaynakları", githubTitle:"GitHub gelişim özeti", themeDark:"Gündüz", themeLight:"Gece", themeDarkAria:"Gündüz moduna geç", themeLightAria:"Gece moduna geç", errorEmpty:"Lütfen bir proje adı veya araştırma konusu gir.", footer:"Açık kaynak araştırma zekâsı" },
            en: { stars:"Stars", forks:"Forks", issues:"Open issues / PRs*", mainLanguage:"Primary language", commits:"Recent commits", brandSubtitle:"Open Research Intelligence", eyebrow:"OPEN-SOURCE AI RESEARCH", heroTitle:"Explore Open Intelligence", heroDescription:"Research Open AGI projects in one place with technical sources, real development signals, and cited AI analysis.", featureResearchTitle:"Live source research", featureResearchText:"Official websites, documentation, announcements, and source links in one report.", featureGithubTitle:"GitHub development signals", featureGithubText:"Review public development activity through stars, forks, recent commits, and releases.", featureEvidenceTitle:"Evidence-based analysis", featureEvidenceText:"Assess technical design, product progress, token economics, and risks with sources.", searchTitle:"Project research", searchDescription:"Enter a project name to review web sources, GitHub development data, and AI analysis together.", projectLabel:"Project name or research topic", placeholder:"e.g. Sentient Foundation", submit:"Start research", loading:"Researching...", hint:"Analysis is based on accessible sources. GitHub repositories that may not match the project are marked as possible matches.", reportTitle:"Research report", sourcesTitle:"Research sources", githubTitle:"GitHub development overview", themeDark:"Light mode", themeLight:"Dark mode", themeDarkAria:"Switch to light mode", themeLightAria:"Switch to dark mode", errorEmpty:"Enter a project name or research topic.", footer:"Open-source research intelligence" },
            es: { stars:"Stars", forks:"Forks", issues:"Issues / PR abiertos*", mainLanguage:"Lenguaje principal", commits:"Commits recientes", brandSubtitle:"Inteligencia de investigación abierta", eyebrow:"INVESTIGACIÓN DE IA DE CÓDIGO ABIERTO", heroTitle:"Explora la inteligencia abierta", heroDescription:"Investiga proyectos Open AGI en un solo lugar con fuentes técnicas, señales reales de desarrollo y análisis de IA con referencias.", featureResearchTitle:"Investigación de fuentes", featureResearchText:"Sitios oficiales, documentación, anuncios y enlaces en un solo informe.", featureGithubTitle:"Señales de desarrollo en GitHub", featureGithubText:"Consulta estrellas, forks, commits recientes y versiones publicadas.", featureEvidenceTitle:"Análisis basado en pruebas", featureEvidenceText:"Evalúa tecnología, progreso del producto, economía del token y riesgos con fuentes.", searchTitle:"Investigación del proyecto", searchDescription:"Introduce un proyecto para consultar fuentes web, datos de GitHub y análisis de IA.", projectLabel:"Nombre del proyecto o tema", placeholder:"p. ej., Sentient Foundation", submit:"Iniciar investigación", loading:"Investigando...", hint:"El análisis utiliza fuentes accesibles. Los repositorios que podrían no coincidir se marcan como posibles coincidencias.", reportTitle:"Informe de investigación", sourcesTitle:"Fuentes de investigación", githubTitle:"Resumen de desarrollo de GitHub", themeDark:"Modo claro", themeLight:"Modo oscuro", themeDarkAria:"Cambiar a modo claro", themeLightAria:"Cambiar a modo oscuro", errorEmpty:"Introduce un nombre de proyecto o tema.", footer:"Inteligencia de investigación de código abierto" },
            pt: { stars:"Stars", forks:"Forks", issues:"Issues / PR abertos*", mainLanguage:"Linguagem principal", commits:"Commits recentes", brandSubtitle:"Inteligência de pesquisa aberta", eyebrow:"PESQUISA DE IA DE CÓDIGO ABERTO", heroTitle:"Explore a inteligência aberta", heroDescription:"Pesquise projetos Open AGI em um só lugar com fontes técnicas, sinais reais de desenvolvimento e análise de IA citada.", featureResearchTitle:"Pesquisa de fontes", featureResearchText:"Sites oficiais, documentação, anúncios e links em um único relatório.", featureGithubTitle:"Sinais de desenvolvimento no GitHub", featureGithubText:"Veja stars, forks, commits recentes e versões publicadas.", featureEvidenceTitle:"Análise baseada em evidências", featureEvidenceText:"Avalie tecnologia, progresso do produto, economia do token e riscos com fontes.", searchTitle:"Pesquisa de projeto", searchDescription:"Digite um projeto para consultar fontes da web, dados do GitHub e análise de IA.", projectLabel:"Nome do projeto ou tema", placeholder:"ex.: Sentient Foundation", submit:"Iniciar pesquisa", loading:"Pesquisando...", hint:"A análise usa fontes acessíveis. Repositórios que talvez não correspondam são marcados como possíveis correspondências.", reportTitle:"Relatório de pesquisa", sourcesTitle:"Fontes da pesquisa", githubTitle:"Resumo de desenvolvimento do GitHub", themeDark:"Modo claro", themeLight:"Modo escuro", themeDarkAria:"Mudar para modo claro", themeLightAria:"Mudar para modo escuro", errorEmpty:"Digite um nome de projeto ou tema.", footer:"Inteligência de pesquisa de código aberto" },
            zh: { stars:"Stars", forks:"Forks", issues:"未关闭的 issue / PR*", mainLanguage:"主要语言", commits:"最近提交", brandSubtitle:"开放研究智能", eyebrow:"开源人工智能研究", heroTitle:"探索开放智能", heroDescription:"在一个平台研究 Open AGI 项目，查看技术来源、真实开发信号和带引用的 AI 分析。", featureResearchTitle:"实时来源研究", featureResearchText:"在一份报告中查看官方网站、文档、公告和来源链接。", featureGithubTitle:"GitHub 开发信号", featureGithubText:"通过 stars、forks、近期提交和版本信息了解公开开发活动。", featureEvidenceTitle:"基于证据的分析", featureEvidenceText:"结合来源评估技术架构、产品进展、代币经济和风险。", searchTitle:"项目研究", searchDescription:"输入项目名称，同时查看网络来源、GitHub 开发数据和 AI 分析。", projectLabel:"项目名称或研究主题", placeholder:"例如：Sentient Foundation", submit:"开始研究", loading:"研究中…", hint:"分析基于可访问的来源。可能不匹配的 GitHub 仓库会标记为候选匹配。", reportTitle:"研究报告", sourcesTitle:"研究来源", githubTitle:"GitHub 开发概览", themeDark:"浅色模式", themeLight:"深色模式", themeDarkAria:"切换到浅色模式", themeLightAria:"切换到深色模式", errorEmpty:"请输入项目名称或研究主题。", footer:"开源研究智能" },
            ru: { stars:"Stars", forks:"Forks", issues:"Открытые issues / PR*", mainLanguage:"Основной язык", commits:"Последние коммиты", brandSubtitle:"Интеллект открытых исследований", eyebrow:"ИССЛЕДОВАНИЯ ОТКРЫТОГО ИИ", heroTitle:"Исследуйте открытый интеллект", heroDescription:"Изучайте проекты Open AGI в одном месте: технические источники, реальные сигналы разработки и анализ ИИ со ссылками.", featureResearchTitle:"Поиск по источникам", featureResearchText:"Официальные сайты, документация, объявления и ссылки в одном отчёте.", featureGithubTitle:"Сигналы разработки GitHub", featureGithubText:"Изучайте открытую активность по звёздам, форкам, коммитам и релизам.", featureEvidenceTitle:"Анализ на основе фактов", featureEvidenceText:"Оценивайте технологии, прогресс продукта, токеномику и риски со ссылками.", searchTitle:"Исследование проекта", searchDescription:"Введите название проекта, чтобы вместе изучить веб-источники, данные GitHub и анализ ИИ.", projectLabel:"Название проекта или тема", placeholder:"например, Sentient Foundation", submit:"Начать исследование", loading:"Идёт исследование…", hint:"Анализ основан на доступных источниках. Возможные несовпадения репозитория GitHub отмечаются отдельно.", reportTitle:"Отчёт исследования", sourcesTitle:"Источники исследования", githubTitle:"Обзор разработки GitHub", themeDark:"Светлая тема", themeLight:"Тёмная тема", themeDarkAria:"Переключить на светлую тему", themeLightAria:"Переключить на тёмную тему", errorEmpty:"Введите название проекта или тему исследования.", footer:"Интеллект открытых исследований" }
        };

        function applyLanguage(code) {
            const t = UI_TEXT[code] || UI_TEXT.en;
            const set = (id, value) => { const el = document.getElementById(id); if (el && value) el.textContent = value; };
            set("brandSubtitle", t.brandSubtitle); set("heroEyebrow", t.eyebrow);
            const heroTitle = document.getElementById("heroTitle");
            if (heroTitle) heroTitle.innerHTML = code === "tr" ? 'Açık Zekâyı <span class="gradient-text">Keşfet</span>' : code === "en" ? 'Explore <span class="gradient-text">Open Intelligence</span>' : t.heroTitle;
            set("heroDescription", t.heroDescription); set("featureResearchTitle", t.featureResearchTitle); set("featureResearchText", t.featureResearchText);
            set("featureGithubTitle", t.featureGithubTitle); set("featureGithubText", t.featureGithubText); set("featureEvidenceTitle", t.featureEvidenceTitle); set("featureEvidenceText", t.featureEvidenceText);
            set("searchTitle", t.searchTitle); set("searchDescription", t.searchDescription); set("projectLabel", t.projectLabel); set("submitLabel", t.submit); set("researchHint", t.hint);
            set("githubTitle", t.githubTitle);
            const setHeadingText = (id, value) => { const el = document.getElementById(id); if (el && el.firstChild) el.firstChild.textContent = value + " "; };
            setHeadingText("reportTitle", t.reportTitle); setHeadingText("sourcesTitle", t.sourcesTitle);
            set("githubStarsLabel", t.stars); set("githubForksLabel", t.forks); set("githubIssuesLabel", t.issues); set("githubLanguageLabel", t.mainLanguage); set("commitsTitle", t.commits);
            set("footerText", t.footer);
            const input = document.getElementById("projectInput"); if (input) input.placeholder = t.placeholder;
            const isDark = root.dataset.theme !== "light";
            label.textContent = isDark ? t.themeDark : t.themeLight;
            button.setAttribute("aria-label", isDark ? t.themeDarkAria : t.themeLightAria);
            document.documentElement.lang = code;
            try { localStorage.setItem("prey-language", code); } catch (e) {}
        }

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
                applyLanguage(selectedCode);

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
            const code = (document.getElementById("dil") || {}).value || "tr";
            const t = UI_TEXT[code] || UI_TEXT.en;
            label.textContent = isDark ? t.themeDark : t.themeLight;
            button.setAttribute("aria-label", isDark ? t.themeDarkAria : t.themeLightAria);
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
        let initialLanguage = (languageInput && languageInput.value) || "tr";
        try {
            const savedLanguage = localStorage.getItem("prey-language");
            if (savedLanguage && UI_TEXT[savedLanguage] && !document.querySelector("#reportTitle")) initialLanguage = savedLanguage;
        } catch (e) {}
        if (languageInput) languageInput.value = initialLanguage;
        const initialOption = languageOptions.find(item => item.dataset.language === initialLanguage);
        if (initialOption) {
            currentLanguageLabel.textContent = initialOption.dataset.languageName;
            languageOptions.forEach(item => { const selected = item === initialOption; item.setAttribute("aria-checked", String(selected)); item.querySelector(".language-check").textContent = selected ? "✓" : ""; });
        }
        applyLanguage(initialLanguage);

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
            submitLabel.textContent = (UI_TEXT[(document.getElementById("dil") || {}).value || "tr"] || UI_TEXT.en).loading;
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
    github_veri = None
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
                    github_veri = github_gelisim_verisi(proje_adi)
                except Exception:
                    logger.exception("GitHub gelişim verileri alınamadı.")
                    github_veri = None

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
        github_veri=github_veri,
        hata=hata,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

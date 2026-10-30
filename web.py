import os
import logging
from flask import Flask, request, render_template_string, url_for
from auth import init_auth, _check_csrf
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
init_auth(app)
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


from workspace import register_workspace
register_workspace(app, render_report)


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

        .brand-copy { display: flex; flex-direction: column; align-items: flex-start; min-width: 0; }

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

        .brand-wordmark{display:flex;align-items:baseline;gap:7px;white-space:nowrap;font-size:19px;font-weight:900;letter-spacing:.025em;line-height:1.1}.brand-prey{color:#36d8c4}.brand-open{color:#e8f3fa;font-weight:800;letter-spacing:0}
        .brand-name {
            font-weight: 800;
            font-size: 17px;
            letter-spacing: -.45px;
            line-height: 1.25;
        }

        .brand-subtitle {
            margin-top: 6px;
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
        .live-data-title { margin: 22px 0 10px; font-size: 16px; }
        .live-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
        .live-metric { padding: 14px; border: 1px solid var(--border); border-radius: 13px; background: linear-gradient(145deg, var(--surface-2), transparent); }
        .live-metric-label { color: var(--muted); font-size: 11px; }
        .live-metric-value { margin-top: 5px; font-size: 22px; font-weight: 850; color: var(--accent-2); }
        .activity-chart { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); align-items: end; gap: 8px; min-height: 155px; margin-top: 14px; padding: 16px 12px 10px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-2); }
        .activity-week { min-width: 0; display: flex; height: 126px; flex-direction: column; justify-content: flex-end; align-items: center; gap: 7px; }
        .activity-count { color: var(--muted); font-size: 10px; font-variant-numeric: tabular-nums; }
        .activity-bar-wrap { display: flex; height: 92px; width: 100%; align-items: flex-end; justify-content: center; }
        .activity-bar { width: min(100%, 25px); min-height: 4px; border-radius: 7px 7px 3px 3px; background: linear-gradient(180deg, var(--accent-2), var(--accent)); box-shadow: 0 0 18px rgba(57,201,154,.12); transform-origin: bottom; animation: barGrow .8s cubic-bezier(.2,.7,.2,1) both; }
        @keyframes barGrow { from { transform: scaleY(.08); opacity: .35; } to { transform: scaleY(1); opacity: 1; } }
        .activity-label { color: var(--muted); font-size: 9px; white-space: nowrap; }
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
            .brand-wordmark { font-size: 14px; }
            .brand-subtitle { font-size: 9px; letter-spacing: 1px; }
            .nav-actions { gap: 6px; }
            .theme-toggle { padding: 9px 10px; font-size: 12px; }
            .language-toggle { padding: 9px 10px; font-size: 12px; }
            .language-dropdown { width: 190px; }
            main { padding-top: 38px; }
            .hero p { font-size: 14px; }
            .panel { padding: 18px; border-radius: 17px; }
            .form-grid, .sources, .feature-grid { grid-template-columns: 1fr; }
            .github-metrics, .live-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .activity-chart { gap: 4px; padding-inline: 6px; }
            .activity-label { font-size: 8px; }
            .form-grid { gap: 14px; }
            .submit-button { margin-top: 16px; }
        }

        /* HIGH-VISIBILITY MOTION: animated grid, glowing orbs, floating cards and CTA pulse. */
        body { isolation: isolate; overflow-x: hidden; position: relative; }
        body::before {
            content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
            background:
              radial-gradient(circle at 12% 18%, rgba(39, 190, 255, .18), transparent 27%),
              radial-gradient(circle at 85% 30%, rgba(48, 230, 166, .15), transparent 28%),
              radial-gradient(circle at 55% 90%, rgba(117, 92, 255, .12), transparent 30%),
              linear-gradient(rgba(89, 166, 200, .045) 1px, transparent 1px),
              linear-gradient(90deg, rgba(89, 166, 200, .045) 1px, transparent 1px);
            background-size: auto, auto, auto, 42px 42px, 42px 42px;
            animation: backgroundFlow 16s ease-in-out infinite alternate;
        }
        body::after {
            content: ""; position: fixed; z-index: -1; pointer-events: none;
            width: 25rem; height: 25rem; top: 18%; right: -11rem; border-radius: 50%;
            background: radial-gradient(circle, rgba(44, 221, 177, .22), rgba(44, 221, 177, 0) 68%);
            filter: blur(18px); animation: orbFloat 9s ease-in-out infinite alternate;
        }
        @keyframes backgroundFlow { 0% { background-position: 0 0, 0 0, 0 0, 0 0, 0 0; } 100% { background-position: 5% 8%, -6% 4%, 4% -8%, 21px 21px, 21px 21px; } }
        @keyframes orbFloat { 0% { transform: translate3d(0, -22px, 0) scale(.88); } 100% { transform: translate3d(-90px, 65px, 0) scale(1.15); } }
        @keyframes fadeSlideUp { from { opacity: 0; transform: translateY(28px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseGlow { 0%,100% { box-shadow: 0 0 0 0 rgba(57,201,154,.48), 0 0 16px rgba(57,201,154,.08); } 50% { box-shadow: 0 0 0 9px rgba(57,201,154,0), 0 0 28px rgba(57,201,154,.22); } }
        @keyframes titleShimmer { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
        @keyframes iconFloat { 0%,100% { transform: translateY(0) rotate(-2deg); } 50% { transform: translateY(-9px) rotate(4deg); } }
        @keyframes buttonShine { 0% { transform: translateX(-150%) skewX(-20deg); } 100% { transform: translateX(330%) skewX(-20deg); } }
        .brand-icon { animation: iconFloat 3.8s ease-in-out infinite; }
        .status-dot { animation: pulseGlow 1.8s ease-in-out infinite; }
        .gradient-text { background-size: 200% 100%; animation: titleShimmer 4s linear infinite; }
        .eyebrow { animation: fadeSlideUp .7s both; }
        .hero h1 { animation: fadeSlideUp .8s .08s both; }
        .hero > p { animation: fadeSlideUp .8s .18s both; }
        .feature-card { position: relative; overflow: hidden; transition: transform .3s ease, border-color .3s ease, box-shadow .3s ease; animation: fadeSlideUp .8s both, cardBreathe 6s ease-in-out infinite; }
        .feature-card:nth-child(2) { animation-delay: .12s, 1s; }
        .feature-card:nth-child(3) { animation-delay: .24s, 2s; }
        @keyframes cardBreathe { 0%,100% { box-shadow: 0 0 0 rgba(57,201,154,0); } 50% { box-shadow: 0 8px 28px rgba(57,201,154,.08); } }
        .feature-card::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(115deg, transparent 20%, rgba(70,220,190,.13) 50%, transparent 80%); transform: translateX(-130%); animation: cardSweep 7s ease-in-out infinite; }
        .feature-card:nth-child(2)::after { animation-delay: 1.6s; }
        .feature-card:nth-child(3)::after { animation-delay: 3.2s; }
        @keyframes cardSweep { 0%, 68%, 100% { transform: translateX(-130%); } 82% { transform: translateX(130%); } }
        .feature-card:hover { transform: translateY(-9px) scale(1.015); border-color: var(--accent); box-shadow: 0 18px 42px rgba(57,201,154,.17); }
        .feature-icon { transition: transform .3s ease; animation: iconFloat 4.5s ease-in-out infinite; }
        .feature-card:hover .feature-icon { transform: translateY(-4px) rotate(-9deg) scale(1.13); }
        .panel, .github-panel, .results, .sources, .error { animation: fadeSlideUp .75s both; }
        .panel { animation-delay: .12s; transition: border-color .25s ease, box-shadow .25s ease; }
        .panel:focus-within { border-color: var(--accent); box-shadow: 0 0 0 1px rgba(57,201,154,.22), 0 18px 55px rgba(57,201,154,.13); }
        .submit-button { position: relative; overflow: hidden; animation: pulseGlow 3s ease-in-out infinite; }
        .submit-button::after { content: ""; position: absolute; top: -30%; left: 0; width: 35%; height: 160%; background: rgba(255,255,255,.28); filter: blur(8px); transform: translateX(-150%) skewX(-20deg); animation: buttonShine 4.5s ease-in-out infinite; }
        .github-metric, .commit-item, .source-card { transition: transform .25s ease, border-color .25s ease, background .25s ease, box-shadow .25s ease; }
        .github-metric:hover, .commit-item:hover, .source-card:hover { transform: translateY(-5px) scale(1.01); border-color: var(--accent); box-shadow: 0 12px 30px rgba(57,201,154,.13); }
        .theme-toggle, .language-toggle { transition: transform .2s ease, border-color .2s ease, background .2s ease; }
        .theme-toggle:hover, .language-toggle:hover { transform: translateY(-3px); }
        .reveal-on-scroll { opacity: 0; transform: translateY(24px); transition: opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1); }
        .reveal-on-scroll.is-visible { opacity: 1; transform: translateY(0); }
        .language-dropdown:not([hidden]) { animation: fadeSlideUp .18s ease both; transform-origin: top right; }
        @media (max-width: 640px) { body::after { width: 18rem; height: 18rem; } }
        @media (prefers-reduced-motion: reduce) {
            .reveal-on-scroll { opacity: 1; transform: none; }
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
            <div class="brand-copy">
                <div class="brand-wordmark" aria-label="Prey Open AGI"><span class="brand-prey">PREY</span><span class="brand-open">OPEN AGI</span></div>
                <div class="brand-subtitle" id="brandSubtitle">Open Research Intelligence</div>
            </div>
        </div>

        <div class="nav-actions">
            {% if current_user %}
            <span style="display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid var(--border);border-radius:999px;color:var(--muted);font-size:11px">
                {{ current_user.name }}
                {% if current_user.role == 'founder' %}<strong id="founderBadge" style="color:var(--accent)">KURUCU</strong>{% endif %}
            </span>
            <form method="post" action="{{ url_for('auth.logout') }}" style="display:inline;margin:0">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button type="submit" class="language-toggle"><span id="signOutLabel">Çıkış yap</span></button>
            </form>
            {% endif %}
            <a class="language-toggle" href="/workspace" style="text-decoration:none;display:inline-flex;align-items:center;gap:8px"><span aria-hidden="true">✦ </span><span id="workspaceNavLabel">AI Çalışma Alanı</span></a>
            <a class="language-toggle" href="/compare" style="text-decoration:none;display:inline-flex;align-items:center;gap:8px"><span aria-hidden="true">⇄ </span><span id="compareNavLabel">Projeleri Karşılaştır</span></a>
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
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
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
                        Olası eşleşme — depo adı tam eşleşmiyor; verileri proje hakkında kesin kanıt sayma.
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

            <h3 class="live-data-title" id="liveMetricsTitle">Canlı geliştirme göstergeleri</h3>
            <div class="live-metrics">
                <div class="live-metric"><div class="live-metric-label" id="commits30Label">Son 30 günde commit</div><div class="live-metric-value">{{ github_veri.commits_last_30_days if github_veri.commits_last_30_days is not none else "—" }}</div></div>
                <div class="live-metric"><div class="live-metric-label" id="commits90Label">Son 90 günde commit</div><div class="live-metric-value">{{ github_veri.commits_last_90_days if github_veri.commits_last_90_days is not none else "—" }}</div></div>
                <div class="live-metric"><div class="live-metric-label" id="lastPushLabel">Son push üzerinden gün</div><div class="live-metric-value">{{ github_veri.days_since_push if github_veri.days_since_push is not none else "—" }}</div></div>
                <div class="live-metric"><div class="live-metric-label" id="watchersLabel">Takipçiler</div><div class="live-metric-value">{{ "{:,}".format(github_veri.watchers).replace(",", " ") if github_veri.watchers is not none else "—" }}</div></div>
            </div>

            <h3 class="live-data-title" id="activityTitle">Son 12 haftalık commit aktivitesi</h3>
            {% if github_veri.weekly_activity %}
                <div class="activity-chart" role="img" aria-label="Son 12 haftadaki commit aktivitesi">
                    {% for week in github_veri.weekly_activity %}
                        <div class="activity-week" title="{{ week.label }}: {{ week.count }} commit">
                            <span class="activity-count">{{ week.count }}</span>
                            <div class="activity-bar-wrap"><div class="activity-bar" style="height: {{ week.height }}%; animation-delay: {{ loop.index0 * 35 }}ms"></div></div>
                            <span class="activity-label">{{ week.label }}</span>
                        </div>
                    {% endfor %}
                </div>
                <p class="github-note" id="activityNote">Grafik GitHub'dan alınan son {{ github_veri.commit_sample_size }} commit üzerinden hesaplanır; tam tarihçe değildir.</p>
            {% else %}
                <p class="github-note">Commit aktivite grafiği için veri alınamadı.</p>
            {% endif %}

            <div class="github-meta" style="margin-top:16px">
                <span id="repoCreatedLabel">Oluşturulma:</span> {{ github_veri.created_at or "Bilinmiyor" }} ·
                <span id="repoPushedLabel">Son push:</span> {{ github_veri.pushed_at or "Bilinmiyor" }} ·
                <span id="repoUpdatedLabel">GitHub kayıt güncellemesi:</span> {{ github_veri.updated_at or "Bilinmiyor" }}
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
                Veriler GitHub API'sinden araştırma sırasında alınır. Grafik, son 100 commit içinde görülen haftalık dağılımı gösterir; geçmiş yıldız/fork değerlerini saklamaz.
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

        // Staggered scroll-in animations for content panels and result sections.
        try {
            const motionTargets = document.querySelectorAll(
                ".panel, .github-panel, .results, .sources, .error, .github-metric, .commit-item, .source-card"
            );
            motionTargets.forEach(function (element) { element.classList.add("reveal-on-scroll"); });
            if ("IntersectionObserver" in window) {
                const motionObserver = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add("is-visible");
                            motionObserver.unobserve(entry.target);
                        }
                    });
                }, { threshold: 0.08, rootMargin: "0px 0px -24px 0px" });
                motionTargets.forEach(function (element) { motionObserver.observe(element); });
            } else {
                motionTargets.forEach(function (element) { element.classList.add("is-visible"); });
            }
        } catch (e) { /* Motion is decorative; the site remains usable if unsupported. */ }

        const UI_TEXT = {
            tr: { signOut:"Çıkış yap", workspaceNav:"AI Çalışma Alanı", compareNav:"Projeleri Karşılaştır", founder:"KURUCU", stars:"Stars", forks:"Forks", issues:"Açık issue / PR sayacı*", mainLanguage:"Ana dil", commits:"Son commitler", liveTitle:"Canlı geliştirme göstergeleri", commits30:"Son 30 günde commit", commits90:"Son 90 günde commit", lastPush:"Son push üzerinden gün", watchers:"Takipçiler", activityTitle:"Son 12 haftalık commit aktivitesi", activityNote:"Grafik son 100 commit içinde alınabilen veriye dayanır; tam depo tarihçesi değildir.", brandSubtitle:"Açık Araştırma Zekâsı", eyebrow:"AÇIK KAYNAKLI AI ARAŞTIRMASI", heroTitle:"Açık Zekâyı Keşfet", heroDescription:"Open AGI projelerini; teknik kaynaklar, gerçek geliştirme sinyalleri ve kaynak gösteren AI analiziyle tek yerde araştır.", featureResearchTitle:"Canlı kaynak araştırması", featureResearchText:"Resmî siteler, dokümantasyon, duyurular ve kaynak bağlantıları tek raporda.", featureGithubTitle:"GitHub geliştirme sinyalleri", featureGithubText:"Stars, forks, son commitler ve sürüm bilgileriyle açık geliştirme etkinliğini incele.", featureEvidenceTitle:"Kanıta dayalı analiz", featureEvidenceText:"Teknik yapı, ürün ilerlemesi, token ekonomisi ve riskleri kaynaklarla birlikte değerlendir.", searchTitle:"Proje araştırması", searchDescription:"Proje adını gir; web kaynaklarını, GitHub geliştirme verilerini ve AI analizini bir arada incele.", projectLabel:"Proje adı veya araştırma konusu", placeholder:"Örn. Sentient Foundation", submit:"Araştırmayı başlat", loading:"Araştırılıyor...", hint:"Analiz erişilebilen kaynaklara dayanır. Proje adıyla eşleşmeyen GitHub depoları olası eşleşme olarak işaretlenir.", reportTitle:"Araştırma raporu", sourcesTitle:"Araştırma kaynakları", githubTitle:"GitHub gelişim özeti", themeDark:"Gündüz", themeLight:"Gece", themeDarkAria:"Gündüz moduna geç", themeLightAria:"Gece moduna geç", errorEmpty:"Lütfen bir proje adı veya araştırma konusu gir.", footer:"Açık kaynak araştırma zekâsı" },
            en: { signOut:"Sign out", workspaceNav:"AI Workspace", compareNav:"Compare Projects", founder:"FOUNDER", stars:"Stars", forks:"Forks", issues:"Open issues / PRs*", mainLanguage:"Primary language", commits:"Recent commits", liveTitle:"Live development signals", commits30:"Commits in last 30 days", commits90:"Commits in last 90 days", lastPush:"Days since last push", watchers:"Watchers", activityTitle:"Commit activity · last 12 weeks", activityNote:"Based on available data from the latest 100 commits; not the full repository history.", brandSubtitle:"Open Research Intelligence", eyebrow:"OPEN-SOURCE AI RESEARCH", heroTitle:"Explore Open Intelligence", heroDescription:"Research Open AGI projects in one place with technical sources, real development signals, and cited AI analysis.", featureResearchTitle:"Live source research", featureResearchText:"Official websites, documentation, announcements, and source links in one report.", featureGithubTitle:"GitHub development signals", featureGithubText:"Review public development activity through stars, forks, recent commits, and releases.", featureEvidenceTitle:"Evidence-based analysis", featureEvidenceText:"Assess technical design, product progress, token economics, and risks with sources.", searchTitle:"Project research", searchDescription:"Enter a project name to review web sources, GitHub development data, and AI analysis together.", projectLabel:"Project name or research topic", placeholder:"e.g. Sentient Foundation", submit:"Start research", loading:"Researching...", hint:"Analysis is based on accessible sources. GitHub repositories that may not match the project are marked as possible matches.", reportTitle:"Research report", sourcesTitle:"Research sources", githubTitle:"GitHub development overview", themeDark:"Light mode", themeLight:"Dark mode", themeDarkAria:"Switch to light mode", themeLightAria:"Switch to dark mode", errorEmpty:"Enter a project name or research topic.", footer:"Open-source research intelligence" },
            es: { signOut:"Cerrar sesión", workspaceNav:"Espacio de trabajo de IA", compareNav:"Comparar proyectos", founder:"FUNDADOR", stars:"Stars", forks:"Forks", issues:"Issues / PR abiertos*", mainLanguage:"Lenguaje principal", commits:"Commits recientes", liveTitle:"Indicadores de desarrollo en vivo", commits30:"Commits en los últimos 30 días", commits90:"Commits en los últimos 90 días", lastPush:"Días desde el último push", watchers:"Seguidores", activityTitle:"Actividad de commits · últimas 12 semanas", activityNote:"Basado en los últimos 100 commits disponibles; no es todo el historial.", brandSubtitle:"Inteligencia de investigación abierta", eyebrow:"INVESTIGACIÓN DE IA DE CÓDIGO ABIERTO", heroTitle:"Explora la inteligencia abierta", heroDescription:"Investiga proyectos Open AGI en un solo lugar con fuentes técnicas, señales reales de desarrollo y análisis de IA con referencias.", featureResearchTitle:"Investigación de fuentes", featureResearchText:"Sitios oficiales, documentación, anuncios y enlaces en un solo informe.", featureGithubTitle:"Señales de desarrollo en GitHub", featureGithubText:"Consulta estrellas, forks, commits recientes y versiones publicadas.", featureEvidenceTitle:"Análisis basado en pruebas", featureEvidenceText:"Evalúa tecnología, progreso del producto, economía del token y riesgos con fuentes.", searchTitle:"Investigación del proyecto", searchDescription:"Introduce un proyecto para consultar fuentes web, datos de GitHub y análisis de IA.", projectLabel:"Nombre del proyecto o tema", placeholder:"p. ej., Sentient Foundation", submit:"Iniciar investigación", loading:"Investigando...", hint:"El análisis utiliza fuentes accesibles. Los repositorios que podrían no coincidir se marcan como posibles coincidencias.", reportTitle:"Informe de investigación", sourcesTitle:"Fuentes de investigación", githubTitle:"Resumen de desarrollo de GitHub", themeDark:"Modo claro", themeLight:"Modo oscuro", themeDarkAria:"Cambiar a modo claro", themeLightAria:"Cambiar a modo oscuro", errorEmpty:"Introduce un nombre de proyecto o tema.", footer:"Inteligencia de investigación de código abierto" },
            pt: { signOut:"Sair", workspaceNav:"Espaço de trabalho de IA", compareNav:"Comparar projetos", founder:"FUNDADOR", stars:"Stars", forks:"Forks", issues:"Issues / PR abertos*", mainLanguage:"Linguagem principal", commits:"Commits recentes", liveTitle:"Indicadores de desenvolvimento ao vivo", commits30:"Commits nos últimos 30 dias", commits90:"Commits nos últimos 90 dias", lastPush:"Dias desde o último push", watchers:"Seguidores", activityTitle:"Atividade de commits · últimas 12 semanas", activityNote:"Baseado nos últimos 100 commits disponíveis; não representa todo o histórico.", brandSubtitle:"Inteligência de pesquisa aberta", eyebrow:"PESQUISA DE IA DE CÓDIGO ABERTO", heroTitle:"Explore a inteligência aberta", heroDescription:"Pesquise projetos Open AGI em um só lugar com fontes técnicas, sinais reais de desenvolvimento e análise de IA citada.", featureResearchTitle:"Pesquisa de fontes", featureResearchText:"Sites oficiais, documentação, anúncios e links em um único relatório.", featureGithubTitle:"Sinais de desenvolvimento no GitHub", featureGithubText:"Veja stars, forks, commits recentes e versões publicadas.", featureEvidenceTitle:"Análise baseada em evidências", featureEvidenceText:"Avalie tecnologia, progresso do produto, economia do token e riscos com fontes.", searchTitle:"Pesquisa de projeto", searchDescription:"Digite um projeto para consultar fontes da web, dados do GitHub e análise de IA.", projectLabel:"Nome do projeto ou tema", placeholder:"ex.: Sentient Foundation", submit:"Iniciar pesquisa", loading:"Pesquisando...", hint:"A análise usa fontes acessíveis. Repositórios que talvez não correspondam são marcados como possíveis correspondências.", reportTitle:"Relatório de pesquisa", sourcesTitle:"Fontes da pesquisa", githubTitle:"Resumo de desenvolvimento do GitHub", themeDark:"Modo claro", themeLight:"Modo escuro", themeDarkAria:"Mudar para modo claro", themeLightAria:"Mudar para modo escuro", errorEmpty:"Digite um nome de projeto ou tema.", footer:"Inteligência de pesquisa de código aberto" },
            zh: { signOut:"退出登录", workspaceNav:"AI 工作区", compareNav:"比较项目", founder:"创始人", stars:"Stars", forks:"Forks", issues:"未关闭的 issue / PR*", mainLanguage:"主要语言", commits:"最近提交", liveTitle:"实时开发指标", commits30:"过去 30 天提交", commits90:"过去 90 天提交", lastPush:"距上次推送天数", watchers:"关注者", activityTitle:"最近 12 周提交活动", activityNote:"基于最近 100 条可用提交记录，不代表完整仓库历史。", brandSubtitle:"开放研究智能", eyebrow:"开源人工智能研究", heroTitle:"探索开放智能", heroDescription:"在一个平台研究 Open AGI 项目，查看技术来源、真实开发信号和带引用的 AI 分析。", featureResearchTitle:"实时来源研究", featureResearchText:"在一份报告中查看官方网站、文档、公告和来源链接。", featureGithubTitle:"GitHub 开发信号", featureGithubText:"通过 stars、forks、近期提交和版本信息了解公开开发活动。", featureEvidenceTitle:"基于证据的分析", featureEvidenceText:"结合来源评估技术架构、产品进展、代币经济和风险。", searchTitle:"项目研究", searchDescription:"输入项目名称，同时查看网络来源、GitHub 开发数据和 AI 分析。", projectLabel:"项目名称或研究主题", placeholder:"例如：Sentient Foundation", submit:"开始研究", loading:"研究中…", hint:"分析基于可访问的来源。可能不匹配的 GitHub 仓库会标记为候选匹配。", reportTitle:"研究报告", sourcesTitle:"研究来源", githubTitle:"GitHub 开发概览", themeDark:"浅色模式", themeLight:"深色模式", themeDarkAria:"切换到浅色模式", themeLightAria:"切换到深色模式", errorEmpty:"请输入项目名称或研究主题。", footer:"开源研究智能" },
            ru: { signOut:"Выйти", workspaceNav:"Рабочее пространство ИИ", compareNav:"Сравнить проекты", founder:"ОСНОВАТЕЛЬ", stars:"Stars", forks:"Forks", issues:"Открытые issues / PR*", mainLanguage:"Основной язык", commits:"Последние коммиты", liveTitle:"Актуальные показатели разработки", commits30:"Коммиты за 30 дней", commits90:"Коммиты за 90 дней", lastPush:"Дней с последнего push", watchers:"Наблюдатели", activityTitle:"Активность коммитов за 12 недель", activityNote:"По доступным данным последних 100 коммитов; это не полная история репозитория.", brandSubtitle:"Интеллект открытых исследований", eyebrow:"ИССЛЕДОВАНИЯ ОТКРЫТОГО ИИ", heroTitle:"Исследуйте открытый интеллект", heroDescription:"Изучайте проекты Open AGI в одном месте: технические источники, реальные сигналы разработки и анализ ИИ со ссылками.", featureResearchTitle:"Поиск по источникам", featureResearchText:"Официальные сайты, документация, объявления и ссылки в одном отчёте.", featureGithubTitle:"Сигналы разработки GitHub", featureGithubText:"Изучайте открытую активность по звёздам, форкам, коммитам и релизам.", featureEvidenceTitle:"Анализ на основе фактов", featureEvidenceText:"Оценивайте технологии, прогресс продукта, токеномику и риски со ссылками.", searchTitle:"Исследование проекта", searchDescription:"Введите название проекта, чтобы вместе изучить веб-источники, данные GitHub и анализ ИИ.", projectLabel:"Название проекта или тема", placeholder:"например, Sentient Foundation", submit:"Начать исследование", loading:"Идёт исследование…", hint:"Анализ основан на доступных источниках. Возможные несовпадения репозитория GitHub отмечаются отдельно.", reportTitle:"Отчёт исследования", sourcesTitle:"Источники исследования", githubTitle:"Обзор разработки GitHub", themeDark:"Светлая тема", themeLight:"Тёмная тема", themeDarkAria:"Переключить на светлую тему", themeLightAria:"Переключить на тёмную тему", errorEmpty:"Введите название проекта или тему исследования.", footer:"Интеллект открытых исследований" }
        };

        function applyLanguage(code) {
            const t = UI_TEXT[code] || UI_TEXT.en;
            const set = (id, value) => { const el = document.getElementById(id); if (el && value) el.textContent = value; };
            set("brandSubtitle", t.brandSubtitle); set("heroEyebrow", t.eyebrow);
            set("signOutLabel", t.signOut); set("workspaceNavLabel", t.workspaceNav); set("compareNavLabel", t.compareNav); set("founderBadge", t.founder);
            const workspaceLink = document.querySelector('a[href^="/workspace"]'); if (workspaceLink) workspaceLink.href = "/workspace?lang=" + encodeURIComponent(code);
            const compareLink = document.querySelector('a[href^="/compare"]'); if (compareLink) compareLink.href = "/compare?lang=" + encodeURIComponent(code);
            const heroTitle = document.getElementById("heroTitle");
            if (heroTitle) heroTitle.innerHTML = code === "tr" ? 'Açık Zekâyı <span class="gradient-text">Keşfet</span>' : code === "en" ? 'Explore <span class="gradient-text">Open Intelligence</span>' : t.heroTitle;
            set("heroDescription", t.heroDescription); set("featureResearchTitle", t.featureResearchTitle); set("featureResearchText", t.featureResearchText);
            set("featureGithubTitle", t.featureGithubTitle); set("featureGithubText", t.featureGithubText); set("featureEvidenceTitle", t.featureEvidenceTitle); set("featureEvidenceText", t.featureEvidenceText);
            set("searchTitle", t.searchTitle); set("searchDescription", t.searchDescription); set("projectLabel", t.projectLabel); set("submitLabel", t.submit); set("researchHint", t.hint);
            set("githubTitle", t.githubTitle);
            const setHeadingText = (id, value) => { const el = document.getElementById(id); if (el && el.firstChild) el.firstChild.textContent = value + " "; };
            setHeadingText("reportTitle", t.reportTitle); setHeadingText("sourcesTitle", t.sourcesTitle);
            set("githubStarsLabel", t.stars); set("githubForksLabel", t.forks); set("githubIssuesLabel", t.issues); set("githubLanguageLabel", t.mainLanguage); set("commitsTitle", t.commits);
            set("liveMetricsTitle", t.liveTitle); set("commits30Label", t.commits30); set("commits90Label", t.commits90); set("lastPushLabel", t.lastPush); set("watchersLabel", t.watchers); set("activityTitle", t.activityTitle); set("activityNote", t.activityNote);
            set("footerText", t.footer);
            const input = document.getElementById("proje_adi"); if (input) input.placeholder = t.placeholder;
            const isDark = root.dataset.theme !== "light";
            label.textContent = isDark ? t.themeDark : t.themeLight;
            button.setAttribute("aria-label", isDark ? t.themeDarkAria : t.themeLightAria);
            document.documentElement.lang = code;
            try { localStorage.setItem("prey-language", code); document.cookie = "prey-language=" + encodeURIComponent(code) + "; Path=/; Max-Age=31536000; SameSite=Lax"; } catch (e) {}
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
    if request.method == "POST":
        _check_csrf()
    proje_adi = ""
    dil = request.args.get("lang", request.cookies.get("prey-language", "tr"))
    rapor = None
    kaynaklar = []
    github_veri = None
    hata = None

    if request.method == "POST":
        proje_adi = request.form.get("proje_adi", "").strip()
        dil = request.form.get("dil", request.args.get("lang", request.cookies.get("prey-language", "tr"))).strip()

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


COMPARE_HTML = r"""
<!doctype html><html lang="{{ dil }}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ t.page_title }} · Prey Open AGI</title>
<style>
:root{color-scheme:dark;--bg:#07131d;--panel:#102330;--line:#244151;--text:#e8f3fa;--muted:#a6bbc8;--a:#29d8c2;--b:#64aaff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% 0%,#123747 0,transparent 35%),var(--bg);color:var(--text);font:15px/1.6 Inter,system-ui,sans-serif}.wrap{max-width:1100px;margin:auto;padding:28px 18px 60px}a{color:#70dff0}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:28px}.brand{font-weight:800;font-size:19px}.pill{border:1px solid var(--line);border-radius:99px;padding:7px 12px;text-decoration:none}.hero{padding:25px 0 15px}.eyebrow{color:var(--a);letter-spacing:.15em;font-size:11px;font-weight:800}.hero h1{font-size:clamp(30px,5vw,46px);line-height:1.1;margin:8px 0}.muted{color:var(--muted)}.panel{background:linear-gradient(145deg,#112633,#0b1c28);border:1px solid var(--line);border-radius:18px;padding:22px;margin:18px 0;box-shadow:0 18px 60px #0002}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}input,select{width:100%;background:#071722;color:var(--text);border:1px solid #2b4859;border-radius:10px;padding:13px;font:inherit}.btn{margin-top:15px;border:0;border-radius:10px;padding:13px 18px;background:linear-gradient(100deg,#27d9bf,#62a7ff);color:#04131b;font-weight:800;cursor:pointer;width:100%}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.metric{background:#0a1a25;border:1px solid var(--line);border-radius:12px;padding:14px}.metric strong{font-size:22px;display:block}.metric small{color:var(--muted)}.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}.brand{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.brand-copy{display:flex;flex-direction:column;align-items:flex-start;min-width:0}.brand-wordmark{display:flex;align-items:baseline;gap:7px;white-space:nowrap;font-size:19px;font-weight:900;letter-spacing:.025em;line-height:1.1}.brand-prey{color:#36d8c4}.brand-open{color:#e8f3fa;font-weight:800;letter-spacing:0}.tag{display:inline-block;background:#183a47;border-radius:99px;padding:3px 9px;font-size:12px}.warn{color:#ffce80}.report h1,.report h2,.report h3{line-height:1.25}.report table{width:100%;border-collapse:collapse;display:block;overflow-x:auto}.report td,.report th{border:1px solid var(--line);padding:8px;text-align:left}.sources a{overflow-wrap:anywhere}.loading{opacity:.8}@media(max-width:680px){.formgrid,.cols,.metrics{grid-template-columns:1fr}.panel{padding:16px}}
</style></head><body><div class="wrap"><div class="top"><div class="brand"><div class="brand-copy"><div class="brand-wordmark" aria-label="Prey Open AGI"><span class="brand-prey">PREY</span><span class="brand-open">OPEN AGI</span></div></div><span class="tag">{{ t.lab }}</span></div><a class="pill" href="/?lang={{ dil }}">← {{ t.home }}</a></div>
<div class="hero"><div class="eyebrow">{{ t.eyebrow }}</div><h1>{{ t.hero }}</h1><p class="muted">{{ t.description }}</p></div>
<section class="panel"><form method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><div class="formgrid"><div><label for="project_a">{{ t.project_a }}</label><input id="project_a" name="project_a" value="{{ a }}" placeholder="" required></div><div><label for="project_b">{{ t.project_b }}</label><input id="project_b" name="project_b" value="{{ b }}" placeholder="" required></div></div><div style="margin-top:14px"><label for="dil">{{ t.report_language }}</label><select id="dil" name="dil">{% for code,name in languages.items() %}<option value="{{code}}" {% if code==dil %}selected{% endif %}>{{name}}</option>{% endfor %}</select></div><button class="btn" type="submit">↔ {{ t.compare }}</button><p class="muted" style="font-size:12px">{{ t.form_note }}</p></form></section>
{% if error %}<section class="panel warn">{{ error }}</section>{% endif %}
{% if result %}<section class="panel"><h2>{{ t.live_signals }}</h2><div class="cols">{% for item in result.github %}<div class="metric"><h3>{{ item.project }}</h3>{% if item.data %}<p><a href="{{item.data.url}}" target="_blank" rel="noopener">{{item.data.name}}</a></p>{% if not item.data.is_exact_match %}<p class="warn">{{ t.possible_match }}</p>{% endif %}<div class="metrics"><div class="metric"><strong>{{ item.data.stars if item.data.stars is not none else '—' }}</strong><small>{{ t.stars }}</small></div><div class="metric"><strong>{{ item.data.forks if item.data.forks is not none else '—' }}</strong><small>{{ t.forks }}</small></div><div class="metric"><strong>{{ item.data.commits_last_30_days if item.data.commits_last_30_days is not none else '—' }}</strong><small>{{ t.commits30 }}</small></div><div class="metric"><strong>{{ item.data.commits_last_90_days if item.data.commits_last_90_days is not none else '—' }}</strong><small>{{ t.commits90 }}</small></div></div><p class="muted">{{ t.language }}: {{item.data.language or t.unknown}} · {{ t.last_push }}: {{item.data.pushed_at or t.unknown}}</p>{% else %}<p class="warn">{{ t.no_repo }}</p>{% endif %}</div>{% endfor %}</div></section>
<section class="panel"><h2>{{ t.research_comparison }}</h2><p class="muted">{{ t.research_note }}</p><div class="report">{{ result.report|safe }}</div></section>
<section class="panel sources"><h2>{{ t.sources }}</h2>{% for src in result.sources %}<div class="metric" style="margin:9px 0"><a href="{{src.url}}" target="_blank" rel="noopener">{{src.baslik or src.url}}</a><p class="muted">{{src.aciklama or ''}}</p></div>{% endfor %}</section>{% endif %}
</div></body></html>
"""

COMPARE_TRANSLATIONS = {
    "tr": {"page_title":"Proje Karşılaştırması","lab":"KIYASLAMA LABI","home":"Araştırma ana sayfası","eyebrow":"AÇIK KAYNAK PROJE İSTİHBARATI","hero":"Projeleri kanıtlarla karşılaştırın.","description":"GitHub etkinliğini, ürün olgunluğunu, token ekonomisini ve ekosistem iddialarını kaynaklarla yan yana inceleyin.","project_a":"Proje A","project_b":"Proje B","example_a":"Örn. Sentient","example_b":"Örn. GenLayer","report_language":"Rapor dili","compare":"Projeleri karşılaştır","form_note":"Token fiyatı, borsa listelenmesi ve ekosistem bilgileri yalnızca kaynaklarda bulunduğunda raporlanır. GitHub etkinliği tek başına proje kalitesini göstermez.","live_signals":"Canlı geliştirme göstergeleri","possible_match":"Olası depo eşleşmesi — metriklere güvenmeden önce doğrulayın.","stars":"Yıldız","forks":"Fork","commits30":"Son 30 gündeki commit","commits90":"Son 90 gündeki commit","language":"Dil","last_push":"Son güncelleme","unknown":"Bilinmiyor","no_repo":"Güvenilir bir GitHub deposu eşleşmesi bulunamadı. Metrikler sıfır kabul edilmedi.","research_comparison":"Araştırmaya dayalı karşılaştırma","research_note":"Token ekonomisi, borsa listelenmeleri, ürün olgunluğu ve ekosistem kanıtları aşağıda özetlenir. Kaynakla desteklenmeyen iddialar doğrulanmamış kabul edilmelidir.","sources":"Kullanılan kaynaklar","empty":"Karşılaştırmak için iki proje adı girin.","same":"Lütfen birbirinden farklı iki proje seçin.","failed":"Karşılaştırma oluşturulamadı. Arama sağlayıcısını, FORTYTWO_API_KEY ayarını ve Render kayıtlarını kontrol edin."},
    "en": {"page_title":"Project Comparison","lab":"COMPARISON LAB","home":"Research home","eyebrow":"OPEN-SOURCE PROJECT INTELLIGENCE","hero":"Compare projects with evidence.","description":"Review GitHub activity, product maturity, tokenomics and ecosystem claims side by side with sources.","project_a":"Project A","project_b":"Project B","example_a":"e.g. Sentient","example_b":"e.g. GenLayer","report_language":"Report language","compare":"Compare projects","form_note":"Token prices, listings and ecosystem claims are reported only when supported by sources. GitHub activity alone does not measure project quality.","live_signals":"Live development signals","possible_match":"Possible repository match — verify before relying on metrics.","stars":"Stars","forks":"Forks","commits30":"Commits · 30 days","commits90":"Commits · 90 days","language":"Language","last_push":"Last push","unknown":"Unknown","no_repo":"No sufficiently reliable GitHub repository match found. Metrics are not treated as zero.","research_comparison":"Research-based comparison","research_note":"Tokenomics, listings, product maturity and ecosystem evidence are summarized below. Claims without supporting sources should be treated as unverified.","sources":"Sources used","empty":"Enter two project names to compare.","same":"Choose two different projects.","failed":"Comparison could not be generated. Check the search provider, FORTYTWO_API_KEY and Render logs."},
    "es": {"page_title":"Comparación de proyectos","lab":"LABORATORIO DE COMPARACIÓN","home":"Inicio de investigación","eyebrow":"INTELIGENCIA DE PROYECTOS DE CÓDIGO ABIERTO","hero":"Compare proyectos con pruebas.","description":"Compare la actividad de GitHub, la madurez del producto, la tokenómica y el ecosistema con fuentes.","project_a":"Proyecto A","project_b":"Proyecto B","example_a":"p. ej., Sentient","example_b":"p. ej., GenLayer","report_language":"Idioma del informe","compare":"Comparar proyectos","form_note":"Los precios, listados y datos del ecosistema solo se incluyen cuando hay fuentes. La actividad de GitHub no mide por sí sola la calidad.","live_signals":"Indicadores de desarrollo en vivo","possible_match":"Posible repositorio coincidente: verifique los datos antes de usarlos.","stars":"Estrellas","forks":"Forks","commits30":"Commits · 30 días","commits90":"Commits · 90 días","language":"Lenguaje","last_push":"Última actualización","unknown":"Desconocido","no_repo":"No se encontró una coincidencia fiable en GitHub. Los datos no se consideran cero.","research_comparison":"Comparación basada en investigación","research_note":"Se resumen la tokenómica, los listados, la madurez del producto y las pruebas del ecosistema. Las afirmaciones sin fuentes deben considerarse no verificadas.","sources":"Fuentes utilizadas","empty":"Introduzca dos proyectos para comparar.","same":"Elija dos proyectos diferentes.","failed":"No se pudo generar la comparación. Revise el proveedor de búsqueda, FORTYTWO_API_KEY y los registros de Render."},
    "pt": {"page_title":"Comparação de projetos","lab":"LABORATÓRIO DE COMPARAÇÃO","home":"Página inicial de pesquisa","eyebrow":"INTELIGÊNCIA DE PROJETOS DE CÓDIGO ABERTO","hero":"Compare projetos com evidências.","description":"Compare atividade no GitHub, maturidade do produto, tokenomics e ecossistema com fontes.","project_a":"Projeto A","project_b":"Projeto B","example_a":"ex.: Sentient","example_b":"ex.: GenLayer","report_language":"Idioma do relatório","compare":"Comparar projetos","form_note":"Preços, listagens e dados do ecossistema só são apresentados quando há fontes. A atividade no GitHub não mede sozinha a qualidade.","live_signals":"Indicadores de desenvolvimento ao vivo","possible_match":"Possível repositório correspondente — verifique antes de confiar nos dados.","stars":"Estrelas","forks":"Forks","commits30":"Commits · 30 dias","commits90":"Commits · 90 dias","language":"Linguagem","last_push":"Última atualização","unknown":"Desconhecido","no_repo":"Não foi encontrada uma correspondência confiável no GitHub. Os dados não são tratados como zero.","research_comparison":"Comparação baseada em pesquisa","research_note":"Tokenomics, listagens, maturidade do produto e evidências do ecossistema são resumidas abaixo. Afirmações sem fontes devem ser consideradas não verificadas.","sources":"Fontes utilizadas","empty":"Digite dois projetos para comparar.","same":"Escolha dois projetos diferentes.","failed":"Não foi possível gerar a comparação. Verifique o provedor de pesquisa, FORTYTWO_API_KEY e os logs do Render."},
    "zh": {"page_title":"项目比较","lab":"比较实验室","home":"研究首页","eyebrow":"开源项目情报","hero":"用证据比较项目。","description":"结合来源并排比较 GitHub 活动、产品成熟度、代币经济和生态信息。","project_a":"项目 A","project_b":"项目 B","example_a":"例如：Sentient","example_b":"例如：GenLayer","report_language":"报告语言","compare":"比较项目","form_note":"只有在来源支持时才报告代币价格、交易所上市和生态信息。GitHub 活动本身不能衡量项目质量。","live_signals":"实时开发指标","possible_match":"可能匹配的仓库——使用指标前请先核实。","stars":"星标","forks":"复刻","commits30":"最近 30 天提交","commits90":"最近 90 天提交","language":"语言","last_push":"最后推送","unknown":"未知","no_repo":"未找到足够可靠的 GitHub 仓库匹配。不会将缺失指标视为零。","research_comparison":"基于研究的比较","research_note":"下方总结代币经济、上市情况、产品成熟度和生态证据。没有来源支持的说法应视为未经验证。","sources":"使用的来源","empty":"请输入两个项目名称进行比较。","same":"请选择两个不同的项目。","failed":"无法生成比较。请检查搜索服务、FORTYTWO_API_KEY 和 Render 日志。"},
    "ru": {"page_title":"Сравнение проектов","lab":"ЛАБОРАТОРИЯ СРАВНЕНИЯ","home":"Главная исследований","eyebrow":"АНАЛИТИКА ПРОЕКТОВ С ОТКРЫТЫМ КОДОМ","hero":"Сравнивайте проекты на основе доказательств.","description":"Сравните активность GitHub, зрелость продукта, токеномику и экосистему с источниками.","project_a":"Проект A","project_b":"Проект B","example_a":"например, Sentient","example_b":"например, GenLayer","report_language":"Язык отчёта","compare":"Сравнить проекты","form_note":"Цены токенов, листинги и сведения об экосистеме приводятся только при наличии источников. Активность GitHub сама по себе не определяет качество проекта.","live_signals":"Текущие показатели разработки","possible_match":"Возможно, найден подходящий репозиторий — проверьте данные.","stars":"Звёзды","forks":"Форки","commits30":"Коммиты · 30 дней","commits90":"Коммиты · 90 дней","language":"Язык","last_push":"Последнее обновление","unknown":"Неизвестно","no_repo":"Надёжное совпадение репозитория GitHub не найдено. Отсутствующие данные не считаются нулём.","research_comparison":"Сравнение на основе исследований","research_note":"Ниже приведены сведения о токеномике, листингах, зрелости продукта и экосистеме. Утверждения без источников считаются неподтверждёнными.","sources":"Использованные источники","empty":"Введите названия двух проектов для сравнения.","same":"Выберите два разных проекта.","failed":"Не удалось выполнить сравнение. Проверьте поиск, FORTYTWO_API_KEY и журналы Render."}
}

@app.route("/compare", methods=["GET", "POST"])
def compare_projects():
    if request.method == "POST":
        _check_csrf()
    a = request.form.get("project_a", "").strip()
    b = request.form.get("project_b", "").strip()
    dil = request.form.get("dil", request.args.get("lang", request.cookies.get("prey-language", "tr"))).strip()
    if dil not in LANGUAGES:
        dil = "tr"
    result = None
    error = None
    t = COMPARE_TRANSLATIONS.get(dil, COMPARE_TRANSLATIONS["tr"])
    if request.method == "POST":
        if not a or not b:
            error = t["empty"]
        elif a.casefold() == b.casefold():
            error = t["same"]
        else:
            try:
                github = []
                for project in (a, b):
                    try:
                        data = github_gelisim_verisi(project, max_commit=100)
                    except Exception:
                        logger.exception("GitHub comparison lookup failed for %s", project)
                        data = None
                    github.append({"project": project, "data": data})
                sources = []
                for project in (a, b):
                    try:
                        found = webde_ara(project, max_sonuc=4) or []
                        for item in found:
                            if item.get("url") and not any(x.get("url") == item.get("url") for x in sources):
                                sources.append(item)
                    except Exception:
                        logger.exception("Comparison web search failed for %s", project)
                topic = (f"Compare {a} and {b} in {LANGUAGES[dil]} using a complete evidence checklist. Cover identity/official links; purpose/users; technology and integrations; products and actual release status; GitHub repository match, license, recent commits/releases; roadmap and delivered milestones; open-source transparency; team/founders; funding/investors; token status, network/contract, supply/circulating supply, allocations, vesting/unlocks and utility; exchange listings and dated market data; ecosystem, partnerships and governance; security audits, auditor/scope/date, bug bounty and incidents; dated recent developments; strengths; risks; contradictory/unverified claims. For every category label status as Verified, Partially verified, Not found, or Conflicting. Use only provided source material and URLs; distinguish official sources from third-party sources; never infer that missing evidence proves something does not exist; do not invent facts, prices, listings or partnerships; explicitly say when data is missing or stale; do not give investment advice. Include a coverage table and source list explaining which claims each URL supports.")
                report_text = ai_analizi(topic, proje_verisi={"project_a": a, "project_b": b, "github": github}, arama_sonuclari=sources, dil=dil)
                result = {"github": github, "sources": sources, "report": render_report(report_text)}
                if not sources and all(not x["data"] for x in github):
                    error = t["no_repo"] if not sources else None
            except Exception:
                logger.exception("Project comparison failed")
                error = t["failed"]
    return render_template_string(COMPARE_HTML, a=a, b=b, dil=dil, languages=LANGUAGES, result=result, error=error, t=t)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

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


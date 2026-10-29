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

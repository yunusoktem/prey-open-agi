
import os
import logging

import bleach
import markdown
from flask import Flask, request, render_template_string
from markupsafe import Markup

from analiz import (
    LANGUAGES,
    ai_analizi,
    webde_ara,
    kayitli_proje_getir,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union({
    "p", "h1", "h2", "h3", "h4", "hr", "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "blockquote", "br", "strong", "em",
})

ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel"],
    "th": ["align"],
    "td": ["align"],
}

HTML = """
<!doctype html>
<html lang="{{ lang }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prey Open AGI — Project Research</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0b1020;color:#eef2ff;font-family:Inter,system-ui,sans-serif}
main{max-width:1120px;margin:0 auto;padding:42px 24px}
.brand{color:#8795ff;letter-spacing:.2em;font-size:14px;font-weight:700;margin-bottom:26px}
h1{font-size:clamp(32px,5vw,48px);line-height:1.12;margin:0 0 18px}
.intro{color:#aeb9d2;line-height:1.7;margin-bottom:28px}
form{display:flex;gap:12px;margin:26px 0;flex-wrap:wrap}
input,select{flex:1;min-width:180px;background:#151d31;color:#fff;border:1px solid #303a52;border-radius:9px;padding:15px;font-size:16px}
button{background:#7184ff;color:white;border:0;border-radius:9px;padding:0 24px;min-height:50px;font-weight:700;cursor:pointer}
.panel{background:#121a2c;border:1px solid #2b354d;border-radius:14px;padding:24px;margin-top:22px;line-height:1.75;overflow-wrap:anywhere}
.report h1,.report h2,.report h3{line-height:1.3;margin:1.3em 0 .5em}
.report h1{font-size:1.6rem}
.report h2{font-size:1.35rem}
.report h3{font-size:1.1rem}
.report table{display:block;overflow-x:auto;border-collapse:collapse;max-width:100%}
.report th,.report td{border:1px solid #3a4660;padding:8px 10px;text-align:left}
.report th{background:#1b2740}
.report a{color:#aab8ff;overflow-wrap:anywhere}
.report code{background:#202b42;padding:2px 5px;border-radius:4px}
.report pre{background:#0a1020;padding:14px;border-radius:8px;overflow:auto}
.error{color:#ffb4bf}
.small{font-size:13px;color:#7f8ba8;margin-top:34px}
.notice{font-size:14px;color:#b9c4dc}
@media(max-width:650px){
main{padding:28px 15px}
form{flex-direction:column}
input,select,button{width:100%}
.panel{padding:16px}
}
</style>
</head>
<body>
<main>
<div class="brand">PREY OPEN AGI</div>
<h1>Understand Open AGI Projects.</h1>
<p class="intro">
Research projects, inspect available sources, and assess technology,
openness, products, token economics, and risks.
</p>

<form method="post">
<input name="project" value="{{ project }}" maxlength="100"
placeholder="Project name (e.g. Sentient)" required>

<select name="lang" aria-label="Report language">
{% for code, name in languages.items() %}
<option value="{{ code }}" {% if code == lang %}selected{% endif %}>
{{ name }}
</option>
{% endfor %}
</select>

<button type="submit">Analyze Project</button>
</form>

{% if message %}
<section class="panel error">{{ message }}</section>
{% endif %}

{% if report %}
<section class="panel report">{{ report }}</section>
<p class="notice">
Search results: {{ source_count }}. Search snippets are leads,
not independent verification.
</p>
{% endif %}

<div class="small">
Prey Open AGI · AI-assisted research · Verify important claims with primary sources.
</div>
</main>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    project = ""
    lang = "tr"
    report_html = ""
    message = ""
    source_count = 0

    if request.method == "POST":
        project = request.form.get("project", "").strip()
        lang = request.form.get("lang", "tr")

        if lang not in LANGUAGES:
            lang = "tr"

        if not project:
            message = "Lütfen bir proje adı yaz."
        elif len(project) > 100:
            message = "Proje adı en fazla 100 karakter olabilir."
        else:
            try:
                stored = kayitli_proje_getir(project)
                results = webde_ara(project)
                source_count = len(results)

                report_text = ai_analizi(
                    project,
                    stored,
                    results,
                    dil=lang,
                )

                if not results:
                    report_text += (
                        "\n\n---\n\n"
                        "**Research limitation:** Web search returned no results. "
                        "Some information may be missing."
                    )

                rendered = markdown.markdown(
                    report_text,
                    extensions=["tables", "fenced_code", "sane_lists"],
                    output_format="html5",
                )

                report_html = Markup(
                    bleach.clean(
                        rendered,
                        tags=ALLOWED_TAGS,
                        attributes=ALLOWED_ATTRIBUTES,
                        protocols={"http", "https", "mailto"},
                        strip=True,
                    )
                )

            except Exception as exc:
                app.logger.exception(
                    "Project analysis failed for %r", project
                )
                message = (
                    str(exc)
                    if isinstance(exc, RuntimeError)
                    else "Analysis failed. Check Render Logs for details."
                )

    return render_template_string(
        HTML,
        project=project,
        lang=lang,
        languages=LANGUAGES,
        report=report_html,
        message=message,
        source_count=source_count,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

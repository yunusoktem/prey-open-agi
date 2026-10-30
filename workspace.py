"""Low-cost multi-mode AI workspace for Prey Open AGI."""
import logging
from flask import request, render_template_string
from analiz import LANGUAGES, ai_analizi, webde_ara

log = logging.getLogger(__name__)
MODES = {
    "research": "Act as a rigorous research analyst. Separate verified facts, assumptions and unknowns. Never invent sources or facts.",
    "web3": "Act as a Web3 protocol analyst. Assess product status, architecture, token utility, supply, unlocks, integrations, security and risks. Never invent metrics, prices, listings or partnerships. No investment advice.",
    "coding": "Act as a senior software engineer. Diagnose the problem, preserve existing behavior, propose safe maintainable code, and include tests and security considerations."
}
PAGE = """
<!doctype html><html lang="{{lang}}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Workspace · Prey Open AGI</title>
<style>
body{margin:0;background:#08131d;color:#edf1ff;font:15px/1.6 system-ui}.wrap{max-width:900px;margin:auto;padding:30px 18px}.panel{background:#102330;border:1px solid #254252;border-radius:18px;padding:22px;margin:18px 0}a{color:#39d6c4}label{display:block;margin:12px 0 6px;color:#a0abc5}select,textarea{width:100%;box-sizing:border-box;padding:13px;border-radius:10px;border:1px solid #254252;background:#0b1a25;color:#edf1ff;font:inherit}textarea{min-height:170px}button{width:100%;padding:14px;border:0;border-radius:10px;margin-top:14px;background:linear-gradient(100deg,#39d6c4,#65aaff);font-weight:800;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.mode{border:1px solid #254252;border-radius:12px;padding:12px}.result{overflow-wrap:anywhere}.result a{color:#39d6c4}@media(max-width:650px){.grid{grid-template-columns:1fr}}
</style></head><body><main class="wrap"><a href="/">← Prey Open AGI</a><h1>AI Workspace</h1><p>One workspace. Three focused modes.</p>
<section class="panel"><form method="post"><label>Workspace mode</label><div class="grid">
<label class="mode"><input type="radio" name="mode" value="research" {% if mode=='research' %}checked{% endif %}> AI Research</label>
<label class="mode"><input type="radio" name="mode" value="web3" {% if mode=='web3' %}checked{% endif %}> Web3 Intelligence</label>
<label class="mode"><input type="radio" name="mode" value="coding" {% if mode=='coding' %}checked{% endif %}> AI Coding</label></div>
<label for="task">Describe your task</label><textarea id="task" name="task" maxlength="12000" required>{{task}}</textarea>
<label for="lang">Response language</label><select id="lang" name="lang">{% for c,n in languages.items() %}<option value="{{c}}" {% if c==lang %}selected{% endif %}>{{n}}</option>{% endfor %}</select>
<label><input type="checkbox" name="search" value="yes" {% if use_search %}checked{% endif %}> Enable free web search (off by default to save credits)</label>
<button type="submit">Run</button></form></section>
{% if error %}<section class="panel">{{error}}</section>{% endif %}{% if report %}<section class="panel"><h2>Result</h2><div class="result">{{report}}</div></section>{% endif %}
</main></body></html>
"""

def register_workspace(app, render_report):
    @app.route("/workspace", methods=["GET", "POST"])
    def workspace():
        mode = request.form.get("mode", "research")
        if mode not in MODES:
            mode = "research"
        lang = request.form.get("lang", "tr")
        if lang not in LANGUAGES:
            lang = "tr"
        task = request.form.get("task", "").strip()
        use_search = request.form.get("search") == "yes"
        report = error = None
        if request.method == "POST":
            if not task or len(task) > 12000:
                error = "Please enter a task under 12,000 characters."
            else:
                try:
                    sources = webde_ara(task, max_sonuc=3) if use_search else []
                    context = {"mode": mode, "instructions": MODES[mode], "task": task}
                    answer = ai_analizi(task, proje_verisi=context, arama_sonuclari=sources or [], dil=lang)
                    report = render_report(answer)
                except Exception:
                    log.exception("AI workspace failed")
                    error = "Request failed. Check the Fortytwo API key and Render logs."
        return render_template_string(PAGE, mode=mode, lang=lang, languages=LANGUAGES,
                                      task=task, use_search=use_search, report=report, error=error)

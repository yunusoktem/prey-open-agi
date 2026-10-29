import os
from flask import Flask, request, render_template_string
from analiz import ai_analizi, webde_ara, kayitli_proje_getir

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prey Open AGI — Project Research</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0b1020;color:#eef2ff;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1120px;margin:0 auto;padding:42px 24px}
.brand{color:#8795ff;letter-spacing:.2em;font-size:14px;font-weight:700;margin-bottom:26px}
h1{font-size:clamp(32px,5vw,48px);line-height:1.12;margin:0 0 18px}
.intro{color:#aeb9d2;line-height:1.7;margin-bottom:28px}
form{display:flex;gap:12px;margin:26px 0}
input{flex:1;min-width:0;background:#151d31;color:#fff;border:1px solid #303a52;border-radius:9px;padding:16px;font-size:16px}
button{background:#7184ff;color:white;border:0;border-radius:9px;padding:0 24px;font-weight:700;cursor:pointer}
button:disabled{opacity:.6}
.panel{background:#121a2c;border:1px solid #2b354d;border-radius:14px;padding:24px;margin-top:22px;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere}
.error{color:#ff9aab}
.small{font-size:13px;color:#7f8ba8;margin-top:34px}
@media(max-width:650px){form{flex-direction:column}button{padding:15px}}
</style>
</head>
<body><main>
<div class="brand">PREY OPEN AGI</div>
<h1>Understand Open AGI Projects.</h1>
<p class="intro">Araştır, kaynakları incele ve açık AGI projelerinin teknolojisini, açıklık durumunu, ürünlerini ve risklerini tek bir yerde değerlendir.</p>
<form method="post">
<input name="project" value="{{ project }}" placeholder="Proje adı yaz (ör. Sentient, Open AGI)" required>
<button type="submit">Analyze Project</button>
</form>
{% if message %}<section class="panel error">{{ message }}</section>{% endif %}
{% if report %}<section class="panel">{{ report }}</section>{% endif %}
<div class="small">Prey Open AGI · AI-assisted research · Sonuçları kaynaklardan ayrıca doğrulayın.</div>
</main></body></html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    project = ""
    report = ""
    message = ""
    if request.method == "POST":
        project = request.form.get("project", "").strip()
        if not project:
            message = "Lütfen bir proje adı yaz."
        elif len(project) > 100:
            message = "Proje adı en fazla 100 karakter olabilir."
        else:
            try:
                stored = kayitli_proje_getir(project)
                results = webde_ara(project)
                report = ai_analizi(project, stored, results)
                if not results:
                    report += "\n\nNot: Web araması sonuç döndürmedi; bu rapor kayıtlı veriyle sınırlı olabilir."
            except Exception as e:
                app.logger.exception("Project analysis failed")
                message = "Analiz sırasında hata oluştu. Render Logs bölümündeki son hata satırlarını kontrol et."
    return render_template_string(HTML, project=project, report=report, message=message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)


from flask import Flask, request, render_template_string
import json
from pathlib import Path
from analiz import ai_analizi

app = Flask(__name__)
KLASOR = Path(__file__).parent
PROJE_DOSYASI = KLASOR / "projeler.json"

HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prey Open AGI</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0b1020;
            color: #f1f5f9;
        }
        .container {
            max-width: 850px;
            margin: 70px auto;
            padding: 25px;
        }
        .brand {
            color: #8b9cff;
            font-size: 15px;
            letter-spacing: 3px;
        }
        h1 {
            font-size: 42px;
            margin-bottom: 12px;
        }
        .description {
            color: #aab4c8;
            line-height: 1.7;
        }
        form {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        input {
            flex: 1;
            min-width: 0;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #303b55;
            background: #141c30;
            color: white;
            font-size: 16px;
        }
        button {
            padding: 15px 20px;
            border: 0;
            border-radius: 8px;
            background: #7185ff;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }
        .result {
            margin-top: 30px;
            padding: 24px;
            border: 1px solid #303b55;
            border-radius: 12px;
            background: #11182a;
            line-height: 1.8;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }
        .error {
            color: #ffaaaa;
        }
        footer {
            margin-top: 45px;
            color: #78849d;
            font-size: 13px;
        }
        @media (max-width: 600px) {
            .container { margin: 30px auto; }
            h1 { font-size: 32px; }
            form { flex-direction: column; }
        }
    </style>
</head>
<body>
    <main class="container">
        <div class="brand">PREY OPEN AGI</div>
        <h1>Understand Open AGI Projects.</h1>
        <p class="description">
            Open AGI ekosistemindeki projeleri analiz et.
            Teknolojilerini, ürünlerini, token ekonomilerini ve
            risklerini tek bir yerde incele.
        </p>

        <form method="POST">
            <input
                type="text"
                name="project"
                placeholder="Proje adı yaz (ör. Sentient)"
                value="{{ project }}"
                required
            >
            <button type="submit">Analyze Project</button>
        </form>

        {% if result %}
            <div class="result">{{ result }}</div>
        {% endif %}

        {% if error %}
            <div class="result error">{{ error }}</div>
        {% endif %}

        <footer>
            Prey Open AGI · AI-powered project analysis
        </footer>
    </main>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def ana_sayfa():
    result = ""
    error = ""
    project = ""

    if request.method == "POST":
        project = request.form.get("project", "").strip()

        try:
            with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
                projeler = json.load(dosya)

            anahtar = project.lower()

            if anahtar not in projeler:
                mevcut = ", ".join(projeler.keys())
                error = (
                    "Bu proje henüz veri tabanımızda yok. "
                    f"Kayıtlı projeler: {mevcut}"
                )
            else:
                result = ai_analizi(projeler[anahtar])

        except Exception as hata:
            error = f"Analiz sırasında hata oluştu: {hata}"

    return render_template_string(
        HTML,
        result=result,
        error=error,
        project=project
    )


if __name__ == "__main__":
    app.run(debug=False)

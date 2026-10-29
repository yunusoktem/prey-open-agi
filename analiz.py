import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from ddgs import DDGS

KLASOR = Path(__file__).parent
PROJE_DOSYASI = KLASOR / "projeler.json"
load_dotenv(KLASOR / ".env")

API_KEY = os.getenv("FORTYTWO_API_KEY")
API_URL = "https://api.fortytwo.network/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"


def webde_ara(proje_adi, max_sonuc=6):
    """DuckDuckGo üzerinden genel web sonuçlarını toplar."""
    sorgu = f'"{proje_adi}" official website documentation GitHub'
    try:
        with DDGS() as ddgs:
            sonuclar = list(ddgs.text(sorgu, max_results=max_sonuc))
        temiz = []
        for s in sonuclar:
            baslik = s.get("title", "")
            url = s.get("href", "")
            aciklama = s.get("body", "")
            if url and (baslik or aciklama):
                temiz.append({
                    "baslik": baslik,
                    "url": url,
                    "aciklama": aciklama
                })
        return temiz
    except Exception:
        return []


def ai_analizi(proje_adi, proje_verisi=None, arama_sonuclari=None):
    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadi. Render Environment ayarlarini kontrol et."
        )

    proje_verisi = proje_verisi or {}
    arama_sonuclari = arama_sonuclari or []

    kaynak_metni = "\n".join(
        f"- Başlık: {s['baslik']}\n  URL: {s['url']}\n  Açıklama: {s['aciklama']}"
        for s in arama_sonuclari
    ) or "Web aramasından sonuç alınamadı."

    prompt = f"""
Sen Prey Open AGI için dikkatli ve tarafsız bir açık AGI proje analistisin.
Kullanıcının aradığı proje: {proje_adi}

Kurallar:
- Türkçe yaz.
- Yalnızca aşağıdaki kayıtlı veri ve arama sonuçlarını dayanak olarak kullan.
- Arama sonuçlarındaki iddiaları doğrulanmış gerçek gibi sunma; kaynakların ne söylediğini ayırt et.
- Kaynakların desteklemediği bilgileri uydurma; "Doğrulanamadı" veya "Veri eksik" de.
- Projenin gerçekten açık kaynak / açık AGI olup olmadığını incele; yeterli kanıt yoksa bunu açıkça belirt.
- Token bilgisi yoksa tokenı varmış gibi varsayma.
- En sonda "Kaynaklar" başlığıyla kullanılan URL'leri listele.
- Yatırım tavsiyesi verme.

Şu başlıkları kullan:
1. Projenin amacı
2. Açıklık ve açık kaynak durumu
3. Teknoloji ve ürün
4. Token ekonomisi (token yoksa "Uygulanamaz veya doğrulanamadı")
5. Güçlü yönler
6. Riskler ve eksikler
7. Genel değerlendirme
8. Kaynaklar

Kayıtlı proje verisi:
{json.dumps(proje_verisi, ensure_ascii=False, indent=2)}

Web arama sonuçları:
{kaynak_metni}
"""

    yanit = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1800,
            "temperature": 0.2
        },
        timeout=120
    )
    yanit.raise_for_status()
    sonuc = yanit.json()
    metin = sonuc["choices"][0]["message"].get("content")
    if not metin:
        raise RuntimeError("Model boş yanıt döndürdü.")
    return metin.strip()


def kayitli_proje_getir(proje_adi):
    if not PROJE_DOSYASI.exists():
        return {}
    try:
        with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
            projeler = json.load(dosya)
        anahtar = proje_adi.strip().lower()
        if anahtar in projeler:
            return projeler[anahtar]
        for key, value in projeler.items():
            if key.lower() == anahtar:
                return value
        return {}
    except (OSError, json.JSONDecodeError):
        return {}
                return value
        return {}
    except (OSError, json.JSONDecodeError):
        return {}

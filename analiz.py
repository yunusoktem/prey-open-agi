
import json
import os
import logging
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

logger = logging.getLogger(__name__)


def webde_ara(proje_adi, max_sonuc=6):
    """DuckDuckGo üzerinden genel web sonuçlarını toplar."""
    sorgu = f'"{proje_adi}" official website documentation GitHub'

    try:
        with DDGS() as ddgs:
            sonuclar = list(
                ddgs.text(sorgu, max_results=max_sonuc)
            )

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
        logger.exception("Web araması başarısız oldu.")
        return []


def ai_analizi(proje_adi, proje_verisi=None, arama_sonuclari=None, dil="tr"):
    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadı. Render Environment ayarını kontrol et."
        )

    diller = {
        "tr": "Türkçe",
        "en": "English",
        "es": "Español",
        "pt": "Português",
        "zh": "简体中文",
        "ru": "Русский"
    }
    dil = dil if dil in diller else "tr"

    proje_verisi = proje_verisi or {}
    arama_sonuclari = arama_sonuclari or []

    kaynak_metni = "\n".join(
        f"- Başlık: {s.get('baslik', '')}\n"
        f"  URL: {s.get('url', '')}\n"
        f"  Açıklama: {s.get('aciklama', '')}"
        for s in arama_sonuclari
    ) or "Web aramasından sonuç alınamadı."

    prompt = f"""
Sen Prey Open AGI için dikkatli ve tarafsız bir proje analistisin.
Raporun tamamını {diller[dil]} dilinde yaz.

Proje adı: {proje_adi}

Kurallar:
- Yalnızca aşağıdaki kayıtlı veri ve arama sonuçlarını kullan.
- Arama sonuçlarını doğrulanmış gerçek gibi sunma.
- Bilgi, tarih, token arzı, fiyat veya ortaklık uydurma.
- Kanıt yoksa "Doğrulanamadı" veya "Veri eksik" de.
- Yatırım tavsiyesi verme.
- Yalnızca aşağıda verilen kaynak URL'lerini listele.
- Başlıklar, maddeler ve tablolar için Markdown kullan.

Bölümler:
1. Yönetici özeti
2. Projenin amacı
3. Teknoloji ve mimari
4. Ürünler ve geliştirme durumu
5. Açık kaynak ve açık AGI durumu
6. Token ekonomisi
7. Ekip ve ekosistem
8. Son gelişmeler
9. Güçlü yönler
10. Riskler ve eksikler
11. Genel değerlendirme
12. Kaynaklar

Kayıtlı proje verisi:
{json.dumps(proje_verisi, ensure_ascii=False, indent=2)}

Web arama sonuçları:
{kaynak_metni}
"""

    try:
        yanit = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2400,
                "temperature": 0.2
            },
            timeout=(10, 150)
        )
        yanit.raise_for_status()

    except requests.Timeout as hata:
        logger.exception("Fortytwo API zaman aşımına uğradı.")
        raise RuntimeError(
            "Fortytwo yanıtı zaman aşımına uğradı. Tekrar denemeden önce kredi kullanımını kontrol et."
        ) from hata

    except requests.HTTPError as hata:
        durum = hata.response.status_code if hata.response is not None else "bilinmiyor"
        logger.exception("Fortytwo API HTTP hatası: %s", durum)
        raise RuntimeError(
            f"Fortytwo API HTTP {durum} hatası döndürdü. Ayrıntı Render Logs bölümünde."
        ) from hata

    except requests.RequestException as hata:
        logger.exception("Fortytwo API bağlantı hatası.")
        raise RuntimeError(
            "Fortytwo API bağlantı hatası oluştu. Ayrıntı Render Logs bölümünde."
        ) from hata

    try:
        sonuc = yanit.json()
        metin = sonuc["choices"][0]["message"].get("content")
    except (ValueError, KeyError, IndexError, TypeError) as hata:
        logger.exception("Fortytwo API beklenmeyen yanıt döndürdü.")
        raise RuntimeError(
            "Fortytwo API beklenmeyen yanıt döndürdü."
        ) from hata

    if not metin or not metin.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return metin.strip()


def kayitli_proje_getir(proje_adi):
    if not PROJE_DOSYASI.exists():
        return {}

    try:
        with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
            projeler = json.load(dosya)

        anahtar = proje_adi.strip().casefold()

        for key, value in projeler.items():
            if key.casefold() == anahtar:
                return value if isinstance(value, dict) else {"veri": value}

        return {}

    except (OSError, json.JSONDecodeError):
        logger.exception("Proje verisi okunamadı.")
        return {}

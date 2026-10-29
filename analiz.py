
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

LANGUAGES = {
    "tr": "Türkçe",
    "en": "English",
    "es": "Español",
    "pt": "Português",
    "zh": "简体中文",
    "ru": "Русский",
}


def webde_ara(proje_adi, max_sonuc=6):
    """DuckDuckGo üzerinden proje hakkında arama yapar."""
    sorgular = [
        f'"{proje_adi}" official website documentation',
        f'"{proje_adi}" GitHub open source',
        f'"{proje_adi}" tokenomics products news',
    ]

    sonuclar = []
    gorulen_urller = set()

    for sorgu in sorgular:
        try:
            with DDGS() as ddgs:
                bulunanlar = list(
                    ddgs.text(sorgu, max_results=max_sonuc)
                )

            for s in bulunanlar:
                baslik = s.get("title", "")
                url = s.get("href", "")
                aciklama = s.get("body", "")

                if not url or url in gorulen_urller:
                    continue

                if not (baslik or aciklama):
                    continue

                gorulen_urller.add(url)

                sonuclar.append({
                    "baslik": baslik,
                    "url": url,
                    "aciklama": aciklama,
                })

                if len(sonuclar) >= max_sonuc * 2:
                    return sonuclar

        except Exception:
            logger.exception(
                "Web araması başarısız: %s", sorgu
            )

    return sonuclar


def kayitli_proje_getir(proje_adi):
    """Projeyi projeler.json dosyasında arar."""
    if not PROJE_DOSYASI.exists():
        logger.warning("projeler.json dosyası bulunamadı.")
        return {}

    try:
        with open(
            PROJE_DOSYASI, "r", encoding="utf-8"
        ) as dosya:
            projeler = json.load(dosya)

        anahtar = proje_adi.strip().casefold()

        for key, value in projeler.items():
            if key.casefold() == anahtar:
                if isinstance(value, dict):
                    return value
                return {"veri": value}

        return {}

    except (OSError, json.JSONDecodeError):
        logger.exception("Proje verileri okunamadı.")
        return {}


def ai_analizi(
    proje_adi,
    proje_verisi=None,
    arama_sonuclari=None,
    dil="tr",
):
    """Fortytwo API kullanarak proje araştırma raporu oluşturur."""

    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadı. "
            "Render Environment ayarını kontrol et."
        )

    if dil not in LANGUAGES:
        dil = "tr"

    proje_verisi = proje_verisi or {}
    arama_sonuclari = arama_sonuclari or []

    kaynak_metni = "\n\n".join(
        (
            f"- Başlık: {s.get('baslik', '')}\n"
            f"  URL: {s.get('url', '')}\n"
            f"  Açıklama: {s.get('aciklama', '')}"
        )
        for s in arama_sonuclari
    )

    if not kaynak_metni:
        kaynak_metni = (
            "Web araması sonuç döndürmedi. "
            "Kaynak veya bilgi uydurma."
        )

    prompt = f"""
Sen Prey Open AGI için dikkatli ve tarafsız bir
açık AGI proje araştırma analistisin.

Raporun tamamını {LANGUAGES[dil]} dilinde yaz.
Proje ve ürün isimlerini özgün bırak.

Proje adı: {proje_adi}

KURALLAR:
- Yalnızca aşağıdaki kayıtlı veriyi ve arama sonuçlarını kullan.
- Arama sonuçlarını doğrulanmış gerçek gibi sunma.
- Eksik bilgileri uydurma; "Doğrulanamadı" veya
  "Veri eksik" şeklinde belirt.
- Token, fiyat, arz, borsa, ekip, ortaklık ve tarih
  bilgilerini kanıt olmadan kesinmiş gibi yazma.
- Web sayfalarının tamamını okuduğunu iddia etme.
  Sana yalnızca aşağıdaki arama parçacıkları veriliyor.
- Yatırım tavsiyesi verme.
- Kaynaklar bölümünde yalnızca verilen URL'leri kullan.
- Markdown biçiminde, düzenli ve okunabilir bir rapor yaz.
- Aynı uyarıları gereksiz yere tekrar etme.

BÖLÜMLER:
1. Yönetici özeti
2. Projenin amacı ve hedef kullanıcıları
3. Teknoloji ve mimari
4. Ürünler ve geliştirme durumu
5. Açık kaynak ve açık AGI durumu
6. Token ekonomisi
7. Ekip, ekosistem ve ortaklıklar
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
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "max_tokens": 2400,
                "temperature": 0.2,
            },
            timeout=(10, 150),
        )
        yanit.raise_for_status()

    except requests.Timeout as hata:
        logger.exception("Fortytwo API zaman aşımı.")
        raise RuntimeError(
            "Fortytwo yanıtı zaman aşımına uğradı. "
            "Yeniden denemeden önce kredi kullanımını kontrol et."
        ) from hata

    except requests.HTTPError as hata:
        durum = (
            hata.response.status_code
            if hata.response is not None
            else "bilinmiyor"
        )
        logger.exception("Fortytwo API HTTP hatası: %s", durum)
        raise RuntimeError(
            f"Fortytwo API HTTP {durum} hatası verdi. "
            "Ayrıntılar Render Logs bölümünde."
        ) from hata

    except requests.RequestException as hata:
        logger.exception("Fortytwo bağlantı hatası.")
        raise RuntimeError(
            "Fortytwo API bağlantı hatası oluştu. "
            "Ayrıntılar Render Logs bölümünde."
        ) from hata

    try:
        sonuc = yanit.json()
        metin = sonuc["choices"][0]["message"].get("content")

    except (ValueError, KeyError, IndexError, TypeError) as hata:
        logger.exception("Fortytwo beklenmeyen yanıt döndürdü.")
        raise RuntimeError(
            "Fortytwo API beklenmeyen bir yanıt döndürdü."
        ) from hata

    if not metin or not metin.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return metin.strip()


if __name__ == "__main__":
    proje = input("Analiz etmek istediğin proje: ").strip()

    if proje:
        veri = kayitli_proje_getir(proje)
        kaynaklar = webde_ara(proje)

        try:
            rapor = ai_analizi(
                proje,
                veri,
                kaynaklar,
                dil="tr",
            )
            print("\n" + rapor)

        except Exception as hata:
            print(f"\nAnaliz başarısız: {hata}")

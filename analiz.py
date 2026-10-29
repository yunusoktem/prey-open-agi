
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
    """Ücretsiz DuckDuckGo araması; hataları gizlemez."""
    sorgular = [
        f'"{proje_adi}" official website',
        f'"{proje_adi}" documentation GitHub',
        f'"{proje_adi}" products latest news',
    ]

    sonuclar = []
    gorulen_urller = set()
    hatalar = []

    for sorgu in sorgular:
        try:
            with DDGS() as ddgs:
                bulunanlar = list(
                    ddgs.text(
                        sorgu,
                        max_results=max_sonuc,
                        backend="auto",
                    )
                )

            for s in bulunanlar:
                url = (s.get("href") or "").strip()
                if not url or url in gorulen_urller:
                    continue

                baslik = s.get("title", "")
                aciklama = s.get("body", "")

                if not (baslik or aciklama):
                    continue

                gorulen_urller.add(url)
                sonuclar.append({
                    "baslik": baslik,
                    "url": url,
                    "aciklama": aciklama,
                })

        except Exception as hata:
            mesaj = f"{type(hata).__name__}: {hata}"
            hatalar.append(mesaj)
            logger.exception("Web arama hatası: %s", sorgu)

    if not sonuclar and hatalar:
        raise RuntimeError(
            "Web araması başarısız oldu: " + " | ".join(hatalar)
        )

    logger.info(
        "Web araması tamamlandı: %s kaynak bulundu.",
        len(sonuclar),
    )
    return sonuclar[:max_sonuc * 2]


def ai_analizi(proje_adi, proje_verisi=None, arama_sonuclari=None):
    """Fortytwo API ile proje analiz raporu oluşturur."""
    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadı. "
            "Render Environment ayarlarını kontrol et."
        )

    proje_verisi = proje_verisi or {}
    arama_sonuclari = arama_sonuclari or []

    kaynak_metni = "\n\n".join(
        f"- Başlık: {s.get('baslik', '')}\n"
        f"  URL: {s.get('url', '')}\n"
        f"  Açıklama: {s.get('aciklama', '')}"
        for s in arama_sonuclari
    )

    if not kaynak_metni:
        raise RuntimeError(
            "Web aramasından kaynak alınamadı. "
            "Kaynaklar düzeltilmeden analiz yapılmadı."
        )

    prompt = f"""
Sen Prey Open AGI için dikkatli ve tarafsız bir
açık AGI proje analistisin.

Proje adı: {proje_adi}

Kurallar:
- Türkçe yaz.
- Yalnızca kayıtlı veriyi ve aşağıdaki arama sonuçlarını dayanak al.
- Arama parçacıklarını doğrulanmış gerçek gibi sunma.
- Kaynakların desteklemediği bilgileri uydurma.
- Eksik bilgileri "Doğrulanamadı" veya "Veri eksik" diye belirt.
- Projenin açık kaynak ve açık AGI durumunu ayrı değerlendir.
- Token, fiyat, arz, borsa, ekip ve ortaklık bilgilerini uydurma.
- Sayfaların tamamını okuduğunu iddia etme.
- Yatırım tavsiyesi verme.
- Kaynaklar bölümünde yalnızca verilen URL'leri kullan.
- Markdown biçiminde düzenli bir rapor hazırla.

Bölümler:
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
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2400,
                "temperature": 0.2,
            },
            timeout=(10, 150),
        )
        yanit.raise_for_status()
        sonuc = yanit.json()
        metin = sonuc["choices"][0]["message"].get("content")

    except requests.RequestException as hata:
        logger.exception("Fortytwo API bağlantı hatası.")
        raise RuntimeError(
            "Fortytwo API isteği başarısız oldu."
        ) from hata
    except (ValueError, KeyError, IndexError, TypeError) as hata:
        logger.exception("Fortytwo API yanıtı okunamadı.")
        raise RuntimeError(
            "Fortytwo API beklenmeyen yanıt döndürdü."
        ) from hata

    if not metin or not metin.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return metin.strip()


def kayitli_proje_getir(proje_adi):
    """Projeyi projeler.json içinde arar."""
    if not PROJE_DOSYASI.exists():
        logger.warning("projeler.json bulunamadı.")
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
        logger.exception("Kayıtlı proje verileri okunamadı.")
        return {}

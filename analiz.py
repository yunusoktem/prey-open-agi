
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
    """Ücretsiz web araması; DDGS ve GitHub yedek araması."""
    sorgular = [
        f'"{proje_adi}" official website',
        f'"{proje_adi}" documentation GitHub',
        f'"{proje_adi}" products latest news',
    ]

    sonuclar = []
    gorulen_urller = set()
    hatalar = []

    def ekle(baslik, url, aciklama):
        url = (url or "").strip()
        if not url or url in gorulen_urller:
            return

        gorulen_urller.add(url)
        sonuclar.append({
            "baslik": baslik or "",
            "url": url,
            "aciklama": aciklama or "",
        })

    # Birincil ücretsiz web araması
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

            for sonuc in bulunanlar:
                ekle(
                    sonuc.get("title", ""),
                    sonuc.get("href", ""),
                    sonuc.get("body", ""),
                )

        except Exception as hata:
            hatalar.append(f"DDGS: {type(hata).__name__}: {hata}")
            logger.exception("DDGS araması başarısız: %s", sorgu)

    # Yedek: ücretsiz GitHub API'si
    if len(sonuclar) < 3:
        try:
            yanit = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f'"{proje_adi}"',
                    "sort": "updated",
                    "per_page": max_sonuc,
                },
                headers={"Accept": "application/vnd.github+json"},
                timeout=(5, 15),
            )
            yanit.raise_for_status()

            for repo in yanit.json().get("items", []):
                ekle(
                    repo.get("full_name", ""),
                    repo.get("html_url", ""),
                    repo.get("description", ""),
                )

        except (requests.RequestException, ValueError) as hata:
            hatalar.append(f"GitHub: {type(hata).__name__}: {hata}")
            logger.exception("GitHub yedek araması başarısız.")

    logger.info(
        "Web araması tamamlandı. Kaynak sayısı: %s",
        len(sonuclar),
    )

    if not sonuclar and hatalar:
        raise RuntimeError(
            "Web araması başarısız oldu. "
            "Ayrıntılar sunucu günlüklerinde."
        )

    return sonuclar[:max_sonuc * 2]


def kayitli_proje_getir(proje_adi):
    """Projeyi projeler.json içinde büyük/küçük harften bağımsız arar."""
    if not PROJE_DOSYASI.exists():
        logger.warning("projeler.json dosyası bulunamadı.")
        return {}

    try:
        with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
            projeler = json.load(dosya)

        if not isinstance(projeler, dict):
            logger.error("projeler.json bir JSON nesnesi olmalı.")
            return {}

        anahtar = proje_adi.strip().casefold()

        for key, value in projeler.items():
            if str(key).casefold() == anahtar:
                if isinstance(value, dict):
                    return value
                return {"veri": value}

        return {}

    except (OSError, json.JSONDecodeError):
        logger.exception("Kayıtlı proje verileri okunamadı.")
        return {}


def ai_analizi(
    proje_adi,
    proje_verisi=None,
    arama_sonuclari=None,
    dil="tr",
):
    """Fortytwo API kullanarak çok dilli proje araştırma raporu oluşturur."""

    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadı. "
            "Render Environment ayarlarını kontrol et."
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
            "Web aramasından sonuç alınamadı. "
            "Harici kaynak bulunamadığını açıkça belirt."
        )

    prompt = f"""
Sen Prey Open AGI için dikkatli ve tarafsız bir
açık AGI proje araştırma analistisin.

Raporun tamamını {LANGUAGES[dil]} dilinde yaz.
Proje ve ürün isimlerini özgün bırak.

Proje adı: {proje_adi}

ARAŞTIRMA KURALLARI:
- Yalnızca aşağıdaki kayıtlı veriyi ve arama sonuçlarını kullan.
- Arama parçacıklarını doğrulanmış gerçek gibi sunma.
- Kaynakların desteklemediği bilgileri uydurma.
- Eksik bilgileri "Doğrulanamadı" veya "Veri eksik" diye belirt.
- Token, fiyat, arz, borsa, ekip ve ortaklık bilgilerini uydurma.
- Web sayfalarının tamamını okuduğunu iddia etme.
- Bir projenin açık kaynaklı olmasıyla açık AGI vizyonunu ayrı değerlendir.
- Kaynak URL'lerini değiştirme veya uydurma.
- Yatırım tavsiyesi verme.
- Raporda analiz tarihi olarak güncel tarihi kullan.
- Tekrarlanan uyarılardan kaçın ve somut bulgulara odaklan.

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
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 3000,
                "temperature": 0.2,
            },
            timeout=(10, 150),
        )
        yanit.raise_for_status()
        sonuc = yanit.json()
        metin = sonuc["choices"][0]["message"].get("content")

    except requests.Timeout as hata:
        logger.exception("Fortytwo API zaman aşımı.")
        raise RuntimeError(
            "Fortytwo API zaman aşımına uğradı."
        ) from hata

    except requests.HTTPError as hata:
        durum = (
            hata.response.status_code
            if hata.response is not None
            else "bilinmiyor"
        )
        logger.exception("Fortytwo API HTTP hatası: %s", durum)
        raise RuntimeError(
            f"Fortytwo API HTTP {durum} hatası verdi."
        ) from hata

    except requests.RequestException as hata:
        logger.exception("Fortytwo API bağlantı hatası.")
        raise RuntimeError(
            "Fortytwo API bağlantısı başarısız oldu."
        ) from hata

    except (ValueError, KeyError, IndexError, TypeError) as hata:
        logger.exception("Fortytwo API yanıtı okunamadı.")
        raise RuntimeError(
            "Fortytwo API beklenmeyen yanıt döndürdü."
        ) from hata

    if not isinstance(metin, str) or not metin.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return metin.strip()


if __name__ == "__main__":
    proje = input("Analiz etmek istediğin proje: ").strip()

    if proje:
        try:
            # Bu bölüm web aramasını tek başına test eder.
            # Fortytwo API'sini çağırmaz ve kredi harcamaz.
            kaynaklar = webde_ara(proje)
            print(f"\nBulunan kaynak sayısı: {len(kaynaklar)}")

            for kaynak in kaynaklar:
                print(f"\n{kaynak['baslik']}")
                print(kaynak["url"])
                print(kaynak["aciklama"])

        except Exception as hata:
            print(f"\nArama başarısız: {hata}")


    


import json
import os
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

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

# Bilinen proje adları için resmî kaynak öncelikleri.
# Yeni projeler bu sözlüğe eklenebilir.
PROJECT_SOURCES = {
    "sentient": {
        "domains": [
            "sentient.foundation",
            "sentientc.ai",
            "sentient.xyz",
            "github.com/sentient-agi",
        ],
        "queries": [
            "Sentient Foundation open source AGI",
            "Sentient AGI official documentation",
            "Sentient AGI GitHub",
        ],
    },
}


def _normalize(text):
    """Karşılaştırma için metni sadeleştirir."""
    text = str(text or "").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _domain(url):
    """URL'den alan adını çıkarır."""
    try:
        return urlparse(url).netloc.casefold().removeprefix("www.")
    except (ValueError, TypeError):
        return ""


def _project_config(project_name):
    """Proje adına ait bilinen kaynak ayarlarını getirir."""
    return PROJECT_SOURCES.get(_normalize(project_name), {})


def _relevance_score(project_name, result, config):
    """Arama sonucunun projeyle alakasına yaklaşık puan verir."""
    title = _normalize(result.get("baslik", ""))
    url = (result.get("url") or "").casefold()
    description = _normalize(result.get("aciklama", ""))
    domain = _domain(url)

    project = _normalize(project_name)
    words = [word for word in project.split() if len(word) > 2]

    score = 0

    if project and project in title:
        score += 5
    elif project and project in description:
        score += 3

    if words:
        matched = sum(
            1 for word in words
            if word in title or word in description or word in url
        )
        score += min(matched * 2, 5)

    # Bilinen resmî alan adlarını güçlü biçimde önceliklendir.
    for known in config.get("domains", []):
        known = known.casefold()

        if known.startswith("github.com/"):
            if urlparse(url).path.casefold().startswith(
                "/" + known.split("/", 1)[1]
            ):
                score += 10
                break
        elif domain == known or domain.endswith("." + known):
            score += 10
            break

    if "github.com/" in url:
        score += 2

    # Sentient ismiyle eşleşen ilgisiz jet sitelerini ele.
    if _normalize(project_name) == "sentient":
        unrelated_terms = (
            "private jet",
            "jet card",
            "aviation",
            "cardholder",
        )
        combined = f"{title} {description} {_normalize(url)}"
        if any(term in combined for term in unrelated_terms):
            return -100

    return score


def webde_ara(proje_adi, max_sonuc=6):
    """
    Ücretsiz web araması.
    Sonuçları birleştirir, tekrarları kaldırır ve alaka puanına göre sıralar.
    Fortytwo API'sini çağırmaz.
    """
    proje_adi = (proje_adi or "").strip()

    if not proje_adi:
        raise ValueError("Arama için proje adı boş olamaz.")

    max_sonuc = max(1, min(int(max_sonuc), 10))
    config = _project_config(proje_adi)

    sorgular = config.get("queries", [
        f'"{proje_adi}" official website',
        f'"{proje_adi}" documentation GitHub',
        f'"{proje_adi}" products development',
        f'"{proje_adi}" latest announcements',
    ])

    bulunanlar = []
    hatalar = []

    # Ücretsiz metasearch: DDGS, otomatik sağlayıcı seçimiyle çalışır.
    try:
        with DDGS() as ddgs:
            for sorgu in sorgular:
                try:
                    results = ddgs.text(
                        sorgu,
                        max_results=max_sonuc,
                        backend="auto",
                        region="wt-wt",
                    )

                    for item in results or []:
                        bulunanlar.append({
                            "baslik": item.get("title", ""),
                            "url": item.get("href", ""),
                            "aciklama": item.get("body", ""),
                        })

                except Exception as hata:
                    hatalar.append(
                        f"DDGS sorgusu başarısız: "
                        f"{type(hata).__name__}: {hata}"
                    )
                    logger.warning(
                        "DDGS sorgusu başarısız (%s): %s",
                        sorgu,
                        hata,
                    )

    except Exception as hata:
        hatalar.append(
            f"DDGS başlatılamadı: {type(hata).__name__}: {hata}"
        )
        logger.exception("DDGS başlatılamadı.")

    # Ücretsiz GitHub araması; ek kaynak ve yedek olarak kullanılır.
    try:
        github_query = f'"{proje_adi}" in:name,description'
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": github_query,
                "sort": "updated",
                "per_page": max_sonuc,
            },
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Prey-Open-AGI",
            },
            timeout=(5, 15),
        )

        if response.ok:
            for repo in response.json().get("items", []):
                bulunanlar.append({
                    "baslik": repo.get("full_name", ""),
                    "url": repo.get("html_url", ""),
                    "aciklama": repo.get("description", ""),
                })
        else:
            hatalar.append(
                f"GitHub araması HTTP {response.status_code}"
            )

    except (requests.RequestException, ValueError) as hata:
        hatalar.append(f"GitHub araması başarısız: {hata}")
        logger.warning("GitHub araması başarısız: %s", hata)

    # URL tekrarlarını temizle.
    benzersiz = {}

    for item in bulunanlar:
        url = (item.get("url") or "").strip()

        if not url.startswith(("https://", "http://")):
            continue

        if url not in benzersiz:
            item["puan"] = _relevance_score(
                proje_adi, item, config
            )
            benzersiz[url] = item
        else:
            # Aynı URL farklı sorgularda bulunursa açıklaması daha dolu olanı tut.
            old = benzersiz[url]
            if len(item.get("aciklama", "")) > len(
                old.get("aciklama", "")
            ):
                item["aciklama"] = item.get("aciklama", "")
                item["baslik"] = item.get("baslik") or old.get("baslik", "")

    sirali = sorted(
        benzersiz.values(),
        key=lambda item: (
            item.get("puan", 0),
            bool(item.get("aciklama")),
        ),
        reverse=True,
    )

    # Düşük alaka puanlı sonuçları ele.
    ilgili = [item for item in sirali if item["puan"] >= 2]

    if not ilgili and not bulunanlar and hatalar:
        logger.error("Tüm ücretsiz aramalar başarısız: %s", hatalar)
        raise RuntimeError(
            "Web araması sonuç alamadı. "
            "Arama sağlayıcıları erişilemiyor olabilir."
        )

    # Puan alanını AI'ye göndermeye gerek yok.
    sonuclar = [
        {
            "baslik": item.get("baslik", ""),
            "url": item.get("url", ""),
            "aciklama": item.get("aciklama", ""),
        }
        for item in ilgili[:max_sonuc * 2]
    ]

    logger.info(
        "Arama tamamlandı: %s ham sonuç, %s ilgili kaynak.",
        len(bulunanlar),
        len(sonuclar),
    )

    return sonuclar


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

        anahtar = _normalize(proje_adi)

        for key, value in projeler.items():
            if _normalize(key) == anahtar:
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
    """Fortytwo API kullanarak çok dilli proje raporu oluşturur."""

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
            "Web araması kullanılabilir kaynak döndürmedi. "
            "Bu durumda araştırmanın sınırlı olduğunu belirt; "
            "kaynak, ürün, ekip veya token bilgisi uydurma."
        )

    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""
Sen Prey Open AGI için açık kaynaklı yapay zekâ projelerini
inceleyen, dikkatli ve tarafsız bir araştırma analistisin.

Rapor dili: {LANGUAGES[dil]}
Proje adı: {proje_adi}
Analiz tarihi (UTC): {bugun}

ARAŞTIRMA KURALLARI:
- Yalnızca sağlanan kayıtlı veriyi ve arama sonuçlarını dayanak al.
- Arama parçacıklarını bağımsız doğrulanmış gerçek gibi sunma.
- Sayfaların tamamını okuduğunu iddia etme.
- Kaynaklar çelişiyorsa çelişkiyi açıkça belirt.
- Eksik bilgileri "Doğrulanamadı" veya "Veri eksik" diye belirt.
- Token, fiyat, arz, borsa, ekip ve ortaklık bilgilerini uydurma.
- Açık kaynak lisansı ile açık AGI vizyonunu birbirinden ayır.
- Ürünün canlı, test aşamasında veya yalnızca duyurulmuş olduğunu
  kanıt yoksa kesin biçimde sınıflandırma.
- Kaynak URL'lerini aynen kullan; URL uydurma.
- Yatırım tavsiyesi verme.
- Raporu somut, okunabilir ve gereksiz tekrarlardan uzak yaz.

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

Her önemli bulguyu mümkün olduğunda ilgili URL ile ilişkilendir.
Kaynak yoksa bunu açıkça belirt. Raporu {LANGUAGES[dil]} dilinde yaz.

Kayıtlı proje verisi:
{json.dumps(proje_verisi, ensure_ascii=False, indent=2)}

Web arama sonuçları:
{kaynak_metni}
"""

    try:
        response = requests.post(
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
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"].get("content")

    except requests.Timeout as hata:
        logger.exception("Fortytwo API zaman aşımı.")
        raise RuntimeError(
            "Fortytwo API zaman aşımına uğradı."
        ) from hata

    except requests.HTTPError as hata:
        status = (
            hata.response.status_code
            if hata.response is not None
            else "bilinmiyor"
        )
        logger.exception("Fortytwo API HTTP hatası: %s", status)
        raise RuntimeError(
            f"Fortytwo API HTTP {status} hatası verdi."
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

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return text.strip()


if __name__ == "__main__":
    project = input("Analiz etmek istediğin proje: ").strip()

    if project:
        try:
            # Yalnızca ücretsiz arama çalışır; Fortytwo çağrılmaz.
            sources = webde_ara(project)
            print(f"\nBulunan ilgili kaynak sayısı: {len(sources)}")

            for source in sources:
                print(f"\n{source['baslik']}")
                print(source["url"])
                print(source["aciklama"])

        except Exception as hata:
            print(f"\nArama başarısız: {hata}")

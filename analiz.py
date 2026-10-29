
import json
import os
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin
from ipaddress import ip_address

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

USER_AGENT = "PreyOpenAGI/1.0 (open-source research tool)"
MAX_PAGE_CHARS = 10000
REQUEST_TIMEOUT = (5, 12)


class _TextExtractor(HTMLParser):
    """HTML içinden okunabilir metni çıkarır."""

    SKIP_TAGS = {
        "script", "style", "noscript", "svg", "nav",
        "footer", "header", "form", "iframe", "canvas",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif tag in {"p", "br", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"p", "br", "div", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth and data.strip():
            self.parts.append(data.strip())

    def text(self):
        result = " ".join(self.parts)
        return re.sub(r"\s+", " ", result).strip()


def _norm(value):
    value = str(value or "").casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _safe_public_url(url):
    """Yalnızca herkese açık HTTP(S) adreslerini kabul eder."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False

        host = parsed.hostname.casefold()
        if host == "localhost" or host.endswith(".localhost"):
            return False

        try:
            ip = ip_address(host)
            if not ip.is_global:
                return False
        except ValueError:
            pass

        return True
    except (ValueError, TypeError):
        return False


def _search_queries(project):
    """Her proje için genel amaçlı farklı araştırma sorguları üretir."""
    return [
        f'"{project}" official website',
        f'"{project}" documentation technical architecture',
        f'"{project}" GitHub source code',
        f'"{project}" products development roadmap',
        f'"{project}" team partners announcements',
        f'"{project}" tokenomics token official',
    ]


def _score_result(project, item):
    """Genel alaka puanı; güvenilirliği tek başına kanıtlamaz."""
    title = _norm(item.get("baslik", ""))
    desc = _norm(item.get("aciklama", ""))
    url = (item.get("url") or "").casefold()
    query = _norm(project)
    words = [w for w in query.split() if len(w) > 2]

    score = 0
    if query and query in title:
        score += 6
    elif query and query in desc:
        score += 3

    if words:
        matched = sum(
            1 for word in words
            if word in title or word in desc or word in url
        )
        score += min(matched * 2, 6)

    host = (urlparse(url).hostname or "").casefold()
    if host.startswith("github.com"):
        score += 2
    if any(term in host for term in ("docs.", "developer.", "developers.")):
        score += 1

    # Açıkça alakasız sonuçları cezalandır.
    if query == "sentient":
        unrelated = (
            "private jet", "jet card", "aviation", "cardholder",
        )
        if any(term in f"{title} {desc}" for term in unrelated):
            score -= 20

    return score


def _fetch_page_text(url):
    """Uygunsa sayfanın metnini indirir; başarısızlıkta boş döner."""
    if not _safe_public_url(url):
        return ""

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            stream=True,
        )
        try:
            if not response.ok:
                return ""

            if not _safe_public_url(response.url):
                return ""

            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return ""

            chunks = []
            total = 0

            for chunk in response.iter_content(chunk_size=4096):
                if not chunk:
                    continue
                total += len(chunk)
                chunks.append(chunk)
                if total >= 500_000:
                    break

            raw = b"".join(chunks)[:500_000]
            encoding = response.encoding or "utf-8"
            html = raw.decode(encoding, errors="replace")

            if "text/plain" in content_type:
                text = html
            else:
                parser = _TextExtractor()
                parser.feed(html)
                text = parser.text()

            return text[:MAX_PAGE_CHARS]
        finally:
            response.close()

    except (requests.RequestException, ValueError, UnicodeError) as hata:
        logger.debug("Sayfa okunamadı (%s): %s", url, hata)
        return ""


def webde_ara(proje_adi, max_sonuc=6):
    """
    Ücretsiz DDGS ve GitHub araması.
    Sonuçları birleştirir, puanlar ve erişilebilen sayfaları okur.
    """
    proje = (proje_adi or "").strip()
    if not proje:
        raise ValueError("Arama için proje adı girilmelidir.")

    max_sonuc = max(1, min(int(max_sonuc), 10))
    raw_results = []
    errors = []

    try:
        with DDGS() as ddgs:
            for query in _search_queries(proje):
                try:
                    results = ddgs.text(
                        query,
                        max_results=max_sonuc,
                        backend="auto",
                    )
                    for result in results or []:
                        raw_results.append({
                            "baslik": result.get("title", ""),
                            "url": result.get("href", ""),
                            "aciklama": result.get("body", ""),
                        })
                except Exception as hata:
                    errors.append(f"DDGS: {type(hata).__name__}")
                    logger.warning("Arama sorgusu başarısız: %s", hata)

    except Exception as hata:
        errors.append(f"DDGS başlatılamadı: {type(hata).__name__}")
        logger.exception("DDGS başlatılamadı.")

    # Ücretsiz GitHub araması, web sonuçlarına ek kaynak sağlar.
    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f'"{proje}" in:name,description',
                "sort": "updated",
                "per_page": max_sonuc,
            },
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.ok:
            for repo in response.json().get("items", []):
                raw_results.append({
                    "baslik": repo.get("full_name", ""),
                    "url": repo.get("html_url", ""),
                    "aciklama": repo.get("description", ""),
                })
        else:
            errors.append(f"GitHub HTTP {response.status_code}")

    except (requests.RequestException, ValueError) as hata:
        errors.append(f"GitHub: {type(hata).__name__}")
        logger.warning("GitHub araması başarısız: %s", hata)

    # URL bazında tekrarları temizle ve puanla.
    unique = {}

    for item in raw_results:
        url = (item.get("url") or "").strip()
        if not _safe_public_url(url):
            continue

        if url not in unique:
            item["puan"] = _score_result(proje, item)
            unique[url] = item
        elif len(item.get("aciklama", "")) > len(
            unique[url].get("aciklama", "")
        ):
            unique[url]["aciklama"] = item["aciklama"]

    ranked = sorted(
        unique.values(),
        key=lambda item: item.get("puan", 0),
        reverse=True,
    )

    # Zayıf eşleşmeleri çıkar. Hiç sonuç kalırsa sessizce uydurma yapma.
    relevant = [item for item in ranked if item["puan"] >= 2]
    selected = relevant[:max_sonuc * 2]

    if not selected and errors and not raw_results:
        raise RuntimeError(
            "Ücretsiz arama sağlayıcılarından sonuç alınamadı. "
            "Ayrıntılar sunucu günlüklerinde."
        )

    # İlk birkaç sonucun gerçek sayfa metnini almaya çalış.
    final_results = []
    for item in selected:
        page_text = _fetch_page_text(item["url"])
        description = item.get("aciklama", "")

        final_results.append({
            "baslik": item.get("baslik", ""),
            "url": item["url"],
            "aciklama": description,
            "icerik": page_text,
        })

    logger.info(
        "Araştırma araması: %d ham, %d seçilmiş, %d içerik okundu.",
        len(raw_results),
        len(final_results),
        sum(bool(item["icerik"]) for item in final_results),
    )

    return final_results


def kayitli_proje_getir(proje_adi):
    """Projeyi projeler.json içinde büyük/küçük harften bağımsız arar."""
    if not PROJE_DOSYASI.exists():
        logger.warning("projeler.json dosyası bulunamadı.")
        return {}

    try:
        with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
            projects = json.load(dosya)

        if not isinstance(projects, dict):
            logger.error("projeler.json bir JSON nesnesi olmalı.")
            return {}

        target = _norm(proje_adi)
        for key, value in projects.items():
            if _norm(key) == target:
                return value if isinstance(value, dict) else {"veri": value}

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
    """Fortytwo ile kaynaklı ve çok dilli araştırma raporu üretir."""
    if not API_KEY:
        raise RuntimeError(
            "FORTYTWO_API_KEY bulunamadı. Render Environment ayarlarını kontrol et."
        )

    if dil not in LANGUAGES:
        dil = "tr"

    proje_verisi = proje_verisi or {}
    arama_sonuclari = arama_sonuclari or []

    source_text = "\n\n".join(
        f"Başlık: {s.get('baslik', '')}\n"
        f"URL: {s.get('url', '')}\n"
        f"Arama açıklaması: {s.get('aciklama', '')}\n"
        f"Sayfadan alınan metin: {(s.get('icerik') or '')[:MAX_PAGE_CHARS]}"
        for s in arama_sonuclari
    )

    if not source_text:
        source_text = "Arama sonucu yok. Araştırma sınırlamasını açıkça belirt."

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""
Sen Prey Open AGI için tarafsız bir açık kaynak araştırma analistisin.

Proje/konu: {proje_adi}
Rapor dili: {LANGUAGES[dil]}
Rapor tarihi (UTC): {today}

Kurallar:
- Yalnızca verilen kayıtlı veriyi ve kaynak materyalini kullan.
- Arama açıklaması ile sayfa içeriğini birbirinden ayır.
- Sayfa içeriği yoksa sayfayı okuduğunu iddia etme.
- Kaynakların desteklemediği bilgileri uydurma.
- Çelişkileri, belirsizlikleri ve veri eksiklerini belirt.
- Açık kaynak lisansı ile açık AGI iddiasını birbirinden ayır.
- Token, fiyat, arz, ekip, ortaklık ve yol haritasını kanıtsız kesinleştirme.
- Güncel gelişme tarihi yoksa güncelliği doğrulanamadı de.
- Kaynak URL'lerini aynen kullan.
- Yatırım tavsiyesi verme.
- Raporun tamamını {LANGUAGES[dil]} dilinde yaz.

Bölümler:
1. Yönetici özeti
2. Amaç ve hedef kullanıcılar
3. Teknoloji ve mimari
4. Ürünler ve geliştirme durumu
5. Açık kaynak ve açıklık değerlendirmesi
6. Token ekonomisi veya uygulanabilirliği
7. Ekip, ekosistem ve ortaklıklar
8. Güncel gelişmeler
9. Güçlü yönler
10. Riskler ve doğrulanamayan bilgiler
11. Genel değerlendirme
12. Kaynaklar

Kayıtlı proje verisi:
{json.dumps(proje_verisi, ensure_ascii=False, indent=2)}

Araştırma kaynakları:
{source_text}
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
                "messages": [{"role": "user", "content": prompt}],
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
        raise RuntimeError("Fortytwo API zaman aşımına uğradı.") from hata
    except requests.HTTPError as hata:
        status = hata.response.status_code if hata.response is not None else "?"
        logger.exception("Fortytwo API HTTP hatası: %s", status)
        raise RuntimeError(f"Fortytwo API HTTP {status} hatası verdi.") from hata
    except requests.RequestException as hata:
        logger.exception("Fortytwo bağlantı hatası.")
        raise RuntimeError("Fortytwo API bağlantısı başarısız oldu.") from hata
    except (ValueError, KeyError, IndexError, TypeError) as hata:
        logger.exception("Fortytwo yanıtı okunamadı.")
        raise RuntimeError("Fortytwo API beklenmeyen yanıt döndürdü.") from hata

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Model boş yanıt döndürdü.")

    return text.strip()


if __name__ == "__main__":
    project = input("Aranacak proje veya konu: ").strip()
    if project:
        try:
            # Bu mod testinde Fortytwo API çağrılmaz.
            sources = webde_ara(project)
            print(f"\nBulunan ilgili kaynak: {len(sources)}")
            for source in sources:
                print(f"\n{source['baslik']}")
                print(source["url"])
                print(source["aciklama"])
                if source["icerik"]:
                    print("Sayfa içeriği alındı.")
                else:
                    print("Sayfa içeriği alınamadı; arama açıklaması mevcut olabilir.")
        except Exception as hata:
            print(f"\nArama başarısız: {hata}")

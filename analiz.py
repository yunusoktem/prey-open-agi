

import json
import os
import logging
import re
from datetime import datetime, timezone, timedelta
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
    """Normalize Unicode text without discarding non-Latin project names."""
    import unicodedata

    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in value).split()
    )


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
    """Projeyi farklı başlıklardan araştırır; sonuç bulunmayan alanlar raporda eksik olarak belirtilir."""
    # Keep discovery bounded: DDGS providers are rate-limited and each query
    # can trigger several upstream engines. Broad queries preserve coverage.
    return [
        f'"{project}" official website documentation architecture product',
        f'"{project}" GitHub repository development release roadmap',
        f'"{project}" tokenomics team funding partnerships ecosystem',
        f'"{project}" security audit latest announcement',
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
        # Follow redirects manually so every destination is validated before
        # the server makes a request to it (prevents redirect-based SSRF).
        current_url = url
        response = None
        for _ in range(5):
            response = requests.get(
                current_url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    return ""
                current_url = urljoin(current_url, location)
                if not _safe_public_url(current_url):
                    return ""
                continue
            break
        else:
            if response is not None:
                response.close()
            return ""
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
    selected = relevant[:max_sonuc]

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



def github_gelisim_verisi(proje_adi, max_commit=5):
    """
    GitHub'daki olası depo eşleşmesini ve temel gelişim sinyallerini döndürür.
    Bu metrikler tek başına proje kalitesi veya sürdürülebilirlik kanıtı değildir.
    """
    proje = (proje_adi or "").strip()
    if not proje:
        return None

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f'"{proje}" in:name,description',
                "sort": "updated",
                "order": "desc",
                "per_page": 5,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            logger.warning("GitHub depo araması HTTP %s", response.status_code)
            return None

        items = response.json().get("items", [])
        if not items:
            # İkinci, daha esnek arama
            response = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": proje, "sort": "updated", "order": "desc", "per_page": 5},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if not response.ok:
                return None
            items = response.json().get("items", [])

        if not items:
            return None

        # Önce isim eşleşmesini ara. Emin olunmayan, alakasız depoyu
        # canlı veri gibi göstermemek için zayıf eşleşmede paneli gizle.
        norm_project = _norm(proje)
        project_tokens = set(norm_project.split())
        def match_score(item):
            repo_name = _norm(item.get("name", ""))
            full_name = _norm(item.get("full_name", ""))
            description = _norm(item.get("description", ""))
            repo_tokens = set(repo_name.split())
            desc_tokens = set(description.split())
            if repo_name == norm_project or full_name == norm_project:
                return 100
            if repo_name and repo_name in norm_project:
                return 80
            if norm_project and norm_project in repo_name:
                return 75
            name_overlap = len(project_tokens & repo_tokens) / max(1, len(project_tokens))
            desc_overlap = len(project_tokens & desc_tokens) / max(1, len(project_tokens))
            return max(name_overlap * 60, desc_overlap * 25)

        ranked_items = sorted(items, key=match_score, reverse=True)
        repo = ranked_items[0]
        best_score = match_score(repo)
        if best_score < 30:
            logger.info("Güvenilir GitHub depo eşleşmesi bulunamadı: %s", proje)
            return None

        owner = repo.get("owner", {}).get("login", "")
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")
        base = f"https://api.github.com/repos/{owner}/{name}"
        # Repository details endpoint exposes watchers/subscribers separately from stars.
        try:
            detail_response = requests.get(base, headers=headers, timeout=REQUEST_TIMEOUT)
            if detail_response.ok:
                repo = {**repo, **detail_response.json()}
        except (requests.RequestException, ValueError, TypeError):
            logger.debug("GitHub depo ayrıntıları alınamadı.", exc_info=True)

        result = {
            "name": full_name or name,
            "url": repo.get("html_url", ""),
            "description": repo.get("description") or "Açıklama sağlanmamış.",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "watchers": repo.get("subscribers_count", repo.get("watchers_count", 0)),
            "open_issues": repo.get("open_issues_count", 0),
            "language": repo.get("language") or "Belirtilmemiş",
            "created_at": (repo.get("created_at") or "")[:10],
            "repo_age_days": None,
            "days_since_push": None,
            "commits_last_30_days": None,
            "commits_last_90_days": None,
            "commit_sample_size": 0,
            "weekly_activity": [],
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "updated_at": (repo.get("updated_at") or "")[:10],
            "pushed_at": (repo.get("pushed_at") or "")[:10],
            "default_branch": repo.get("default_branch") or "main",
            "commits": [],
            "latest_release": None,
            "is_exact_match": (
                _norm(repo.get("name", "")) == norm_project
                or _norm(repo.get("full_name", "")) == norm_project
            ),
            "match_confidence": "exact" if (
                _norm(repo.get("name", "")) == norm_project
                or _norm(repo.get("full_name", "")) == norm_project
            ) else "possible",
        }

        # Son commitler + gerçek haftalık aktivite özeti.
        # GitHub'ın son 100 commit'i kullanılır; bu tüm depo geçmişi anlamına gelmez.
        try:
            commits_response = requests.get(
                f"{base}/commits",
                params={"per_page": 100},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if commits_response.ok:
                commit_items = commits_response.json()
                now = datetime.now(timezone.utc)
                dates = []
                for item in commit_items:
                    commit = item.get("commit", {})
                    author = commit.get("author") or {}
                    date_text = author.get("date") or (commit.get("committer") or {}).get("date") or ""
                    try:
                        parsed_date = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        dates.append(parsed_date.astimezone(timezone.utc))
                    except (ValueError, TypeError):
                        parsed_date = None
                    if len(result["commits"]) < max(1, min(int(max_commit), 10)):
                        message = (commit.get("message") or "Commit").splitlines()[0]
                        result["commits"].append({
                            "message": message[:180],
                            "date": date_text[:10],
                            "author": (author.get("name") or "Bilinmiyor")[:80],
                            "url": item.get("html_url", ""),
                        })
                result["commit_sample_size"] = len(dates)
                result["commits_last_30_days"] = sum(1 for d in dates if (now - d).days <= 30 and d <= now)
                result["commits_last_90_days"] = sum(1 for d in dates if (now - d).days <= 90 and d <= now)
                pushed_text = repo.get("pushed_at") or ""
                try:
                    pushed_date = datetime.fromisoformat(pushed_text.replace("Z", "+00:00"))
                    result["days_since_push"] = max(0, (now - pushed_date).days)
                except (ValueError, TypeError):
                    pass
                created_text = repo.get("created_at") or ""
                try:
                    created_date = datetime.fromisoformat(created_text.replace("Z", "+00:00"))
                    result["repo_age_days"] = max(0, (now - created_date).days)
                except (ValueError, TypeError):
                    pass

                # 12 haftalık mini grafik; yalnızca indirilen son 100 commit üzerinden.
                current_monday = now.date() - timedelta(days=now.weekday())
                weeks = []
                for offset in range(11, -1, -1):
                    week_start = current_monday - timedelta(weeks=offset)
                    week_end = week_start + timedelta(days=7)
                    count = sum(1 for d in dates if week_start <= d.date() < week_end)
                    weeks.append({"label": week_start.strftime("%d/%m"), "count": count})
                max_count = max((week["count"] for week in weeks), default=0) or 1
                for week in weeks:
                    week["height"] = max(4, round(week["count"] / max_count * 100))
                result["weekly_activity"] = weeks
        except (requests.RequestException, ValueError, TypeError):
            logger.debug("GitHub commit bilgileri alınamadı.", exc_info=True)

        # En son yayınlanan release
        try:
            release_response = requests.get(
                f"{base}/releases/latest",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if release_response.ok:
                release = release_response.json()
                result["latest_release"] = {
                    "name": release.get("name") or release.get("tag_name") or "Release",
                    "tag": release.get("tag_name") or "",
                    "date": (release.get("published_at") or "")[:10],
                    "url": release.get("html_url", ""),
                }
        except (requests.RequestException, ValueError, TypeError):
            logger.debug("GitHub release bilgileri alınamadı.", exc_info=True)

        return result

    except (requests.RequestException, ValueError, TypeError, KeyError) as hata:
        logger.warning("GitHub gelişim verileri alınamadı: %s", hata)
        return None


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
    system_prompt=None,
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

Rapor eksiksiz bir KONTROL LİSTESİ izlemelidir. Her başlık için kanıt varsa bulguyu ve doğrudan URL'yi yaz; kanıt yoksa "Doğrulanamadı / kaynak bulunamadı" de. Bir alanın bulunmaması, o özelliğin kesinlikle olmadığı anlamına gelmez. İlgisiz veriyi doldurmak için tahmin üretme.

Zorunlu bölümler:
1. Yönetici özeti ve araştırma kapsamı (tarih, kaç kaynak incelendi, veri sınırlamaları)
2. Proje kimliği, resmî web sitesi ve doğrulanmış resmî bağlantılar
3. Amaç, hedef kullanıcılar ve çözdüğü sorun
4. Teknoloji, mimari, ağ/altyapı ve entegrasyonlar
5. Ürünler, kullanım örnekleri, demo ve ürünün mevcut durumu
6. Geliştirme etkinliği: depo eşleşmesi, lisans, son commit/sürüm ve bilinen sınırlamalar
7. Yol haritası, kilometre taşları ve gerçekleştiği doğrulanabilen teslimatlar
8. Açık kaynak durumu, lisans, şeffaflık ve yeniden üretilebilirlik
9. Ekip, kurucular, danışmanlar ve doğrulanabilir geçmiş (kanıt yoksa belirt)
10. Fonlama, yatırımcılar ve hibeler (yalnızca kaynaklıysa)
11. Token durumu: token var mı, ağ/kontrat, sembol, arz, dolaşım, dağılım, vesting/unlock, kullanım alanı; bulunmayan her alt alanı ayrı belirt
12. Borsa listelenmeleri ve piyasa verisi: tarih damgası ve kaynak; teyit yoksa listeleme iddiası kurma
13. Ekosistem, ortaklıklar, entegrasyonlar ve yönetişim; duyuru ile doğrulanmış entegrasyonu ayır
14. Güvenlik: denetimler, denetleyen kuruluş, kapsam/tarih, bug bounty ve bilinen olaylar; kaynak yoksa "denetim yok" diye kesin hüküm verme
15. Son gelişmeler: tarihli olaylar ve güncellik sınırı
16. Güçlü yönler ve bunları destekleyen kanıtlar
17. Riskler, çelişkili iddialar ve doğrulanamayan bilgiler
18. Kapsam tablosu: her ana kategori için "Doğrulandı / Kısmen doğrulandı / Bulunamadı / Çelişkili" durumu
19. Genel değerlendirme: yatırım tavsiyesi olmadan, kanıtın gücü ve sınırlamaları
20. Kaynakça: kaynak başlığı, URL ve hangi iddiayı desteklediği

Kaynak sayısı tek başına kanıt kalitesi değildir. Resmî kaynakları önceliklendir; üçüncü taraf iddialarını resmî bilgi gibi sunma. Güncel fiyatlar veya borsa durumları gibi değişken bilgilerde kaynak tarihi yoksa güncel olduğunu iddia etme.

Kayıtlı proje verisi:
{json.dumps(proje_verisi, ensure_ascii=False, indent=2)}

Araştırma kaynakları:
{source_text}
"""

    # Workspace görevleri proje araştırma kontrol listesine zorlanmamalı.
    # Bu yol, kullanıcının istediği işi doğrudan yanıtlar ve aynı tek API çağrısını kullanır.
    if system_prompt:
        prompt = f"""
Kullanıcının görevi:
{proje_adi}

Yanıt dili: {LANGUAGES[dil]}

Yanıt kuralları:
- Önce kullanıcının asıl isteğini yerine getir; konu dışı proje kontrol listesi üretme.
- Sağlanan kaynakları ve bağlamı kullan. Kaynak yoksa bunu açıkça söyle.
- Bilmediğin bilgileri, sonuçları, testleri veya işlemleri yapılmış gibi gösterme.
- Gerekliyse uygulanabilir adımları, kodu veya sonucu doğrudan ver.
- Belirsizlikleri ve sınırlamaları kısa ve açık biçimde belirt.
- Kullanıcı analiz istiyorsa somut bulguları, nedenleri ve çözüm önerilerini sırala.
- Yanıtı {LANGUAGES[dil]} dilinde ver.

Bağlam:
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
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt or (
                            "You are Prey Open AGI, a careful research assistant. "
                            "Follow the user's task, distinguish evidence from assumptions, "
                            "and never invent facts or sources."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4500,
                "reasoning_effort": "low",
                "temperature": 0.2,
            },
            timeout=(10, 150),
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise RuntimeError("Fortytwo API yanıtında completion mesajı bulunamadı.")
        message = choices[0]["message"]
        text = message.get("content")
        if isinstance(text, list):
            text = "\n".join(
                part.get("text", "") for part in text if isinstance(part, dict)
            )

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

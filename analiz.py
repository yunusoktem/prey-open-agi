
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

KLASOR = Path(__file__).parent
PROJE_DOSYASI = KLASOR / "projeler.json"
load_dotenv(KLASOR / ".env")

API_KEY = os.getenv("FORTYTWO_API_KEY")
API_URL = "https://api.fortytwo.network/v1/chat/completions"
MODEL = "qwen/qwen3.8-27b"


def ai_analizi(proje_verisi):
    if not API_KEY:
        raise RuntimeError(".env dosyasinda API anahtari bulunamadi.")

    prompt = f"""
Sen dikkatli bir Web3 proje analistisin.
Yalnizca asagidaki JSON verisini kullan.
Eksik bilgileri kendin uydurma; "Veri eksik" diye belirt.
Guncel internet verisine sahip oldugunu iddia etme.
Turkce, acik ve tarafsiz yaz.
Su basliklari kullan:
1. Projenin amaci
2. Teknoloji ve urun
3. Token ekonomisi
4. Guclu yonler
5. Riskler
6. Eksik ve dogrulanmasi gereken bilgiler

Her baslik altinda en fazla 3 kisa madde yaz.
Veri:
{json.dumps(proje_verisi, ensure_ascii=False)}
"""

    yanit = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1200,
            "temperature": 0.2
        },
        timeout=90
    )

    yanit.raise_for_status()
    sonuc = yanit.json()
    mesaj = sonuc["choices"][0]["message"]
    metin = mesaj.get("content")

    if not metin:
        raise RuntimeError(
            "Model bos metin dondurdu. Bitis nedeni: "
            + str(sonuc["choices"][0].get("finish_reason"))
        )

    return metin.strip()


def rapor_olustur(proje):
    with open(PROJE_DOSYASI, "r", encoding="utf-8") as dosya:
        projeler = json.load(dosya)

    anahtar = proje.strip().lower()

    if anahtar not in projeler:
        print(f"\n'{proje}' kayitli projeler arasinda bulunamadi.")
        print("Mevcut projeler:", ", ".join(projeler.keys()))
        return

    veri = projeler[anahtar]

    print("\nFortytwo AI analiz yapiyor...")
    try:
        rapor = ai_analizi(veri)
        durum = "Fortytwo AI tarafindan olusturuldu."
    except Exception as hata:
        print(f"\nAI analizi basarisiz: {hata}")
        print("Kayitli verilerden standart rapor olusturuluyor.")

        bolumler = [
            ("Projenin amaci", veri.get("amac", "Veri eksik")),
            ("Teknoloji ve urun", veri.get("teknoloji", "Veri eksik")),
            ("Urun durumu", veri.get("urun_durumu", "Veri eksik")),
            ("Token ekonomisi", json.dumps(
                veri.get("token", {}), ensure_ascii=False, indent=2
            )),
            ("Guclu yonler", "\n".join(
                "- " + x for x in veri.get("guclu_yonler", [])
            )),
            ("Riskler", "\n".join(
                "- " + x for x in veri.get("riskler", [])
            )),
            ("Eksik bilgiler", "\n".join(
                "- " + x for x in veri.get("bilinmeyenler", [])
            ))
        ]
        rapor = "\n\n".join(
            baslik + "\n" + icerik for baslik, icerik in bolumler
        )
        durum = "Standart rapor; AI kullanilamadi."

    tam_rapor = (
        f"WEB3 PROJE ANALIZI: {veri.get('ad', proje)}\n"
        f"Durum: {durum}\n"
        "Not: Analiz yalnizca kayitli veriye dayanir; "
        "guncel bilgiler ayrica dogrulanmalidir.\n\n"
        + rapor
    )

    print("\n" + "=" * 50)
    print(tam_rapor)
    print("=" * 50)

    cikti = KLASOR / f"{anahtar}_raporu.txt"
    cikti.write_text(tam_rapor, encoding="utf-8")
    print(f"\nRapor kaydedildi: {cikti.name}")


if __name__ == "__main__":
    proje = input("Analiz etmek istedigin proje adini yaz: ")
    rapor_olustur(proje)

"""
Tələbələrin nəticələrinin süni intellektlə təhlili.

İstifadə:
    python3 telebe_analizi.py               # daxili nümunə məlumatlarla
    python3 telebe_analizi.py telebeler.csv # öz CSV faylınızla

CSV formatı (birinci sətir başlıqdır):
    Tələbə,Riyaziyyat,İnformatika,Fizika,İngilis dili
    Aysel,85,92,78,88
    ...
"""

import csv
import statistics
import sys

# --- Qiymətləndirmə meyarları (100 ballıq sistem) ---
ELA_HEDDI = 91        # bu baldan yuxarı və ya bərabər -> "əla" (A)
YAXSI_HEDDI = 71      # bu baldan yuxarı və ya bərabər -> "yaxşı" (C)
YUKSEK_ORTA = 85      # 5-ci tapşırıq: orta balı 85-dən yuxarı olanlar

NUMUNE_FENNLER = ["Riyaziyyat", "İnformatika", "Fizika", "İngilis dili"]
NUMUNE_TELEBELER = {
    "Aysel":  [85, 92, 78, 88],
    "Murad":  [72, 95, 81, 70],
    "Nigar":  [94, 87, 91, 93],
    "Elvin":  [65, 73, 69, 76],
    "Kamran": [88, 68, 84, 79],
    "Leyla":  [76, 90, 72, 85],
}


def csv_oxu(yol):
    with open(yol, encoding="utf-8-sig") as f:
        setirler = [s for s in csv.reader(f) if s]
    fennler = [x.strip() for x in setirler[0][1:]]
    telebeler = {s[0].strip(): [float(x) for x in s[1:]] for s in setirler[1:]}
    return fennler, telebeler


def b(x):
    """Balı səliqəli göstər."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def basliq(metn):
    print("\n" + "=" * 70)
    print(metn)
    print("=" * 70)


class TelebeAnalizSI:
    def __init__(self, fennler, telebeler):
        self.fennler = fennler
        self.telebeler = telebeler
        self.ortalar = {ad: statistics.mean(ballar) for ad, ballar in telebeler.items()}
        self.fenn_ortalari = {
            f: statistics.mean(ballar[i] for ballar in telebeler.values())
            for i, f in enumerate(fennler)
        }
        self.qrup_ortasi = statistics.mean(self.ortalar.values())

    # 1
    def orta_ballar(self):
        basliq("1. Hər tələbənin orta balı")
        for ad, orta in self.ortalar.items():
            print(f"  {ad:<10} {b(orta):>6}")

    # 2
    def siralama(self):
        basliq("2. Orta bala görə sıralama (yüksəkdən aşağıya)")
        sirali = sorted(self.ortalar.items(), key=lambda x: x[1], reverse=True)
        for yer, (ad, orta) in enumerate(sirali, 1):
            print(f"  {yer}. {ad:<10} {b(orta):>6}")
        return sirali

    # 3
    def fenn_ortalari_goster(self):
        basliq("3. Hər fənn üzrə qrupun orta nəticəsi")
        for f, orta in self.fenn_ortalari.items():
            print(f"  {f:<14} {b(orta):>6}")
        print(f"  {'Qrup üzrə':<14} {b(self.qrup_ortasi):>6}")

    # 4
    def guclu_zeif(self):
        basliq("4. Hər fənn üzrə ən güclü və ən zəif tələbə")
        for i, f in enumerate(self.fennler):
            ballar = {ad: bl[i] for ad, bl in self.telebeler.items()}
            maks, mins = max(ballar.values()), min(ballar.values())
            gucluler = ", ".join(a for a, x in ballar.items() if x == maks)
            zeifler = ", ".join(a for a, x in ballar.items() if x == mins)
            print(f"  {f:<14} ən güclü: {gucluler} ({b(maks)}) | ən zəif: {zeifler} ({b(mins)})")

    # 5
    def yuksek_orta(self):
        basliq(f"5. Orta balı {YUKSEK_ORTA}-dən yuxarı olan tələbələr")
        siyahi = [(a, o) for a, o in self.ortalar.items() if o > YUKSEK_ORTA]
        if not siyahi:
            print("  Belə tələbə yoxdur.")
        for a, o in siyahi:
            print(f"  {a} ({b(o)})")
        return siyahi

    def kateqoriya(self, ad):
        ballar = self.telebeler[ad]
        if all(x >= ELA_HEDDI for x in ballar):
            return "əlaçı"
        if any(x >= ELA_HEDDI for x in ballar) and all(x >= YAXSI_HEDDI for x in ballar):
            return "zərbəçi"
        return "adi"

    # 6, 7
    def elaci_zerbeci(self):
        elacilar = [a for a in self.telebeler if self.kateqoriya(a) == "əlaçı"]
        zerbeciler = [a for a in self.telebeler if self.kateqoriya(a) == "zərbəçi"]
        basliq(f"6. Əlaçı tələbələr (bütün fənlərdən ≥ {ELA_HEDDI})")
        print("  " + (", ".join(elacilar) if elacilar else "Əlaçı tələbə yoxdur."))
        basliq(f"7. Zərbəçi tələbələr (ən azı bir fəndən ≥ {ELA_HEDDI}, qalanlardan ≥ {YAXSI_HEDDI})")
        print("  " + (", ".join(zerbeciler) if zerbeciler else "Zərbəçi tələbə yoxdur."))
        return elacilar, zerbeciler

    # 8
    def cetin_fenn(self):
        basliq("8. Qrup üçün ən çətin fənn")
        for i, f in enumerate(self.fennler):
            ballar = [bl[i] for bl in self.telebeler.values()]
            asagi = sum(1 for x in ballar if x < YAXSI_HEDDI)
            print(f"  {f:<14} orta: {b(self.fenn_ortalari[f]):>6} | "
                  f"yayınma: {b(statistics.pstdev(ballar)):>5} | {YAXSI_HEDDI}-dən aşağı: {asagi} nəfər")
        cetin = min(self.fenn_ortalari, key=self.fenn_ortalari.get)
        print(f"\n  Qərar: ən çətin fənn — {cetin} (ən aşağı qrup ortası: "
              f"{b(self.fenn_ortalari[cetin])}).")
        return cetin

    # 9
    def tovsiyeler(self):
        basliq("9. Fərdi təhsil tövsiyələri")
        for ad, ballar in self.telebeler.items():
            orta = self.ortalar[ad]
            zeif_i = min(range(len(ballar)), key=lambda i: ballar[i])
            guclu_i = max(range(len(ballar)), key=lambda i: ballar[i])
            zeif, guclu = self.fennler[zeif_i], self.fennler[guclu_i]
            ferq = ballar[guclu_i] - ballar[zeif_i]
            asagi_fennler = [self.fennler[i] for i, x in enumerate(ballar)
                             if x < self.fenn_ortalari[self.fennler[i]]]

            print(f"\n  ▶ {ad} (orta: {b(orta)}, status: {self.kateqoriya(ad)})")
            if orta >= 90:
                print("    - Çox yüksək nəticə. Olimpiada, layihə və tədqiqat işlərinə cəlb olunması tövsiyə olunur.")
            elif orta >= 80:
                print("    - Yaxşı nəticə. Sabitliyi qoruyub zəif fənni gücləndirməklə əlaçı ola bilər.")
            elif orta >= 70:
                print("    - Orta nəticə. Həftəlik plan qurmalı və müntəzəm təkrar etməlidir.")
            else:
                print("    - Nəticə qrupdan aşağıdır. Müəllimlə fərdi məşğələ və əlavə dəstək lazımdır.")
            if ballar[guclu_i] > self.fenn_ortalari[guclu]:
                print(f"    - Güclü tərəfi: {guclu} ({b(ballar[guclu_i])}). Bu fənndə qrup yoldaşlarına kömək edə bilər.")
            else:
                print(f"    - Nisbətən ən yaxşı fənni: {guclu} ({b(ballar[guclu_i])}), amma qrup ortasından aşağıdır.")
            if ballar[zeif_i] < YAXSI_HEDDI:
                print(f"    - Təcili diqqət: {zeif} ({b(ballar[zeif_i])}) — {YAXSI_HEDDI}-dən aşağıdır, əlavə dərs tövsiyə olunur.")
            else:
                print(f"    - İnkişaf sahəsi: {zeif} ({b(ballar[zeif_i])}).")
            if ferq >= 20:
                print(f"    - Fənlər arası fərq böyükdür ({b(ferq)} bal). Vaxtı fənlər arasında daha bərabər bölməlidir.")
            if asagi_fennler:
                print(f"    - Qrup ortasından aşağı olduğu fənlər: {', '.join(asagi_fennler)}.")

    # 10
    def umumi_netice(self, sirali, elacilar, zerbeciler, cetin):
        basliq("10. Ümumi nəticə")
        n = len(self.telebeler)
        en_asan = max(self.fenn_ortalari, key=self.fenn_ortalari.get)
        risk = [a for a, bl in self.telebeler.items() if any(x < YAXSI_HEDDI for x in bl)]
        print(f"  • Qrupda {n} tələbə var, qrupun ümumi orta balı {b(self.qrup_ortasi)}-dir.")
        print(f"  • Ən yüksək nəticə: {sirali[0][0]} ({b(sirali[0][1])}); "
              f"ən aşağı nəticə: {sirali[-1][0]} ({b(sirali[-1][1])}).")
        print(f"  • Əlaçı: {len(elacilar)} nəfər, zərbəçi: {len(zerbeciler)} nəfər, "
              f"digər: {n - len(elacilar) - len(zerbeciler)} nəfər.")
        print(f"  • Qrup ən yaxşı {en_asan} fənnində ({b(self.fenn_ortalari[en_asan])}), "
              f"ən zəif {cetin} fənnində ({b(self.fenn_ortalari[cetin])}) çıxış edib.")
        if risk:
            print(f"  • {YAXSI_HEDDI}-dən aşağı balı olan tələbələr: {', '.join(risk)} — onlara əlavə dəstək lazımdır.")
        if self.qrup_ortasi >= 85:
            qiymet = "çox yüksəkdir"
        elif self.qrup_ortasi >= 75:
            qiymet = "yaxşıdır, amma inkişaf potensialı var"
        else:
            qiymet = "kifayət deyil, ciddi dəstək tələb olunur"
        print(f"  • Qərar: qrupun ümumi səviyyəsi {qiymet}. {cetin} fənni üzrə əlavə "
              f"məşğələlər və güclü tələbələrin zəif tələbələrə kömək etdiyi cüt iş tövsiyə olunur.")

    def tam_analiz(self):
        self.orta_ballar()
        sirali = self.siralama()
        self.fenn_ortalari_goster()
        self.guclu_zeif()
        self.yuksek_orta()
        elacilar, zerbeciler = self.elaci_zerbeci()
        cetin = self.cetin_fenn()
        self.tovsiyeler()
        self.umumi_netice(sirali, elacilar, zerbeciler, cetin)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fennler, telebeler = csv_oxu(sys.argv[1])
    else:
        fennler, telebeler = NUMUNE_FENNLER, NUMUNE_TELEBELER
    TelebeAnalizSI(fennler, telebeler).tam_analiz()

"""
Ağıllı şəhərdə yol hərəkətinin optimallaşdırılması — süni intellekt analizi.

İstifadə:
    python3 yol_herekati.py
"""

# Son 1 saatın məlumatları: avtomobil, orta gözləmə (san.), qəza, piyada
KESISMELER = {
    "A": {"avto": 420, "gozleme": 75, "qeza": 2, "piyada": 180},
    "B": {"avto": 280, "gozleme": 42, "qeza": 0, "piyada": 320},
    "C": {"avto": 610, "gozleme": 110, "qeza": 3, "piyada": 150},
    "D": {"avto": 350, "gozleme": 58, "qeza": 1, "piyada": 420},
    "E": {"avto": 190, "gozleme": 35, "qeza": 0, "piyada": 90},
}

# Risk düsturunun əmsalları
EMSAL = {"avto": 0.3, "gozleme": 0.4, "qeza": 20, "piyada": 0.1}

# Risk səviyyəsinin hədləri
ORTA_HEDD = 150      # risk < 150         -> aşağı
YUKSEK_HEDD = 250    # 150 <= risk < 250  -> orta, risk >= 250 -> yüksək


def b(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def basliq(metn):
    print("\n" + "=" * 70)
    print(metn)
    print("=" * 70)


def risk_bali(d):
    return sum(d[k] * EMSAL[k] for k in EMSAL)


def seviyye(risk):
    if risk >= YUKSEK_HEDD:
        return "yüksək"
    if risk >= ORTA_HEDD:
        return "orta"
    return "aşağı"


class YolHerekatiSI:
    def __init__(self, kesismeler):
        self.k = kesismeler
        self.risk = {ad: risk_bali(d) for ad, d in kesismeler.items()}

    # 1
    def risk_hesabla(self):
        basliq("1. Risk balı = Avto×0.3 + Gözləmə×0.4 + Qəza×20 + Piyada×0.1")
        for ad, d in self.k.items():
            hisseler = " + ".join(b(d[x] * EMSAL[x]) for x in EMSAL)
            print(f"  {ad}: {hisseler} = {b(self.risk[ad])}")

    # 2
    def qruplar(self):
        basliq(f"2. Risk qrupları (aşağı < {ORTA_HEDD} ≤ orta < {YUKSEK_HEDD} ≤ yüksək)")
        for s in ("yüksək", "orta", "aşağı"):
            uzvler = [f"{a} ({b(r)})" for a, r in sorted(self.risk.items(), key=lambda x: -x[1])
                      if seviyye(r) == s]
            print(f"  {s.capitalize():<7}: {', '.join(uzvler) if uzvler else '—'}")

    # 3
    def en_tehlukeli(self):
        basliq("3. Ən təhlükəli kəsişmə")
        ad = max(self.risk, key=self.risk.get)
        d = self.k[ad]
        print(f"  {ad} kəsişməsi — risk balı {b(self.risk[ad])} ({seviyye(self.risk[ad])} səviyyə).")
        print("  Riskin tərkibi:")
        for x, ad_az in (("avto", "avtomobil"), ("gozleme", "gözləmə"),
                         ("qeza", "qəza"), ("piyada", "piyada")):
            pay = d[x] * EMSAL[x]
            print(f"    - {ad_az:<10} {b(pay):>6}  ({b(pay / self.risk[ad] * 100)}%)")
        return ad

    # 4
    def yasil_isiq(self):
        basliq("4. Yaşıl işıq müddətinin artırılması harada daha məqsədəuyğundur?")
        print("  Gecikmə = avtomobil × gözləmə / 3600 (saatda itirilən avtomobil-saat)")
        print("  Avto/piyada nisbəti yüksək olduqca avtomobillərə yaşıl işığı artırmaq piyadalara az zərər verir.\n")
        bal = {}
        for ad, d in self.k.items():
            gecikme = d["avto"] * d["gozleme"] / 3600
            nisbet = d["avto"] / d["piyada"]
            bal[ad] = gecikme * nisbet
            print(f"  {ad}: gecikmə {b(gecikme):>6} avto-saat | avto/piyada {b(nisbet):>5} | "
                  f"uyğunluq balı {b(bal[ad]):>6}")
        secim = max(bal, key=bal.get)
        d = self.k[secim]
        print(f"\n  Qərar: {secim} kəsişməsi. Burada ən çox avtomobil ({d['avto']}) və ən uzun gözləmə "
              f"({d['gozleme']} san.) var,\n  piyada sayı isə nisbətən azdır ({d['piyada']}), "
              f"ona görə yaşıl müddətin artırılması ən çox fayda verər.")
        return secim

    # 5, 6, 7
    def ssenariler(self, ad="C"):
        d = self.k[ad]
        esas = self.risk[ad]

        basliq(f"5. Ssenari 1: {ad} kəsişməsində avtomobil sayı 20% artır")
        yeni_avto = d["avto"] * 1.2
        r1 = risk_bali({**d, "avto": yeni_avto})
        print(f"  Avtomobil: {d['avto']} → {b(yeni_avto)}")
        print(f"  Risk: {b(esas)} → {b(r1)}  (dəyişmə: +{b(r1 - esas)}, +{b((r1 - esas) / esas * 100)}%)")
        print(f"  Yeni səviyyə: {seviyye(r1)}")

        basliq(f"6. Ssenari 2: {ad} kəsişməsində gözləmə müddəti 30% azalır")
        yeni_gozleme = d["gozleme"] * 0.7
        r2 = risk_bali({**d, "gozleme": yeni_gozleme})
        print(f"  Gözləmə: {d['gozleme']} → {b(yeni_gozleme)} san.")
        print(f"  Risk: {b(esas)} → {b(r2)}  (dəyişmə: {b(r2 - esas)}, {b((r2 - esas) / esas * 100)}%)")
        print(f"  Yeni səviyyə: {seviyye(r2)}")

        basliq("7. Ssenarilərin müqayisəsi")
        t1, t2 = r1 - esas, esas - r2
        birge = risk_bali({**d, "avto": yeni_avto, "gozleme": yeni_gozleme})
        lazim_gozleme = t1 / EMSAL["gozleme"]
        print(f"  • Avtomobil artımı riski {b(t1)} bal artırır, gözləmənin azalması isə {b(t2)} bal azaldır.")
        print(f"  • Təsir gücünə görə avtomobil sayının dəyişməsi {b(t1 / t2)} dəfə güclüdür.")
        print(f"  • Hər ikisi birlikdə baş versə, risk {b(birge)} olar — yəni gözləmənin 30% azalması")
        print(f"    avtomobil artımını kompensasiya etmir (bunun üçün gözləmə {b(lazim_gozleme)} san. azalmalıdır,")
        print(f"    halbuki cəmi {d['gozleme']} san.-dir).")
        print(f"  • 1 qəzanın qarşısını almaq riski 20 bal azaldır — bu, gözləmənin 30% azalmasından "
              f"({b(t2)}) daha effektivdir.")
        print("  Nəticə: riskə ən güclü təsir edən amil avtomobil axınıdır. Ona görə tək işıqfor")
        print("  optimallaşdırması kifayət deyil — axının bir hissəsini başqa yollara yönəltmək və")
        print("  qəzaları azaltmaq daha effektiv strategiyadır. İdarə edilə bilən tədbir kimi isə")
        print("  gözləmənin azaldılması riski real olaraq aşağı salan yeganə ssenaridir.")
        return r1, r2

    # 8
    def tovsiyeler(self, tehlukeli):
        basliq("8. Şəhər rəhbərliyinə 3 konkret tövsiyə")
        piyada_cox = max(self.k, key=lambda a: self.k[a]["piyada"])
        qeza_sirali = sorted((a for a in self.k if a != tehlukeli and self.k[a]["qeza"] > 0),
                             key=lambda a: -self.k[a]["qeza"])
        asagi = [a for a in self.k if seviyye(self.risk[a]) == "aşağı"]
        d = self.k[tehlukeli]
        print(f"  1) {tehlukeli} kəsişməsində süni intellektlə idarə olunan adaptiv işıqfor quraşdırılsın:")
        print(f"     yaşıl müddət real axına görə uzadılsın, gözləmə {d['gozleme']} san.-dən ən azı "
              f"{b(d['gozleme'] * 0.7)} san.-yə endirilsin, qırmızı işıq və sürət kameraları qoyulsun "
              f"({d['qeza']} qəza qeydə alınıb).")
        print(f"  2) {piyada_cox} kəsişməsində ({self.k[piyada_cox]['piyada']} piyada) ayrıca piyada fazası "
              f"və ya yeraltı/yerüstü keçid yaradılsın, piyada və avtomobil axınları ayrılsın.")
        if qeza_sirali:
            q = qeza_sirali[0]
            print(f"  3) {q} kəsişməsində ({self.k[q]['qeza']} qəza) yol nişanları və sürət məhdudiyyəti "
                  f"gücləndirilsin; naviqasiya sistemləri vasitəsilə {tehlukeli} və {q}-dan axının bir hissəsi "
                  f"az yüklü {', '.join(asagi)} kəsişmələrinə yönəldilsin.")
        else:
            print(f"  3) Naviqasiya vasitəsilə {tehlukeli}-dən axının bir hissəsi az yüklü "
                  f"{', '.join(asagi)} kəsişmələrinə yönəldilsin.")

    # 9
    def qerar(self, tehlukeli, r1, r2):
        basliq("9. Yekun qərar və əsaslandırma")
        d = self.k[tehlukeli]
        print(f"  Qərar: prioritet {tehlukeli} kəsişməsidir. Səbəblər:")
        print(f"   • Risk balı ən yüksəkdir ({b(self.risk[tehlukeli])}), ikinci yerdən "
              f"{b(self.risk[tehlukeli] - sorted(self.risk.values())[-2])} bal çoxdur.")
        print(f"   • Ən çox avtomobil ({d['avto']}), ən uzun gözləmə ({d['gozleme']} san.) və "
              f"ən çox qəza ({d['qeza']}) buradadır.")
        print(f"   • Avtomobil sayı 20% artsa risk {b(r1)}-ə qalxacaq; gözləmənin 30% azaldılması isə "
              f"riski {b(r2)}-ə endirir.")
        print("   • Ssenarilər göstərir ki, ən yaxşı nəticə üç tədbirin birgə tətbiqi ilə əldə olunur:")
        print("     adaptiv işıqfor (gözləməni azaldır) + axının yönləndirilməsi (avtomobil sayını azaldır)")
        print("     + kameralar (qəzaları azaldır, hər qəza = 20 risk balı).")
        asagi = [a for a in self.k if seviyye(self.risk[a]) == "aşağı"]
        print(f"   • {', '.join(asagi)} kəsişmələri aşağı risklidir və əlavə axını qəbul edə bilər.")

    def tam_analiz(self):
        self.risk_hesabla()
        self.qruplar()
        tehlukeli = self.en_tehlukeli()
        self.yasil_isiq()
        r1, r2 = self.ssenariler("C")
        self.tovsiyeler(tehlukeli)
        self.qerar(tehlukeli, r1, r2)


if __name__ == "__main__":
    YolHerekatiSI(KESISMELER).tam_analiz()

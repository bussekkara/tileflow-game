"""
TILEFLOW - modern kayar bulmaca oyunu.
"""

import pygame
import sys
import random
import math
import time
import os
import json

#  SABITLER
EKRAN_EN   = 900
EKRAN_BOY  = 700
FPS        = 60
BASLIK     = "TILEFLOW"

# Oyun ızgara bölgesi (ekranın ortası)
IZGARA_OFFSET_X = 0
IZGARA_OFFSET_Y = 0

# İpucu sayısı
MAX_IPUCU = 8

# Animasyon hızı (piksel/kare)
ANIM_HIZ = 18

# Zorluk seviyeleri
SEVIYELER = {
    "Kolay":  {"boyut": 3, "renk": (80, 200, 100), "karisma": 12},
    "Orta":   {"boyut": 4, "renk": (230, 160,  40), "karisma": 55},
    "Zor":    {"boyut": 5, "renk": (220,  60,  60), "karisma": 130},
}

# Temalar (arka plan, kare renkleri listesi, metin, kenarlık)
TEMALAR = {
    "Okyanus": {
        "arkaplan":   (10,  25,  60),
        "panel":      (15,  40,  90),
        "bos_kare":   (8,   18,  45),
        "kare_renk":  [(30, 100, 200), (20, 140, 210), (40,  80, 180),
                       (25, 120, 190), (50,  90, 220), (15, 160, 200),
                       (35, 110, 170), (60, 130, 210), (20,  70, 190),
                       (45, 150, 220), (30,  60, 160), (55, 100, 200)],
        "metin":      (220, 240, 255),
        "kenarlık":   (100, 180, 255),
        "vurgu":      (0,  200, 255),
    },
    "Orman": {
        "arkaplan":   (10,  35,  15),
        "panel":      (15,  55,  20),
        "bos_kare":   (8,   28,  10),
        "kare_renk":  [(40, 160,  60), (30, 130,  80), (60, 180,  40),
                       (50, 150,  70), (35, 110,  90), (70, 190,  50),
                       (45, 140,  65), (55, 170,  45), (25, 120,  75),
                       (65, 200,  55), (38, 125,  85), (48, 155,  60)],
        "metin":      (210, 255, 215),
        "kenarlık":   (100, 230, 120),
        "vurgu":      (80,  255, 100),
    },
    "Gece": {
        "arkaplan":   (15,  10,  35),
        "panel":      (25,  18,  55),
        "bos_kare":   (10,   7,  28),
        "kare_renk":  [(120,  60, 200), (100,  80, 220), (150,  40, 180),
                       (130,  70, 210), (110,  90, 190), (160,  50, 230),
                       (140,  65, 205), (115,  85, 215), (105,  55, 175),
                       (155,  75, 225), (125,  45, 185), (145,  95, 195)],
        "metin":      (230, 210, 255),
        "kenarlık":   (180, 130, 255),
        "vurgu":      (200, 100, 255),
    },
    "Alev": {
        "arkaplan":   (40,  10,   5),
        "panel":      (60,  18,   8),
        "bos_kare":   (30,   8,   3),
        "kare_renk":  [(220,  80,  30), (200, 120,  20), (240,  50,  40),
                       (210,  90,  25), (230,  60,  50), (195, 140,  15),
                       (215, 100,  35), (225,  70,  45), (205,  85,  20),
                       (235, 110,  30), (198,  55,  42), (245,  75,  28)],
        "metin":      (255, 230, 210),
        "kenarlık":   (255, 160,  60),
        "vurgu":      (255, 120,  30),
    },
}

TEMA_SIRASI = list(TEMALAR.keys())   # tema geçişi için sıra
ZITLAR = {"yukari": "asagi", "asagi": "yukari", "sol": "sag", "sag": "sol"}


#  YARDIMCI FONKSİYONLAR
def ilerlem_bari_ciz(ekran, x, y, en, boy, oran, renk, arkaplan=(40, 40, 50)):
    """
    Yatay ilerleme barı çizer.
    Kitap Bölüm 34.2 – Sağlık Barı mantığıyla aynı yapı,
    burada tamamlanma yüzdesi için kullanıldı.

    Parametreler:
      ekran     – pygame.Surface
      x, y      – sol üst köşe
      en, boy   – boyutlar
      oran      – 0.0 ile 1.0 arası doluluk oranı
      renk      – dolu kısmın rengi
      arkaplan  – boş kısmın rengi
    """
    # Arka plan (boş kısım)
    pygame.draw.rect(ekran, arkaplan, (x, y, en, boy), border_radius=6)
    # Dolu kısım
    dolu = int(en * oran)
    if dolu > 0:
        pygame.draw.rect(ekran, renk, (x, y, dolu, boy), border_radius=6)
    # Kenarlık
    pygame.draw.rect(ekran, (180, 180, 180), (x, y, en, boy), 2, border_radius=6)


def renk_karistir(r1, r2, t):
    """İki renk arasında t (0.0–1.0) oranında lineer interpolasyon."""
    return tuple(int(r1[i] + (r2[i] - r1[i]) * t) for i in range(3))


def saniyeleri_formatla(saniye):
    """120 → '02:00' biçiminde string döndürür."""
    d = int(saniye)
    return f"{d // 60:02d}:{d % 60:02d}"


def skor_dosya_yolu():
    """En iyi skorların saklanacağı JSON dosyasının yolunu döndürür."""
    return os.path.join(os.path.dirname(__file__), "best_scores.json")


def skor_etiketi(deger):
    """Skor yoksa '-' gösterir, varsa hamle sayısını döndürür."""
    return "-" if deger is None else str(deger)

#  BUTON SINIFI

class Buton:
    """
    Hover efektli, callback destekli buton sınıfı.
    Kitap Bölüm 35.1–35.3 yapısına uygun olarak yazılmıştır.

    Parametreler:
      x, y          – merkez konumu
      en, boy       – boyutlar
      metin         – buton yazısı
      renk          – normal arka plan rengi
      hover_renk    – fareyle üzerine gelince renk
      callback      – tıklandığında çağrılacak fonksiyon
      font_boyut    – yazı tipi büyüklüğü
      border_r      – köşe yuvarlama miktarı
    """

    def __init__(self, x, y, en, boy, metin,
                 renk=(60, 90, 160), hover_renk=(90, 130, 210),
                 callback=None, font_boyut=26, border_r=10):
        # Rect merkezi x,y noktasına hizalanır
        self.rect       = pygame.Rect(0, 0, en, boy)
        self.rect.center = (x, y)
        self.metin      = metin
        self.renk       = renk
        self.hover_renk = hover_renk
        self.callback   = callback
        self.font       = pygame.font.SysFont("segoeui", font_boyut, bold=True)
        self.border_r   = border_r
        self.uzerinde   = False     # hover durumu
        self.aktif      = True      # devre dışı bırakılabilir

    def guncelle(self):
        """
        Her karede fare konumunu kontrol eder, hover durumunu günceller.
        Kitap Bölüm 35.2.1 – Fare Konum Kontrolü.
        """
        if not self.aktif:
            return
        fare = pygame.mouse.get_pos()
        self.uzerinde = self.rect.collidepoint(fare)

    def olay_isle(self, olay):
        """
        Fare tıklama olayını işler; tıklandıysa callback'i çağırır.
        Click ve Callback Mekanizması.
        """
        if not self.aktif:
            return
        if olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
            if self.rect.collidepoint(olay.pos):
                if self.callback:
                    self.callback()

    def ciz(self, ekran):
        """
        Butonu ekrana çizer.
        Hover durumuna göre renk ve kenarlık değişir.
        Gelişmiş Hover Efektleri.
        """
        if not self.aktif:
            # Devre dışı görünümü
            pygame.draw.rect(ekran, (50, 50, 55), self.rect, border_radius=self.border_r)
            pygame.draw.rect(ekran, (80, 80, 90), self.rect, 2, border_radius=self.border_r)
            yazi = self.font.render(self.metin, True, (100, 100, 110))
            ekran.blit(yazi, yazi.get_rect(center=self.rect.center))
            return

        aktif_renk = self.hover_renk if self.uzerinde else self.renk

        # Gölge efekti
        golge = pygame.Rect(self.rect.x + 3, self.rect.y + 4,
                             self.rect.width, self.rect.height)
        pygame.draw.rect(ekran, (10, 10, 15), golge, border_radius=self.border_r)

        # Gövde
        pygame.draw.rect(ekran, aktif_renk, self.rect, border_radius=self.border_r)

        # Kenarlık
        kenarlık_rengi = (220, 220, 100) if self.uzerinde else (180, 180, 180)
        kenarlık_kalinligi = 3 if self.uzerinde else 1
        pygame.draw.rect(ekran, kenarlık_rengi, self.rect,
                         kenarlık_kalinligi, border_radius=self.border_r)

        # Yazı
        metin_rengi = (255, 255, 200) if self.uzerinde else (240, 240, 240)
        yazi = self.font.render(self.metin, True, metin_rengi)
        ekran.blit(yazi, yazi.get_rect(center=self.rect.center))

#  BULMACA MANTIK SINIFI

class Bulmaca:
    """
    NxN Sliding Puzzle mantığını yöneten sınıf.
    Boş hücre 0 ile temsil edilir.

    Yöntemler:
      karistir()        – çözülebilir bir karışık durum oluşturur
      hamle_yap(yon)    – boş hücreyi belirtilen yönde kaydırır
      cozuldu_mu()      – bulmaca tamamlandı mı?
      tamamlanma_orani()– 0.0 – 1.0 arası yüzde
      ipucu_ver()       – bir sonraki hamlede ne yapılması gerektiğini döndürür
      coz()             – BFS ile çözüm yolu bulur (ipucu için)
    """

    def __init__(self, boyut):
        self.boyut   = boyut
        self.hedef   = list(range(1, boyut * boyut)) + [0]
        self.izgara  = self.hedef[:]
        self.bos_pos = boyut * boyut - 1   # boş hücrenin indeksi
        self.cozum_yolu = []

    #Sıfırlama & Karıştırma

    def sifirla(self):
        """Bulmacayı çözülmüş hale getirir."""
        self.izgara  = self.hedef[:]
        self.bos_pos = self.boyut * self.boyut - 1
        self.cozum_yolu = []

    def karistir(self, hamle_sayisi=100):
        """
        Rastgele geçerli hamleler yaparak bulmacayı karıştırır.
        Geri gitmemeye dikkat ederek (son hamlenin tersini almamak)
        daha az 'toplu' bir karışıklık sağlar.
        """
        self.izgara  = self.hedef[:]
        self.bos_pos = self.boyut * self.boyut - 1
        onceki_yon   = None

        self.cozum_yolu = []

        for _ in range(hamle_sayisi):
            secenekler = [y for y in ["yukari", "asagi", "sol", "sag"]
                          if y != onceki_yon and self._gecerli_mi(y)]
            if not secenekler:
                secenekler = [y for y in ["yukari", "asagi", "sol", "sag"]
                              if self._gecerli_mi(y)]
            if secenekler:
                yon          = random.choice(secenekler)
                self._hamle(yon)
                self.cozum_yolu.insert(0, ZITLAR[yon])
                onceki_yon   = ZITLAR.get(yon)

    # Hareket

    def _bos_satir_sutun(self):
        """Boş hücrenin satır ve sütununu döndürür."""
        return divmod(self.bos_pos, self.boyut)

    def _gecerli_mi(self, yon):
        """Belirtilen yönde hamle yapılabilir mi?"""
        satir, sutun = self._bos_satir_sutun()
        if yon == "yukari"  and satir > 0:              return True
        if yon == "asagi"   and satir < self.boyut - 1: return True
        if yon == "sol"     and sutun > 0:              return True
        if yon == "sag"     and sutun < self.boyut - 1: return True
        return False

    def _hamle(self, yon):
        """Boş hücreyi belirtilen yönde kaydırır (iç kullanım)."""
        satir, sutun = self._bos_satir_sutun()
        d = {"yukari": (-1, 0), "asagi": (1, 0),
             "sol": (0, -1),    "sag":   (0, 1)}
        ds, dc   = d[yon]
        yeni_pos = (satir + ds) * self.boyut + (sutun + dc)
        self.izgara[self.bos_pos], self.izgara[yeni_pos] = \
            self.izgara[yeni_pos], self.izgara[self.bos_pos]
        self.bos_pos = yeni_pos

    def hamle_yap(self, yon):
        """
        Dışarıdan çağrılan hamle fonksiyonu.
        Geçerliyse yapar ve True döner, değilse False döner.
        """
        if self._gecerli_mi(yon):
            self._hamle(yon)
            return True
        return False

    #Durum Sorgulama

    def cozuldu_mu(self):
        """Bulmaca tamamlandı mı?"""
        return self.izgara == self.hedef

    def tamamlanma_orani(self):
        """
        Doğru konumdaki kare sayısının toplam kareye oranını verir.
        (Boş kare hariç)
        Örnek: 8/9 doğruysa 0.888... döner
        """
        dogru = sum(1 for i, v in enumerate(self.izgara)
                    if v == self.hedef[i] and v != 0)
        return dogru / (self.boyut * self.boyut - 1)

    def kare_dogru_mu(self, indeks):
        """Belirli bir indeksteki kare doğru konumda mı?"""
        return self.izgara[indeks] == self.hedef[indeks] and self.izgara[indeks] != 0

    #BFS çözücü

    def ipucu_ver(self):
        """
        BFS (genişlik öncelikli arama) ile çözüm yolu bulur.
        İlk hamleyi yön olarak döndürür.
        Sadece küçük bulmacalarda pratik; 5×5'te sınırlı derinlikte çalışır.
        """
        hedef_tuple = tuple(self.hedef)
        baslangic   = tuple(self.izgara)

        if baslangic == hedef_tuple:
            return None

        # BFS kuyruğu: (durum, bos_pos, hamle_listesi)
        from collections import deque
        kuyruk    = deque([(baslangic, self.bos_pos, [])])
        ziyaret   = {baslangic}
        YONLER    = ["yukari", "asagi", "sol", "sag"]
        D         = {"yukari": (-1, 0), "asagi": (1, 0),
                     "sol": (0, -1),    "sag":   (0, 1)}
        MAX_DERINLIK = 30   # 5×5 için aşırı uzun çözümlerden kaçın

        while kuyruk:
            durum, bos, hamleler = kuyruk.popleft()
            if len(hamleler) > MAX_DERINLIK:
                continue
            satir, sutun = divmod(bos, self.boyut)
            for yon in YONLER:
                ds, dc = D[yon]
                ys, yc = satir + ds, sutun + dc
                if 0 <= ys < self.boyut and 0 <= yc < self.boyut:
                    yeni_bos  = ys * self.boyut + yc
                    liste     = list(durum)
                    liste[bos], liste[yeni_bos] = liste[yeni_bos], liste[bos]
                    yeni_tuple = tuple(liste)
                    if yeni_tuple == hedef_tuple:
                        return (hamleler + [yon])[0] if hamleler else yon
                    if yeni_tuple not in ziyaret:
                        ziyaret.add(yeni_tuple)
                        kuyruk.append((yeni_tuple, yeni_bos, hamleler + [yon]))
        return None   # çözüm bulunamadı (MAX_DERINLIK aşıldı)

#  ANİMASYON YÖNETİCİSİ

class KareAnimasyon:
    """
    Bir karenin başlangıç konumundan bitiş konumuna düzgün kaymasını sağlar.

    Parametreler:
      baslangic_px – (x, y) piksel başlangıç noktası
      bitis_px     – (x, y) piksel bitiş noktası
      sure_kare    – kaç karede tamamlanacak
    """

    def __init__(self, baslangic_px, bitis_px, sure_kare=8):
        self.baslangic  = baslangic_px
        self.bitis      = bitis_px
        self.sure       = sure_kare
        self.gecen      = 0
        self.bitti      = False

    def guncelle(self):
        """Her karede bir adım ilerler."""
        self.gecen += 1
        if self.gecen >= self.sure:
            self.bitti = True

    def suanki_poz(self):
        """Animasyonun şu anki piksel konumunu döndürür (ease-out eğrisi)."""
        if self.bitti:
            return self.bitis
        t = self.gecen / self.sure
        # Ease-out: t^0.5 ile yumuşatılmış geçiş
        t_yumus = math.sqrt(t)
        x = self.baslangic[0] + (self.bitis[0] - self.baslangic[0]) * t_yumus
        y = self.baslangic[1] + (self.bitis[1] - self.baslangic[1]) * t_yumus
        return (int(x), int(y))

#  ANA OYUN SINIFI

class SlidingPuzzleOyunu:
    """
    Tüm oyun durumlarını yöneten ana sınıf.

    Durumlar (self.durum):
      "menu"    – Seviye & tema seçim ekranı
      "oyun"    – Oyun ekranı
      "bitis"   – Kazanma ekranı

    Oyun Döngüsü yapısı:
    """

    def __init__(self):
        pygame.init()
        self.ekran  = pygame.display.set_mode((EKRAN_EN, EKRAN_BOY))
        pygame.display.set_caption(BASLIK)
        self.saat   = pygame.time.Clock()

        # Ses sistemi
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self._sesler_olustur()

        # Fontlar
        self.font_buyuk = pygame.font.SysFont("segoeui", 56, bold=True)
        self.font_orta  = pygame.font.SysFont("segoeui", 34, bold=True)
        self.font_kucuk = pygame.font.SysFont("segoeui", 22)
        self.font_mini  = pygame.font.SysFont("segoeui", 16)

        # Oyun durumu
        self.durum        = "menu"
        self.secili_seviye = "Kolay"
        self.tema_indeks  = 0
        self.tema_adi     = TEMA_SIRASI[self.tema_indeks]
        self._tema_muzigini_cal()

        # En iyi skor sistemi
        self.en_iyi_skorlar = self._en_iyi_skorlari_yukle()
        self.yeni_rekor = False

        # Bulmaca nesnesi (yeni_oyun çağrısında oluşturulur)
        self.bulmaca      = None
        self.kare_boyutu  = 0

        # Animasyon
        self.animasyonlar = {}   # indeks → KareAnimasyon

        # HUD bilgileri
        self.hamle_sayisi = 0
        self.sure_baslangic = 0
        self.sure_toplam  = 0
        self.oyun_devam   = False

        # İpucu
        self.ipucu_hakki      = MAX_IPUCU
        self.ipucu_yon        = None    # BFS'in önerdiği yön
        self.ipucu_sure       = 0      # ipucu gösterim süresi (kare)
        self.hata_sallanti    = 0      # yanlış hamlede kısa shake efekti

        # Yıldız titreme efekti (kazanma ekranı)
        self.yildiz_anim = 0

        # Sürükle-bırak hareketi
        self.suruklenen_indeks = None
        self.surukleme_baslangic = (0, 0)
        self.surukleme_offset = (0, 0)
        self.surukleme_yonu = None
        self.surukleme_hedef = None

        # Otomatik çözme sistemi
        self.oto_cozuyor = False
        self.oto_cozum_kuyrugu = []
        self.oto_cozum_sayac = 0
        self.oto_cozum_aralik = 12

        # Menü butonları (yeni_oyun ve menü kurulumunda oluşturulur)
        self.menu_butonlari  = []
        self.oyun_butonlari  = []
        self.bitis_butonlari = []
        self._menu_kur()

        # Arka plan yıldızları
        self.yildizlar = [(random.randint(0, EKRAN_EN),
                           random.randint(0, EKRAN_BOY),
                           random.uniform(0.5, 2.0)) for _ in range(60)]


    #  EN İYİ SKOR SİSTEMİ

    def _en_iyi_skorlari_yukle(self):
        """Her zorluk için en az hamle skorunu dosyadan okur."""
        varsayilan = {"Kolay": None, "Orta": None, "Zor": None}
        yol = skor_dosya_yolu()
        if not os.path.exists(yol):
            return varsayilan
        try:
            with open(yol, "r", encoding="utf-8") as f:
                veri = json.load(f)
            for seviye in varsayilan:
                deger = veri.get(seviye)
                varsayilan[seviye] = int(deger) if deger is not None else None
            return varsayilan
        except Exception:
            return varsayilan

    def _en_iyi_skorlari_kaydet(self):
        """En iyi skorları JSON dosyasına yazar."""
        try:
            with open(skor_dosya_yolu(), "w", encoding="utf-8") as f:
                json.dump(self.en_iyi_skorlar, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _en_iyi_skoru_guncelle(self):
        """Oyun bitince mevcut hamle sayısı daha iyiyse kaydeder."""
        mevcut = self.en_iyi_skorlar.get(self.secili_seviye)
        if mevcut is None or self.hamle_sayisi < mevcut:
            self.en_iyi_skorlar[self.secili_seviye] = self.hamle_sayisi
            self.yeni_rekor = True
            self._en_iyi_skorlari_kaydet()
        else:
            self.yeni_rekor = False

    #  SES (Ses Tasarımı)

    def _sesler_olustur(self):
        """
        Tema bazlı arka plan müzikleri ve kısa efektler üretir.
        Harici dosya gerekmez; tema değiştikçe müzik de değişir.
        """
        import struct
        freq = 44100

        def _ses_olustur(nota_hz, sure_ms, ses=0.35, zarf=(0.04, 0.35)):
            ornekler = int(freq * sure_ms / 1000)
            atk = max(1, int(ornekler * zarf[0]))
            rel = max(1, int(ornekler * zarf[1]))
            veri = bytearray()
            for i in range(ornekler):
                t = i / freq
                if i < atk:
                    zarf_d = i / atk
                elif i > ornekler - rel:
                    zarf_d = max(0, (ornekler - i) / rel)
                else:
                    zarf_d = 1.0
                dalga = math.sin(2 * math.pi * nota_hz * t) + 0.18 * math.sin(2 * math.pi * nota_hz * 2 * t)
                deger = int(zarf_d * ses * 15000 * dalga)
                veri += struct.pack('<hh', deger, deger)
            return pygame.mixer.Sound(buffer=bytes(veri))

        def _tema_muzigi(akor, tempo=1.0, sure_ms=2600, ses=0.12):
            ornekler = int(freq * sure_ms / 1000)
            veri = bytearray()
            for i in range(ornekler):
                t = i / freq
                fade = min(1.0, i / (freq * 0.35), (ornekler - i) / (freq * 0.45))
                dalga = sum(math.sin(2 * math.pi * hz * t) for hz in akor) / len(akor)
                nabiz = 0.72 + 0.28 * math.sin(2 * math.pi * tempo * t)
                deger = int(fade * nabiz * ses * 12000 * dalga)
                veri += struct.pack('<hh', deger, deger)
            snd = pygame.mixer.Sound(buffer=bytes(veri))
            snd.set_volume(0.28)
            return snd

        try:
            # Önce klasördeki hazır WAV dosyalarını kullanır.
            # Dosyalar yoksa eski otomatik üretilen seslere düşer.
            ses_klasoru = os.path.join(os.path.dirname(__file__), "sounds")

            def dosyadan_ses(dosya_adi, yedek_ses):
                yol = os.path.join(ses_klasoru, dosya_adi)
                if os.path.exists(yol):
                    return pygame.mixer.Sound(yol)
                return yedek_ses

            self.ses_hamle  = dosyadan_ses("move.wav",  _ses_olustur(660,  70, 0.20))
            self.ses_hata   = dosyadan_ses("error.wav", _ses_olustur(170, 120, 0.17))
            self.ses_kazanc = dosyadan_ses("win.wav",   _ses_olustur(880, 450, 0.28))
            self.ses_ipucu  = dosyadan_ses("hint.wav",  _ses_olustur(720, 130, 0.22))
            self.ses_menu   = dosyadan_ses("menu.wav",  _ses_olustur(640,  60, 0.16))

            self.tema_muzikleri = {
                "Okyanus": dosyadan_ses("music_okyanus.wav", _tema_muzigi([246.94, 329.63, 392.00, 493.88], tempo=0.9, ses=0.10)),
                "Orman":   dosyadan_ses("music_orman.wav",   _tema_muzigi([220.00, 261.63, 329.63, 392.00], tempo=0.7, ses=0.09)),
                "Gece":    dosyadan_ses("music_gece.wav",    _tema_muzigi([196.00, 246.94, 293.66, 392.00], tempo=0.8, ses=0.10)),
                "Alev":    dosyadan_ses("music_alev.wav",    _tema_muzigi([261.63, 329.63, 415.30, 523.25], tempo=1.35, ses=0.11)),
            }

            for muzik in self.tema_muzikleri.values():
                muzik.set_volume(0.32)
            self.aktif_muzik = None
        except Exception:
            class SessizSes:
                def play(self, *args, **kwargs): pass
                def stop(self, *args, **kwargs): pass
                def set_volume(self, *args, **kwargs): pass
            self.ses_hamle = self.ses_hata = self.ses_kazanc = self.ses_ipucu = self.ses_menu = SessizSes()
            self.tema_muzikleri = {ad: SessizSes() for ad in TEMALAR}
            self.aktif_muzik = None

    def _tema_muzigini_cal(self):
        """Seçili temanın müziğini başlatır; önceki tema müziğini durdurur."""
        try:
            if self.aktif_muzik:
                self.aktif_muzik.stop()
            self.aktif_muzik = self.tema_muzikleri.get(self.tema_adi)
            if self.aktif_muzik:
                self.aktif_muzik.play(loops=-1)
        except Exception:
            pass

    #  MENÜ KURULUMU (Buton Sınıfı)

    def _menu_kur(self):
        """
        Ana menü butonlarını oluşturur.
        Ana Menü yapısına uygun.
        """
        self.menu_butonlari.clear()

        MX = EKRAN_EN // 2

        # Seviye butonları
        for i, (ad, bilgi) in enumerate(SEVIYELER.items()):
            secili = (ad == self.secili_seviye)
            renk       = bilgi["renk"] if secili else (60, 65, 80)
            hover_renk = tuple(min(255, c + 40) for c in bilgi["renk"])
            btn = Buton(
                MX - 220 + i * 220, 325, 170, 54, ad,
                renk=renk, hover_renk=hover_renk,
                callback=lambda a=ad: self._seviye_sec(a),
                font_boyut=24
            )
            self.menu_butonlari.append(btn)

        # Tema değiştir butonu
        btn_tema = Buton(
            MX, 425, 230, 48, f"Tema: {self.tema_adi}",
            renk=(70, 50, 100), hover_renk=(110, 80, 150),
            callback=self._tema_degistir,
            font_boyut=22
        )
        self.menu_butonlari.append(btn_tema)

        # Oyna butonu
        btn_oyna = Buton(
            MX, 510, 220, 58, "OYNA",
            renk=(30, 130, 80), hover_renk=(50, 180, 110),
            callback=self.yeni_oyun,
            font_boyut=30
        )
        self.menu_butonlari.append(btn_oyna)

    def _oyun_butonlari_kur(self):
        """Oyun sırasında altta, üst üste binmeyen butonları oluşturur."""
        self.oyun_butonlari.clear()
        mx = EKRAN_EN // 2
        y = 640
        aralik = 135

        self.oyun_butonlari.append(Buton(
            mx - int(aralik * 1.5), y, 125, 42, f"İpucu ({self.ipucu_hakki})",
            renk=(130, 100, 20), hover_renk=(190, 150, 30),
            callback=self._ipucu_iste, font_boyut=18
        ))
        self.oyun_butonlari.append(Buton(
            mx - int(aralik * 0.5), y, 125, 42, "Oto Çöz",
            renk=(30, 115, 125), hover_renk=(45, 160, 175),
            callback=self._oto_coz_baslat, font_boyut=18
        ))
        self.oyun_butonlari.append(Buton(
            mx + int(aralik * 0.5), y, 125, 42, "Tema",
            renk=(70, 50, 100), hover_renk=(110, 80, 150),
            callback=self._tema_degistir, font_boyut=18
        ))
        self.oyun_butonlari.append(Buton(
            mx + int(aralik * 1.5), y, 125, 42, "Yenile",
            renk=(60, 80, 130), hover_renk=(90, 120, 180),
            callback=self.yeni_oyun, font_boyut=18
        ))

    def _bitis_butonlari_kur(self):
        """Kazanma ekranı butonlarını oluşturur."""
        self.bitis_butonlari.clear()
        MX = EKRAN_EN // 2

        btn_tekrar = Buton(
            MX - 110, 600, 190, 54, "Tekrar Oyna",
            renk=(30, 120, 80), hover_renk=(50, 170, 110),
            callback=self.yeni_oyun,
            font_boyut=24
        )
        btn_menu = Buton(
            MX + 110, 600, 190, 54, "Ana Menü",
            renk=(60, 80, 140), hover_renk=(90, 120, 190),
            callback=lambda: self._duruma_gec("menu"),
            font_boyut=24
        )
        self.bitis_butonlari.extend([btn_tekrar, btn_menu])

    #  OYUN KURULUM & SIFIRLAMA

    def yeni_oyun(self):
        """
        Seçili seviyeye göre yeni bir oyun başlatır.
        Bulmacayı karıştırır, sayaçları sıfırlar.
        """
        bilgi        = SEVIYELER[self.secili_seviye]
        boyut        = bilgi["boyut"]
        karisma      = bilgi["karisma"]

        self.bulmaca = Bulmaca(boyut)
        self.bulmaca.karistir(karisma)

        # Kare boyutunu orta oyun alanına göre hesapla; alt butonlara taşmaz.
        maks_alan_en  = 520
        maks_alan_boy = 455
        self.kare_boyutu = min(maks_alan_en // boyut, maks_alan_boy // boyut)
        self.bosluk = max(6, self.kare_boyutu // 12)

        self.hamle_sayisi    = 0
        self.sure_baslangic  = time.time()
        self.sure_toplam     = 0
        self.oyun_devam      = True
        self.animasyonlar    = {}
        self.ipucu_hakki     = MAX_IPUCU
        self.ipucu_yon       = None
        self.ipucu_sure      = 0
        self.hata_sallanti   = 0
        self.suruklenen_indeks = None
        self.surukleme_offset = (0, 0)
        self.surukleme_yonu = None
        self.surukleme_hedef = None
        self.oto_cozuyor = False
        self.oto_cozum_kuyrugu = []
        self.oto_cozum_sayac = 0
        self.yeni_rekor = False

        self._oyun_butonlari_kur()
        self.durum = "oyun"

    def _duruma_gec(self, yeni_durum):
        """Oyun durumunu değiştirir ve gerekli kurulumları yapar."""
        self.durum = yeni_durum
        if yeni_durum == "menu":
            self._menu_kur()

    def _seviye_sec(self, ad):
        """Menüden seviye seçildiğinde çağrılır."""
        self.secili_seviye = ad
        self.ses_menu.play()
        self._menu_kur()   # seçili rengi güncellemek için butonları yenile

    def _tema_degistir(self):
        """Bir sonraki temaya geçer (döngüsel)."""
        self.tema_indeks = (self.tema_indeks + 1) % len(TEMA_SIRASI)
        self.tema_adi    = TEMA_SIRASI[self.tema_indeks]
        self.ses_menu.play()
        self._tema_muzigini_cal()
        # Menüdeyse butonu güncelle
        if self.durum == "menu":
            self._menu_kur()
        elif self.durum == "oyun":
            self._oyun_butonlari_kur()

    def _ipucu_iste(self):
        """İpucu butonuna basıldığında hazır çözüm kuyruğundan ilk hamleyi gösterir."""
        if self.ipucu_hakki <= 0 or self.oto_cozuyor:
            return
        # Orta/Zor seviyelerde BFS donma yapmasın diye hazır çözüm yolu kullanılır.
        yon = self.bulmaca.cozum_yolu[0] if self.bulmaca.cozum_yolu else None
        if yon:
            self.ipucu_yon  = yon
            self.ipucu_sure = 120   # 2 saniye göster
            self.ipucu_hakki -= 1
            self.ses_ipucu.play()
            self._oyun_butonlari_kur()   # hakk sayısını güncelle
        else:
            self.ses_hata.play()

    def _oto_coz_baslat(self):
        """C tuşu veya Oto Çöz butonu ile bulmacayı otomatik çözer."""
        if not self.oyun_devam or self.animasyonlar or self.bulmaca.cozuldu_mu():
            return
        if not self.bulmaca.cozum_yolu:
            self.ses_hata.play()
            return
        self.oto_cozum_kuyrugu = list(self.bulmaca.cozum_yolu)
        self.oto_cozuyor = True
        self.oto_cozum_sayac = 0
        self.ses_ipucu.play()

    #  ANA DÖNGÜ

    def calistir(self):
        """
        Programın ana döngüsü.
        1. Olayları işle
        2. Güncelle
        3. Ekrana çiz
        4. FPS sınırla
        """
        calistir = True
        while calistir:
            # 1. Olayları işle
            for olay in pygame.event.get():
                if olay.type == pygame.QUIT:
                    calistir = False

                if self.durum == "menu":
                    for btn in self.menu_butonlari:
                        btn.olay_isle(olay)

                elif self.durum == "oyun":
                    self._oyun_olaylar(olay)

                elif self.durum == "bitis":
                    for btn in self.bitis_butonlari:
                        btn.olay_isle(olay)

            #  2. Güncelle
            if self.durum == "menu":
                for btn in self.menu_butonlari:
                    btn.guncelle()

            elif self.durum == "oyun":
                self._oyun_guncelle()
                for btn in self.oyun_butonlari:
                    btn.guncelle()

            elif self.durum == "bitis":
                self.yildiz_anim += 1
                for btn in self.bitis_butonlari:
                    btn.guncelle()

            # 3. Çiz
            self._ciz()

            #  4. FPS sınırla
            self.saat.tick(FPS)

        pygame.quit()
        sys.exit()
    #  OLAY İŞLEME – OYUN EKRANI

    def _oyun_olaylar(self, olay):
        """
        Oyun sırasındaki klavye ve fare olaylarını işler.
       – Klavye Girdisi, – Fare Girdisi.
        """
        # Butonlar
        for btn in self.oyun_butonlari:
            btn.olay_isle(olay)

        if olay.type == pygame.KEYDOWN:
            # Ok tuşları / WASD ile hamle
            # Tuş yönü, hareket eden KARENİN yönüdür.
            # Örn. sağdaki kareyi sola kaydırmak için SOL tuşuna basılır.
            harita = {
                pygame.K_UP:    "asagi",
                pygame.K_DOWN:  "yukari",
                pygame.K_LEFT:  "sag",
                pygame.K_RIGHT: "sol",
                pygame.K_w:     "asagi",
                pygame.K_s:     "yukari",
                pygame.K_a:     "sag",
                pygame.K_d:     "sol",
            }
            if olay.key in harita and not self.animasyonlar:
                self._hamle_dene(harita[olay.key])

            elif olay.key == pygame.K_h:
                self._ipucu_iste()

            elif olay.key == pygame.K_c:
                self._oto_coz_baslat()

            elif olay.key == pygame.K_t:
                self._tema_degistir()

            elif olay.key == pygame.K_ESCAPE:
                self._duruma_gec("menu")

        elif olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
            self._surukleme_baslat(olay.pos)

        elif olay.type == pygame.MOUSEMOTION:
            self._surukleme_guncelle(olay.pos)

        elif olay.type == pygame.MOUSEBUTTONUP and olay.button == 1:
            self._surukleme_bitir(olay.pos)

    def _hata_efekti(self):
        """Yanlış hamlede kısa ses + titreşim efekti başlatır."""
        self.hata_sallanti = 12
        self.ses_hata.play()

    def _hamle_dene(self, yon, otomatik=False):
        """
        Belirtilen yönde hamle yapmayı dener.
        Başarılıysa animasyon başlatır.
        """
        if not self.oyun_devam or self.animasyonlar:
            return

        bos_once = self.bulmaca.bos_pos
        basarili  = self.bulmaca.hamle_yap(yon)

        if basarili:
            self.hamle_sayisi += 1
            self.ses_hamle.play()

            if otomatik:
                # Oto çözüm zaten çözüm kuyruğundaki ilk hamleyi uygular.
                if self.bulmaca.cozum_yolu:
                    self.bulmaca.cozum_yolu.pop(0)
            else:
                # Kullanıcı ipucunun söylediği hamleyi yaptıysa, çözüm kuyruğunda
                # o hamleyi tüketmeliyiz. Aksi halde bir sonraki ipucu aynı
                # hamlenin tersini gösterip oyuncuyu geri döndürür.
                if self.bulmaca.cozum_yolu and yon == self.bulmaca.cozum_yolu[0]:
                    self.bulmaca.cozum_yolu.pop(0)
                else:
                    # Kullanıcı farklı bir hamle yaptıysa güvenli çözüm yolu:
                    # önce bu hamleyi geri al, sonra eski çözüm yoluna devam et.
                    self.bulmaca.cozum_yolu.insert(0, ZITLAR[yon])

            # Animasyon başlat: hangi kare hareket etti?
            bos_simdi = self.bulmaca.bos_pos
            # Şu an boş olan → daha önce hareket eden kare oraya geldi
            self._animasyon_baslat(bos_simdi, bos_once)

            # İpucu öneri süresini sıfırla
            if self.ipucu_sure > 0:
                self.ipucu_sure = 0
                self.ipucu_yon  = None
        else:
            self._hata_efekti()

    def _surukleme_baslat(self, pos):
        """Boş kareye komşu bir kareye basılırsa sürüklemeyi başlatır."""
        if not self.oyun_devam or self.animasyonlar:
            return
        boyut = self.bulmaca.boyut
        bos_satir, bos_sutun = divmod(self.bulmaca.bos_pos, boyut)

        for indeks in range(boyut * boyut):
            if self.bulmaca.izgara[indeks] == 0:
                continue
            kx, ky = self._kare_piksel(indeks)
            rect = pygame.Rect(kx, ky, self.kare_boyutu - self.bosluk, self.kare_boyutu - self.bosluk)
            if not rect.collidepoint(pos):
                continue
            satir, sutun = divmod(indeks, boyut)
            if abs(satir - bos_satir) + abs(sutun - bos_sutun) != 1:
                self._hata_efekti()
                return

            # Tıklanan kare boşluğa hangi yönde kayacak?
            if satir < bos_satir:
                yon = "yukari"
                eksen = "y"; limit = self.kare_boyutu
            elif satir > bos_satir:
                yon = "asagi"
                eksen = "y"; limit = -self.kare_boyutu
            elif sutun < bos_sutun:
                yon = "sol"
                eksen = "x"; limit = self.kare_boyutu
            else:
                yon = "sag"
                eksen = "x"; limit = -self.kare_boyutu

            self.suruklenen_indeks = indeks
            self.surukleme_baslangic = pos
            self.surukleme_offset = (0, 0)
            self.surukleme_yonu = yon
            self.surukleme_hedef = (eksen, limit)
            return

    def _surukleme_guncelle(self, pos):
        """Sürüklenen kareyi yalnızca boşluğa doğru kaydırır."""
        if self.suruklenen_indeks is None or not self.surukleme_hedef:
            return
        eksen, limit = self.surukleme_hedef
        dx = pos[0] - self.surukleme_baslangic[0]
        dy = pos[1] - self.surukleme_baslangic[1]
        if eksen == "x":
            # limit pozitifse sağa, negatifse sola hareket serbesttir.
            miktar = max(0, min(dx, limit)) if limit > 0 else min(0, max(dx, limit))
            self.surukleme_offset = (int(miktar), 0)
        else:
            miktar = max(0, min(dy, limit)) if limit > 0 else min(0, max(dy, limit))
            self.surukleme_offset = (0, int(miktar))

    def _surukleme_bitir(self, pos):
        """Yeterince sürüklenirse hamleyi yapar; kısa dokunuşta tıklama gibi çalışır."""
        if self.suruklenen_indeks is None:
            return
        ox, oy = self.surukleme_offset
        mesafe = abs(ox) + abs(oy)
        yon = self.surukleme_yonu
        self.suruklenen_indeks = None
        self.surukleme_offset = (0, 0)
        self.surukleme_yonu = None
        self.surukleme_hedef = None

        # Kısa tıklamada da hamle yapılsın; sürüklemede eşik geçilince hamle yapılsın.
        if mesafe >= self.kare_boyutu * 0.25 or mesafe < 5:
            self._hamle_dene(yon)
        else:
            self._hata_efekti()

    def _fare_tiklama(self, pos):
        """
        Tıklanan kare boş hücreye komşuysa kareyi boşluğa kaydırır.
        Böylece oyuncu doğrudan hareket ettirmek istediği kareye tıklar.
        """
        if not self.oyun_devam or self.animasyonlar:
            return

        boyut = self.bulmaca.boyut
        bos_satir, bos_sutun = divmod(self.bulmaca.bos_pos, boyut)

        for indeks in range(boyut * boyut):
            kx, ky = self._kare_piksel(indeks)
            rect = pygame.Rect(kx, ky, self.kare_boyutu - self.bosluk,
                               self.kare_boyutu - self.bosluk)

            if not rect.collidepoint(pos) or self.bulmaca.izgara[indeks] == 0:
                continue

            satir, sutun = divmod(indeks, boyut)
            komsu_mu = abs(satir - bos_satir) + abs(sutun - bos_sutun) == 1

            if not komsu_mu:
                self._hata_efekti()
                return

            # Boş hücre tıklanan kareye doğru hareket eder; kare boşluğa kaymış olur.
            if satir < bos_satir:
                yon = "yukari"
            elif satir > bos_satir:
                yon = "asagi"
            elif sutun < bos_sutun:
                yon = "sol"
            else:
                yon = "sag"

            self._hamle_dene(yon)
            return

    #  ANİMASYON

    def _animasyon_baslat(self, kaynak_indeks, hedef_indeks):
        """
        Kaynak indeksteki karenin hedef indeks piksel konumuna
        kayma animasyonunu başlatır.
        """
        baslangic_px = self._kare_piksel(kaynak_indeks)
        bitis_px     = self._kare_piksel(hedef_indeks)
        self.animasyonlar[hedef_indeks] = KareAnimasyon(baslangic_px, bitis_px, sure_kare=8)

    def _kare_piksel(self, indeks):
        """
        Izgara indeksinden sol üst köşe piksel konumunu hesaplar.
        Rect Sınıfı fikri kullanıldı.
        """
        boyut  = self.bulmaca.boyut
        satir  = indeks // boyut
        sutun  = indeks  % boyut

        # Izgarayı ekranın gerçek orta alanına al; üst yazılar ve alt butonlarla çakışmaz.
        izgara_en  = self.kare_boyutu * boyut
        izgara_boy = self.kare_boyutu * boyut
        baslangic_x = (EKRAN_EN - izgara_en) // 2
        baslangic_y = 135 + (455 - izgara_boy) // 2

        x = baslangic_x + sutun * self.kare_boyutu
        y = baslangic_y + satir  * self.kare_boyutu
        return (x, y)

    #  GÜNCELLEME – OYUN EKRANI

    def _oyun_guncelle(self):
        """
        Her karede oyun mantığını günceller:
          - Süre sayacı
          - Animasyonlar
          - İpucu süre sayacı
          - Yanlış hamle shake efekti
          - Kazanma kontrolü
        """
        if not self.oyun_devam:
            return

        # Süreyi güncelle
        self.sure_toplam = time.time() - self.sure_baslangic

        # Animasyonları güncelle; bitmişleri temizle
        biten = []
        for indeks, anim in self.animasyonlar.items():
            anim.guncelle()
            if anim.bitti:
                biten.append(indeks)
        for i in biten:
            del self.animasyonlar[i]

        # Otomatik çözme: animasyon yokken sıradaki hamleyi uygula
        if self.oto_cozuyor and not self.animasyonlar:
            self.oto_cozum_sayac += 1
            if self.oto_cozum_sayac >= self.oto_cozum_aralik:
                self.oto_cozum_sayac = 0
                if self.oto_cozum_kuyrugu:
                    yon = self.oto_cozum_kuyrugu.pop(0)
                    self._hamle_dene(yon, otomatik=True)
                else:
                    self.oto_cozuyor = False

        # Yanlış hareket titreşim süresini azalt
        if self.hata_sallanti > 0:
            self.hata_sallanti -= 1

        # İpucu süresini azalt
        if self.ipucu_sure > 0:
            self.ipucu_sure -= 1
            if self.ipucu_sure == 0:
                self.ipucu_yon = None

        # Kazanma kontrolü
        if self.bulmaca.cozuldu_mu() and not self.animasyonlar:
            self.oyun_devam = False
            self._en_iyi_skoru_guncelle()
            self.ses_kazanc.play()
            self._bitis_butonlari_kur()
            self.durum = "bitis"

    #  ÇİZİM FONKSİYONLARI

    def _ciz(self):
        """Aktif duruma göre ilgili ekranı çizer."""
        tema = TEMALAR[self.tema_adi]
        self.ekran.fill(tema["arkaplan"])
        self._arka_plan_yildizlar(tema)

        if self.durum == "menu":
            self._menu_ciz(tema)
        elif self.durum == "oyun":
            self._oyun_ciz(tema)
        elif self.durum == "bitis":
            self._bitis_ciz(tema)

        pygame.display.flip()

    def _arka_plan_yildizlar(self, tema):
        """Arka planda hafif yıldız noktaları çizer."""
        for (sx, sy, parlaklik) in self.yildizlar:
            renk = tuple(min(255, int(c * 0.3 + parlaklik * 15))
                         for c in tema["arkaplan"])
            pygame.draw.circle(self.ekran, renk, (sx, sy), 1)

    #Menü Ekranı

    def _menu_ciz(self, tema):
        """Ana menü ekranını çizer."""
        MX = EKRAN_EN // 2

        # Başlık
        golge = self.font_buyuk.render("TileFlow", True, (0, 0, 0))
        baslik = self.font_buyuk.render("TileFlow", True, tema["vurgu"])
        self.ekran.blit(golge, golge.get_rect(center=(MX + 3, 103)))
        self.ekran.blit(baslik, baslik.get_rect(center=(MX, 100)))

        alt_baslik = self.font_kucuk.render("Kareleri sıraya diz, boşluğu akıllıca kullan!",
                                             True, tema["metin"])
        self.ekran.blit(alt_baslik, alt_baslik.get_rect(center=(MX, 150)))

        # Seviye seçimi başlığı
        seviye_lbl = self.font_kucuk.render("Zorluk Seviyesi Seç:", True, tema["kenarlık"])
        self.ekran.blit(seviye_lbl, seviye_lbl.get_rect(center=(MX, 255)))

        # Bilgi metni
        bilgiler = [
            "Komşu kareyi sürükle veya ok/WASD tuşlarıyla oyna",
            "H: İpucu hakkı    C: Otomatik çöz",
            "T: Tema değiştir    ESC: Menüye dön",
        ]
        for i, satir in enumerate(bilgiler):
            metin = self.font_mini.render(satir, True, tema["metin"])
            self.ekran.blit(metin, metin.get_rect(center=(MX, 580 + i * 24)))

        # Butonları çiz
        for btn in self.menu_butonlari:
            btn.ciz(self.ekran)

    # Oyun Ekranı

    def _oyun_ciz(self, tema):
        """Oyun ekranının tüm bileşenlerini, üst üste binmeyecek biçimde çizer."""
        self._hud_ciz(tema)
        self._izgara_ciz(tema)
        for btn in self.oyun_butonlari:
            btn.ciz(self.ekran)

        # ESC yazısı artık sağ üstte değil; altta küçük ve ortalı bilgi satırı.
        bilgi = self.font_mini.render("ESC: Menüye dön  •  H: İpucu  •  C: Otomatik çöz  •  T: Tema", True, tema["metin"])
        self.ekran.blit(bilgi, bilgi.get_rect(center=(EKRAN_EN // 2, 685)))

        if self.ipucu_yon and self.ipucu_sure > 0:
            self._ipucu_goster(tema)

    def _hud_ciz(self, tema):
        """Üstte ortalanmış, taşmayan modern bilgi paneli."""
        mx = EKRAN_EN // 2

        baslik = self.font_orta.render("ZEKA KARELERİ", True, tema["vurgu"])
        self.ekran.blit(baslik, baslik.get_rect(center=(mx, 38)))

        oran = self.bulmaca.tamamlanma_orani()
        en_iyi = self.en_iyi_skorlar.get(self.secili_seviye)
        bilgiler = [
            f"Seviye: {self.secili_seviye}",
            f"Tema: {self.tema_adi}",
            f"Süre: {saniyeleri_formatla(self.sure_toplam)}",
            f"Hamle: {self.hamle_sayisi}",
            f"En İyi: {skor_etiketi(en_iyi)}",
            f"İpucu: {self.ipucu_hakki}/{MAX_IPUCU}",
        ]

        panel = pygame.Rect(0, 0, 820, 54)
        panel.center = (mx, 88)
        pygame.draw.rect(self.ekran, tema["panel"], panel, border_radius=18)
        pygame.draw.rect(self.ekran, tema["kenarlık"], panel, 1, border_radius=18)

        xler = [panel.left + 70, panel.left + 200, panel.left + 330, panel.left + 455, panel.left + 585, panel.left + 735]
        for x, metin in zip(xler, bilgiler):
            renk = tema["vurgu"] if metin.startswith("En İyi") else tema["metin"]
            yazi = self.font_mini.render(metin, True, renk)
            self.ekran.blit(yazi, yazi.get_rect(center=(x, panel.centery - 8)))

        yuzde = int(oran * 100)
        tamamlanma_yazisi = self.font_mini.render(f"Tamamlanma Seviyesi: %{yuzde}", True, tema["vurgu"])
        self.ekran.blit(tamamlanma_yazisi, tamamlanma_yazisi.get_rect(center=(mx, panel.bottom - 20)))

        bar_renk = renk_karistir((200, 60, 60), (60, 200, 80), oran)
        ilerlem_bari_ciz(self.ekran, panel.left + 70, panel.bottom - 9, panel.width - 140, 7,
                          oran, bar_renk, arkaplan=(30, 30, 40))

    def _izgara_ciz(self, tema):
        """
        Sade modern kare tasarımı.
        Kare içindeki küçük simgeler kaldırıldı; sadece büyük ve ortalı sayı var.
        Sürüklenen kare parmağın/farenin hareketine göre boşluğa doğru kayar.
        """
        boyut   = self.bulmaca.boyut
        kb      = self.kare_boyutu
        bosluk  = self.bosluk
        kare_ic = kb - bosluk
        tema_renkler = TEMALAR[self.tema_adi]["kare_renk"]

        # Izgara arka paneli
        ilk_x, ilk_y = self._kare_piksel(0)
        panel = pygame.Rect(ilk_x - 12, ilk_y - 12, kb * boyut + 12, kb * boyut + 12)
        pygame.draw.rect(self.ekran, tuple(max(0, c - 8) for c in tema["panel"]), panel, border_radius=22)
        pygame.draw.rect(self.ekran, tema["kenarlık"], panel, 2, border_radius=22)

        # Boş kareye komşu olan oynanabilir kareleri hesapla.
        bos_satir, bos_sutun = divmod(self.bulmaca.bos_pos, boyut)
        oynanabilir_indeksler = set()
        for ds, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ss, sc = bos_satir + ds, bos_sutun + dc
            if 0 <= ss < boyut and 0 <= sc < boyut:
                oynanabilir_indeksler.add(ss * boyut + sc)

        ipucu_indeks = None
        if self.ipucu_yon and self.ipucu_sure > 0:
            D = {"yukari": (-1, 0), "asagi": (1, 0), "sol": (0, -1), "sag": (0, 1)}
            ds, dc = D[self.ipucu_yon]
            is_, ic_ = bos_satir + ds, bos_sutun + dc
            if 0 <= is_ < boyut and 0 <= ic_ < boyut:
                ipucu_indeks = is_ * boyut + ic_

        for indeks in range(boyut * boyut):
            deger = self.bulmaca.izgara[indeks]

            if indeks in self.animasyonlar:
                px, py = self.animasyonlar[indeks].suanki_poz()
            else:
                px, py = self._kare_piksel(indeks)

            # Yanlış hamlede tüm ızgaraya minik titreşim ver.
            if self.hata_sallanti > 0:
                px += int(math.sin(self.hata_sallanti * 2.7) * 5)

            # Kullanıcı kareyi elle sürüklüyorsa kareyi gerçek zamanlı oynat.
            if indeks == self.suruklenen_indeks:
                px += self.surukleme_offset[0]
                py += self.surukleme_offset[1]

            kare_rect = pygame.Rect(px, py, kare_ic, kare_ic)

            if deger == 0:
                pygame.draw.rect(self.ekran, tema["bos_kare"], kare_rect, border_radius=14)
                pygame.draw.rect(self.ekran, tema["kenarlık"], kare_rect, 1, border_radius=14)
                continue

            temel_renk = tema_renkler[(deger - 1) % len(tema_renkler)]
            dogru = self.bulmaca.kare_dogru_mu(indeks)
            renk = tuple(min(255, c + 24) for c in temel_renk) if dogru else temel_renk

            if indeks == ipucu_indeks:
                faz = (self.ipucu_sure // 8) % 2
                renk = (255, 235, 95) if faz == 0 else renk

            # Gölge
            golge = pygame.Rect(kare_rect.x + 4, kare_rect.y + 6, kare_rect.width, kare_rect.height)
            pygame.draw.rect(self.ekran, (0, 0, 0), golge, border_radius=14)

            # Ana kare
            pygame.draw.rect(self.ekran, renk, kare_rect, border_radius=14)

            # Hafif üst parlama; küçük kare/simge değil, sadece derinlik efekti.
            parlama = pygame.Rect(kare_rect.x + 8, kare_rect.y + 8, kare_rect.width - 16, max(8, kare_rect.height // 5))
            pygame.draw.rect(self.ekran, tuple(min(255, c + 45) for c in renk), parlama, border_radius=10)

            if dogru:
                k_renk, k_kalin = (120, 255, 150), 3
            elif indeks == ipucu_indeks:
                k_renk, k_kalin = (255, 240, 80), 3
            elif indeks == self.suruklenen_indeks:
                k_renk, k_kalin = (255, 255, 255), 3
            elif indeks in oynanabilir_indeksler:
                # Yardım modu gibi hafif bir glow: oyuncu hangi karelerin oynanabileceğini görür.
                k_renk, k_kalin = (255, 230, 120), 2
            else:
                k_renk, k_kalin = tema["kenarlık"], 1
            pygame.draw.rect(self.ekran, k_renk, kare_rect, k_kalin, border_radius=14)

            # Büyük, net, tam ortalı sayı
            num_font = pygame.font.SysFont("segoeui", max(28, kare_ic // 2), bold=True)
            num_surf = num_font.render(str(deger), True, (255, 255, 255))
            self.ekran.blit(num_surf, num_surf.get_rect(center=kare_rect.center))

    def _ipucu_goster(self, tema):
        """
        İpucu aktifken ekranın altına yön mesajı gösterir.
        """
        # self.ipucu_yon boş karenin hareket yönüdür. Oyuncuya ise
        # sarı karenin hangi yöne kayacağı söylenmelidir; bu yön tersidir.
        kare_yonu = ZITLAR.get(self.ipucu_yon, self.ipucu_yon)
        yon_tr = {"yukari": "⬆ Yukarı",
                  "asagi":  "⬇ Aşağı",
                  "sol":    "⬅ Sol",
                  "sag":    "➡ Sağ"}.get(kare_yonu, "")
        metin = self.font_kucuk.render(f"İpucu: Sarı parlayan kareyi {yon_tr} kaydır",
                                        True, (255, 240, 80))
        x = EKRAN_EN // 2
        y = EKRAN_BOY - 30
        # Arka plan dikdörtgeni
        arka = pygame.Rect(0, 0, metin.get_width() + 20, metin.get_height() + 10)
        arka.center = (x, y)
        pygame.draw.rect(self.ekran, (40, 40, 10), arka, border_radius=8)
        pygame.draw.rect(self.ekran, (255, 220, 30), arka, 2, border_radius=8)
        self.ekran.blit(metin, metin.get_rect(center=(x, y)))

    #Kazanma Ekranı

    def _bitis_ciz(self, tema):
        """
        Motivasyonel kazanma ekranını çizer.
        Yıldız sayısı: hamle & süreye göre belirlenir.
        """
        MX = EKRAN_EN // 2

        # Yarı saydam karartma
        sis = pygame.Surface((EKRAN_EN, EKRAN_BOY), pygame.SRCALPHA)
        sis.fill((0, 0, 0, 140))
        self.ekran.blit(sis, (0, 0))

        # Animasyonlu konfeti noktaları
        for i in range(30):
            t    = (self.yildiz_anim * 0.02 + i * 0.21) % 1.0
            x_c  = (MX - 250) + (i * 37) % 500
            y_c  = int(EKRAN_BOY * t)
            boyut_c = 4 + i % 5
            renk_c = [(255,80,80),(80,255,80),(80,80,255),
                       (255,255,80),(255,80,255),(80,255,255)][i % 6]
            pygame.draw.circle(self.ekran, renk_c, (x_c, y_c), boyut_c)

        # Yıldız hesapla (1–3 yıldız)
        boyut      = self.bulmaca.boyut
        sure       = self.sure_toplam
        hamle      = self.hamle_sayisi
        min_hamle  = {"Kolay": 20, "Orta": 50, "Zor": 120}[self.secili_seviye]
        min_sure   = {"Kolay": 60, "Orta": 120, "Zor": 300}[self.secili_seviye]

        if hamle <= min_hamle and sure <= min_sure:
            yildiz_say = 3
            yorum = "MÜKEMMEL! Gerçek bir bulmaca ustasısın!"
        elif hamle <= min_hamle * 2 and sure <= min_sure * 2:
            yildiz_say = 2
            yorum = "HARİKA! Çok iyi iş çıkardın!"
        else:
            yildiz_say = 1
            yorum = "TEBRİKLER! Bulmacayı çözdün!"

        # Başlık
        baslik = self.font_buyuk.render("KAZANDIN!", True, tema["vurgu"])
        self.ekran.blit(baslik, baslik.get_rect(center=(MX, 100)))

        # Yorum
        yorum_yazi = self.font_kucuk.render(yorum, True, (240, 240, 240))
        self.ekran.blit(yorum_yazi, yorum_yazi.get_rect(center=(MX, 160)))

        # Yıldız/kutucuk göstergesi kaldırıldı.
        # Bazı bilgisayarlarda yıldız emojileri kutucuk gibi göründüğü için
        # kazanma ekranında sadece yazılı sonuç ve istatistikler gösteriliyor.

        # İstatistikler kutusu
        kutu = pygame.Rect(MX - 220, 220, 440, 205)
        pygame.draw.rect(self.ekran, tema["panel"], kutu, border_radius=12)
        pygame.draw.rect(self.ekran, tema["kenarlık"], kutu, 2, border_radius=12)

        en_iyi = self.en_iyi_skorlar.get(self.secili_seviye)
        istatler = [
            ("Seviye",       self.secili_seviye),
            ("Toplam Süre",  saniyeleri_formatla(self.sure_toplam)),
            ("Hamle Sayısı", str(self.hamle_sayisi)),
            ("En İyi Skor",  skor_etiketi(en_iyi)),
            ("Kalan İpucu",  f"{self.ipucu_hakki} / {MAX_IPUCU}"),
        ]
        for i, (lbl, deger) in enumerate(istatler):
            lbl_yazi = self.font_kucuk.render(lbl, True, tema["metin"])
            deg_yazi = self.font_kucuk.render(deger, True, tema["vurgu"])
            y_pos = 243 + i * 34
            self.ekran.blit(lbl_yazi, lbl_yazi.get_rect(midleft=(kutu.left + 20, y_pos)))
            self.ekran.blit(deg_yazi, deg_yazi.get_rect(midright=(kutu.right - 20, y_pos)))

        if self.yeni_rekor:
            rekor_kutu = pygame.Rect(MX - 190, 455, 380, 52)
            pygame.draw.rect(self.ekran, tema["panel"], rekor_kutu, border_radius=14)
            pygame.draw.rect(self.ekran, tema["vurgu"], rekor_kutu, 2, border_radius=14)
            rekor_yazi = self.font_kucuk.render("Yeni en iyi skor!", True, tema["vurgu"])
            self.ekran.blit(rekor_yazi, rekor_yazi.get_rect(center=rekor_kutu.center))

        # Butonlar
        for btn in self.bitis_butonlari:
            btn.ciz(self.ekran)
#  PROGRAMIN GİRİŞ NOKTASI

if __name__ == "__main__":
    oyun = SlidingPuzzleOyunu()
    oyun.calistir()


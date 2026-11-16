# Formativ va Summativ Baholash Uyg'unligi Asosida O'quvchilar O'quv Yutuqlarini Baholash Tizimi (EduAssess AI)

Mazkur ilmiy-amaliy loyiha o'quvchilarning har darsdagi formativ baholash natijalarini (darsdagi faollik, uy vazifalari, qisqa testlar) tahlil qilish orqali ularning zaif o'zlashtirgan mavzularini diagnostika qiladi va yakuniy (summativ / BSB / CHSB) imtihonlarni adaptiv tarzda generatsiya qilib beradi.

---

## 📌 Asosiy Imkoniyatlar va Modullar

### 1. Dinamik va Adaptiv Test Platformasi (Adaptive Assessment Engine)
- **Mavzular diagnostikasi:** Har bir mavzu oxiridagi qisqa formativ testlar asosida o'quvchining o'zlashtirish foizi aniqlanadi. O'zlashtirish $60\%$ dan past bo'lsa, mavzu *"Zaif nuqta (Knowledge Gap)"* deb belgilanadi.
- **Moslashuvchan (Adaptiv) imtihon:** Yakuniy BSB/CHSB generatsiya qilinganda savollarning $60\%$ qismi aynan o'quvchining zaif mavzulariga qaratilgan holda tanlanadi.
- **Rasch Psixometrik Modeli:** Har bir savol o'z qiyinchilik parametri ($b_i$) va vazniga ega bo'lib, o'quvchining haqiqiy intellektual qobiliyatini adolatli o'lchaydi.

### 2. O'qituvchilar Uchun Aqlli Jurnal & Tahlil (Dashboard)
- Kundalik formativ baholarni tezkor kiritish va o'zlashtirishni qayta hisoblash;
- Formativ ko'rsatkichlar asosida kutilayotgan summativ bahoni ($\hat{Y}_{BSB}$) oldindan prognozlash;
- Interaktiv **Chart.js** grafiklari: Sinf bo'yicha eng ko'p oqsayotgan "Qizil mavzular" va o'quvchilarning prognoz/haqiqiy natijalari korrelyatsiyasi.

### 3. Gamifikatsiya va Summativ Imtihonga Ruxsat (Dopusk)
- Kundalik vazifa va testlar uchun **EduCoin**, **XP** va **Streak** berish;
- Sinf va maktab reytingi (**Leaderboard**);
- **Dopusk tizimi:** Agar o'quvchining formattiv balli yoki coinlari yetarli bo'lmasa, summativ imtihonga kirish cheklanadi;
- Yig'ilgan coinlar evaziga yakuniy imtihonga **+5%** yoki **+10%** bonus berish imkoniyati.

---

## 🚀 Loyihani Ishga Tushirish

### 1. Terminal orqali papkaga o'tish:
```bash
cd /Users/techstore/Desktop/yangi_loyiha_noyabr
```

### 2. Virtual muhitni faollashtirish:
```bash
source venv/bin/activate
```

### 3. Serverni ishga tushirish:
```bash
python manage.py runserver
```

Brauzerda ochish: **http://127.0.0.1:8000/**

---

## 👥 Demo Foydalanuvchilar (Boshlang'ich Ma'lumotlar)

| Foydalanuvchi | Rol | Holati / Xususiyati | Parol |
|---|---|---|---|
| `muallim` | O'qituvchi | Barcha o'quvchilarni monitoring qiladi, jurnal yuritadi | `parol123` |
| `azizbek` | O'quvchi | A'lochi profil (95 coin, zaif mavzusi yo'q) | `parol123` |
| `madina` | O'quvchi | 3-mavzuda (Algoritmlar) zaif nuqtasi bor profil | `parol123` |
| `jasur` | O'quvchi | Dopusk chegara holatidagi profil (<40 coin) | `parol123` |
| `admin` | Superadmin | Django Admin paneliga to'liq kirish | `admin123` |

---

## 📂 Loyiha Tuzilmasi

- `apps/academic/` — Fanlar, mavzular va savollar banki (Rasch vaznlari bilan)
- `apps/assessment/` — Formativ baholar, test topshirish, summativ imtihon modellari
- `apps/gamification/` — EduCoinlar, XP, darajalar, nishonlar va Dopusk qoidalari
- `apps/analytics/` — Adaptiv savollar tanlash, prognozlash formulalari va Chart.js servislar
- `apps/accounts/` — O'qituvchi va o'quvchi rollari profillari
- `templates/` — Zamonaviy TailwindCSS + FontAwesome + Chart.js shablonlari

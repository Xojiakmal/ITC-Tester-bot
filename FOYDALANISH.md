# ITTestBot — Foydalanish qo'llanmasi

> Bu qo'llanma **ikkita qismdan** iborat: **Telegram bot** (o'qituvchi/tutor/guruh egasi uchun) va **Admin panel / sayt** (tizim administratori uchun).

---

## Mundarija

1. [Umumiy ma'lumot](#1-umumiy-malumot)
2. [A qism — Telegram botdan foydalanish](#a-qism--telegram-botdan-foydalanish)
   - [Ro'yxatdan o'tish](#21-royxatdan-otish)
   - [Kirish](#22-kirish)
   - [Shaxsiy kabinet](#23-shaxsiy-kabinet)
   - [Guruhlarim va guruh qo'shish](#24-guruhlarim-va-guruh-qoshish)
   - [Savollarim](#25-savollarim)
   - [Jadvallar](#26-jadvallar)
   - [Sozlamalar](#27-sozlamalar)
   - [Bildirishnomalar](#28-bildirishnomalar)
3. [B qism — Admin panel (sayt)](#b-qism--admin-panel-sayt)
   - [Kirish (2FA)](#31-kirish-2fa-bilan)
   - [Dashboard](#32-dashboard)
   - [Users (Foydalanuvchilar)](#33-users-foydalanuvchilar)
   - [Groups (Guruhlar)](#34-groups-guruhlar)
   - [Questions (Savollar)](#35-questions-savollar)
   - [Schedules (Jadvallar)](#36-schedules-jadvallar)
   - [Audit Log](#37-audit-log)
   - [Chiqish](#38-chiqish)
4. [Limitlar va qoidalar](#4-limitlar-va-qoidalar)
5. [Ko'p beriladigan savollar (FAQ)](#5-kop-beriladigan-savollar-faq)
6. [Administrator uchun texnik eslatmalar](#6-administrator-uchun-texnik-eslatmalar)

---

## 1. Umumiy ma'lumot

**ITTestBot** — bu Telegram guruhlariga test savollarini (native quiz so'rovnomalar) belgilangan jadval bo'yicha **avtomatik yuboradigan** tizim. Tizim ikki qismdan iborat:

| Qism | Kim uchun | Nima qiladi |
| :--- | :--- | :--- |
| **Telegram bot** | O'qituvchi / tutor / guruh egasi | Ro'yxatdan o'tish, guruh ulash, savol va to'plam yaratish, jadval sozlash |
| **Admin panel (sayt)** | Tizim administratori | Foydalanuvchi, guruh, savol va jadvallarni nazorat qilish, audit jurnal |

Ikkalasi **bitta** ilova ichida bir vaqtda ishlaydi: bot uzluksiz so'rovlarni qabul qiladi, sayt esa brauzer orqali boshqariladi.

Asosiy tushunchalar:

- **Guruh** — bot ulangan Telegram guruhi (supergroup yoki group).
- **Savol** — bitta quiz: matn + 2..10 ta variant + bitta to'g'ri javob (+ ixtiyoriy tushuntirish).
- **Test to'plami** — savollarni mavzular bo'yicha guruhlash uchun to'plam.
- **Jadval** — qaysi guruhga, qaysi to'plamdan, qaysi vaqtda, nechta savol yuborilishini belgilovchi qoida.

---

## A qism — Telegram botdan foydalanish

### 2.1 Ro'yxatdan o'tish

1. Botga o'ting va **`/start`** buyrug'ini yuboring.
2. **📝 Ro'yxatdan o'tish** tugmasini bosing.
3. **Foydalanuvchi nomi (username)** ni kiriting:
   - 3 tadan 32 tagacha belgi;
   - faqat lotin harflari, raqamlar va pastki chiziq (`_`);
   - band bo'lsa, boshqa nom tanlash so'raladi.
4. **Parol** kiriting:
   - kamida **10 belgi**;
   - oddiy/oson parollar (masalan `1234567890`, `password`) qabul qilinmaydi.
   - ⚠️ Parol yozilgan xabar **darhol o'chiriladi** (xavfsizlik uchun).
5. Parolni qayta kiriting (tasdiqlash).
6. Muvaffaqiyatli ro'yxatdan so'ng avtomatik ravishda **shaxsiy kabinetga** kirasiz.

> **Muhim:** 1 ta Telegram hisobi = 1 ta ITTestBot hisobi. Hisob Telegram ID'ga doimiy bog'lanadi.

### 2.2 Kirish

1. **🔑 Kirish** tugmasini bosing.
2. Username va parolni kiriting.
3. Parol faqat **shu Telegram hisobidan** kiritilsa qabul qilinadi (boshqa hisobdan kirish mumkin emas).

**Xavfsizlik:** ketma-ket noto'g'ri urinishlar bo'lsa, tizim vaqtincha bloklaydi (eksponensial sekinlashtirish). Bloklangan hisob bilan kirish mumkin emas — administrator blokni ochishi kerak.

### 2.3 Shaxsiy kabinet

`/start` yoki kabinetga qaytganda quyidagi bo'limlar ko'rinadi:

| Tugma | Vazifasi |
| :--- | :--- |
| 👥 **Guruhlarim** | Ulangan guruhlar ro'yxati va boshqaruvi |
| ➕ **Guruh qo'shish** | Yangi guruh ulash uchun kod olish |
| ❓ **Savollarim** | Savollar, to'plamlar, CSV import |
| 🗓 **Jadvallar** | Avtomatik yuborish jadvallari |
| ⚙️ **Sozlamalar** | Vaqt mintaqasi, parol, sessiyalar, hisob |
| 🚪 **Chiqish** | Tizimdan chiqish |

### 2.4 Guruhlarim va guruh qo'shish

#### Guruhni ulash tartibi

1. **➕ Guruh qo'shish** tugmasini bosing — bot **15 daqiqa** amal qiladigan va **faqat bir marta** ishlatiladigan kod beradi. Kod ikki ko'rinishda bo'ladi:
   ```
   /join@BotUsername <kod>
   ```
   yoki oddiy:
   ```
   /join <kod>
   ```
2. Botni guruhingizga qo'shing va uni **Administrator** qilib tayinlang.
   > ⚠️ **Diqqat:** guruhda botdan so'rovnoma yuborilishi uchun bot **albatta admin** bo'lishi kerak. Telegram'da admin huquqlari ro'yxatida alohida "Send Polls" bandi yo'q — admin bo'lgan bot so'rovnoma yuborishga doim haqli.
3. **Kodning egasi** (siz) guruh ichida yuqoridagi buyruqni yuboring. Kod egasi bilan yuboruvchi mos kelishi shart.
4. Muvaffaqiyatli ulanishda guruhda qisqa tasdiq chiqadi va sizga **shaxsiy xabarnoma** keladi.

Kod bilan bog'liq xatolar:

| Xabar | Sababi |
| :--- | :--- |
| ❌ Kod yaroqsiz yoki muddati tugagan | Kod 15 daqiqadan oshgan yoki allaqachon ishlatilgan |
| ❌ Siz kod egasi emassiz | Kodni boshqa odam yubordi |
| ❌ Bu guruh allaqachon ulangan | Guruh boshqa foydalanuvchiga bog'langan |
| ❌ Bot bu guruhda Administrator emas! | Botni admin qilmagansiz |

#### Guruh kartasi (Guruhlarim → guruhni tanlang)

- Holati (🟢 Faol / 🔴 Nofaol), guruh ID, so'rovnoma yuborish ruxsati, faol jadvallar soni ko'rsatiladi.
- **🗓 Guruh jadvallari** — shu guruhga tegishli jadvallarga o'tish.
- **⏸ Barcha jadvallarni to'xtatish** / **▶️ Barcha jadvallarni yoqish** — guruhdagi barcha jadvallarni birdan pauza/qayta yoqish.
- **🗑 Guruhni uzish** — guruhni hisobdan uzadi. ⚠️ Uning **barcha jadvallari o'chiriladi**.

### 2.5 Savollarim

Bo'limda: **➕ Savol qo'shish**, **📋 Savollar ro'yxati**, **📁 Test to'plamlari**, **📥 CSV dan yuklash**, **📄 CSV shablonini olish**.

#### Savol qo'shish (5 qadam)

1. **Savol matni** — maksimal **300 belgi**.
2. **Variantlar** — har biri **alohida qatorda**, **2 tadan 10 tagacha**, har biri maksimal **100 belgi**:
   ```
   Python
   Java
   C++
   JavaScript
   ```
3. **To'g'ri javob** — raqamli tugmalardan birini tanlang.
4. **Tushuntirish** — ixtiyoriy, maksimal **200 belgi** yoki **⏭ O'tkazib yuborish**.
5. **Test to'plami** — mavjud to'plamdan birini tanlang yoki **📂 To'plamsiz (Umumiy)**.

So'ng **✅ Savol muvaffaqiyatli saqlandi!** xabari chiqadi.

#### Savollar ro'yxati

- Har sahifada **5 ta** savol, **⬅️ Oldingi / Keyingi ➡️** bilan varaqlash.
- Savol ustiga bosib **tafsilot**: variantlar (to'g'ri javob belgilangan), tushuntirish va to'plam ko'rinadi.
- **🗑 Savolni o'chirish** tugmasi bor.
- **🔍 Qidirish** — savol matni bo'yicha qidiruv.
- ⚠️ Botda savolni **tahrirlash** yo'q; tahrirlash **Admin panel**da mumkin (pastga qarang).

#### Test to'plamlari

- **➕ Yangi to'plam yaratish** — nom (maksimal 100 belgi).
- **📁** tugmasi orqali to'plam kartasi: nom, tavsif, savollar soni.
- **🗑 To'plamni o'chirish** — to'plam o'chadi, lekin **savollar saqlanib qoladi**.

#### CSV orqali ommaviy yuklash

1. **📥 CSV dan yuklash** tugmasini bosing va `.csv` faylni botga yuboring.
2. Fayl formati (vergul yoki nuqta-vergul bilan ajratilgan):
   ```
   question,option1,option2,option3,option4,correct_option,explanation,set_name
   ```
   - `correct_option` — **1 dan boshlanuvchi** raqam yoki variant matni.
   - Namuna olish uchun **📄 CSV shablonini olish** tugmasidan foydalaning.

Natijada: **✅ `<count>` ta savol muvaffaqiyatli yuklandi!**

### 2.6 Jadvallar

Bu bo'limda testlarni guruhlarga avtomatik yuborish vaqtlari boshqariladi.

#### Yangi jadval yaratish

1. **➕ Yangi jadval yaratish** (avval kamida bitta guruh ulangan bo'lishi kerak).
2. **Nom** — masalan `Ertalabki test` (maksimal 100 belgi).
3. **Guruh** — jadval qaysi guruhga tegishli.
4. **To'plam** — savollar qaysi to'plamdan olinadi (yoki **🌐 Barcha savollarimdan**).
5. **Turi**:
   - **🔄 Har haftalik (takroriy)** — hafta kunlari tanlanadi (kerakli kunlarni belgilang, kamida bittasi, so'ng **✅ Tayyor**).
   - **⏰ Bir martalik** — sana kiritiladi (`YYYY-MM-DD`, masalan `2026-10-20`).
6. **Vaqt** — `HH:MM`, **sizning vaqt mintaqangiz** bo'yicha (masalan `09:30`).
7. **Savollar soni** — 1 dan 10 gacha (har bir yuborishda nechta savol).
8. **Tartib**:
   - **🎲 Tasodifiy (takrorlanmasdan)** — savollar tasodifiy tanlanadi, to'plam tugagach qaytadan boshlanadi.
   - **🔢 Ketma-ket** — savollar ketma-ket tartibda yuboriladi.

So'ng **✅ Jadval yaratildi va faollashtirildi!**

> Variantlar (javoblar) tartibi har yuborishda **tasodifiy** aralashtiriladi — to'g'ri javob har doim bir joyda turmaydi.

#### Jadval kartasi

- Nom, guruh, to'plam, turi, vaqt, savollar soni, tartibi, holati va **keyingi yuborish vaqti** (UTC) ko'rinadi.
- **⏸ To'xtatish / ▶️ Davom ettirish** — vaqtincha pauza qilish.
- **🗑 O'chirish** — jadvalni butunlay o'chirish.

### 2.7 Sozlamalar

| Amal | Tafsilot |
| :--- | :--- |
| 🌍 **Vaqt mintaqasini o'zgartirish** | IANA nomi (masalan `Asia/Tashkent`, `Europe/Moscow`, `UTC`). Jadvallar shu vaqt bo'yicha ishlaydi. |
| 🔒 **Parolni o'zgartirish** | Eski parol → yangi parol (kamida 10 belgi) → tasdiqlash. Parol xabarlari darhol o'chiriladi. |
| 🚪 **Barcha qurilmalardan chiqish** | Barcha faol sessiyalar bekor qilinadi; qayta kirish kerak bo'ladi. |
| ⚠️ **Hisobni o'chirish** | Barcha guruhlar, savollar va jadvallar **qaytarib bo'lmas** tarzda o'chiriladi. |

### 2.8 Bildirishnomalar

Agar bot guruhdan **chiqarib yuborilsa yoki bloklansa**:

- o'sha guruhdagi barcha jadvallar avtomatik **pauza** qilinadi;
- sizga shaxsiy xabarnoma yuboriladi.

---

## B qism — Admin panel (sayt)

Sayt manzili: `http://<server>:<PORT>/admin/` (standart `PORT` — `8000`; `.env` faylidagi `PORT` bilan o'zgartiriladi). Root manzil `/` avtomatik `/admin/` ga yo'naltiradi.

### 3.1 Kirish (2FA bilan)

1. `/admin/login` sahifasini oching.
2. **Username**, **Parol** va **6 xonali TOTP kodi** (authenticator ilovadan) kiritib **Login** tugmasini bosing.

> **2FA (TOTP)** majburiy. Admin CLI orqali yaratilganda chiqadigan QR kodni Google Authenticator, Aegis yoki 1Password'da skanerlang.

Noto'g'ri urinishlar IP va username bo'yicha cheklanadi (vaqtincha blok).

### 3.2 Dashboard

Asosiy ko'rsatkichlar va oxirgi 5 ta admin amali:

- **Registered Users** — ro'yxatdan o'tgan foydalanuvchilar
- **Linked Groups** — ulangan guruhlar
- **Total Questions** — savollar
- **Active Schedules** — jadvallar
- **Executed Runs** — bajarilgan yuborishlar
- **Active Sessions** — faol foydalanuvchi sessiyalari
- **Recent Admin Audit Events** — oxirgi admin harakatlari

### 3.3 Users (Foydalanuvchilar)

- **Qidirish** — username yoki Telegram ID bo'yicha.
- Har bir foydalanuvchi kartasida amallar:
  - **Block / Unblock** — bloklash (bloklanganda barcha sessiyalari bekor qilinadi) yoki blokdan chiqarish.
  - **Force logout** — barcha sessiyalarini majburiy bekor qilish.
  - **Rebind Telegram ID** — hisobni boshqa Telegram ID'ga qayta bog'lash.
  - **Delete** — foydalanuvchini butunlay o'chirish.

### 3.4 Groups (Guruhlar)

- Barcha ulangan guruhlar va ularning egasi (owner) ko'rinadi.
- **Unlink** — guruhni egasidan uzish.
- **Delete** — guruhni o'chirish.

### 3.5 Questions (Savollar)

- Matn bo'yicha **qidirish** (oxirgi 100 ta).
- **Edit** — savol matnini tahrirlash (botda bu imkon yo'q, shu yerda).
- **Delete** — savolni o'chirish.

### 3.6 Schedules (Jadvallar)

- Barcha jadvallar (egasi, guruh, to'plam bilan).
- **Toggle** — pauza qilish / qayta yoqish.
- **Delete** — o'chirish.

### 3.7 Audit Log

Oxirgi **200 ta** admin harakati: vaqt (UTC), admin, amal, obyekt turi va ID, IP manzil. Har bir o'zgartirish (bloklash, o'chirish, tahrirlash va h.k.) shu yerda qayd etiladi.

### 3.8 Chiqish

Chap paneldagi **Logout** tugmasi (CSRF bilan himoyalangan).

---

## 4. Limitlar va qoidalar

| Limit | Standart qiymat | Sozlama (.env) |
| :--- | :--- | :--- |
| Bitta foydalanuvchiga guruhlar | 20 | `MAX_GROUPS_PER_USER` |
| Bitta foydalanuvchiga savollar | 500 | `MAX_QUESTIONS_PER_USER` |
| Bitta foydalanuvchiga jadvallar | 50 | `MAX_SCHEDULES_PER_USER` |
| Savol matni | 300 belgi | — |
| Variantlar | 2..10 ta, har biri 100 belgi | — |
| Tushuntirish | 200 belgi | — |
| Join-kod amal qilish muddati | 15 daqiqa, bir martalik | — |
| Yuborishda kechikish oynasi (grace) | 10 daqiqa | `SCHEDULER_GRACE_WINDOW_SECONDS` |
| Tekshirish davri | 10 soniya | `SCHEDULER_INTERVAL_SECONDS` |
| Admin sessiyasi | 12 soat | — |

---

## 5. Ko'p beriladigan savollar (FAQ)

**❓ Bot guruhga so'rovnoma yubormayapti.**
Botni guruhda **Administrator** qilib tayinlang (Telegram'da admin uchun alohida "Send Polls" bandi yo'q — admin bo'lsa yetarli). So'ng guruhni qayta ulang.

**❓ Guruhni ulay olmayapman (`/join`).**
- Bot admin bo'lishi kerak;
- kodni **kodning egasi** yuborishi kerak;
- kod **15 daqiqa** ichida va **faqat bir marta** ishlaydi;
- guruh allaqachon boshqa hisobga ulangan bo'lmasligi kerak.

**❓ Vaqt noto'g'ri kelmoqda.**
Sozlamalar → **Vaqt mintaqasini o'zgartirish** bo'limidan to'g'ri IANA mintaqani (`Asia/Tashkent`) tanlang. Jadvallar shu vaqtga moslashadi.

**❓ Variantlar tartibi o'zgaradimi?**
Ha. Har bir so'rovnomada variantlar **tasodifiy** aralashtiriladi. Bu funksiyani o'chirish uchun administrator `.env` da `SHUFFLE_POLL_OPTIONS=false` qiladi.

**❓ Savolni bot orqali tahrirlash mumkinmi?**
Yo'q. Tahrirlash **Admin panel → Questions** bo'limida bajariladi. Botda faqat ko'rish va o'chirish bor.

**❓ Parolimni unutdim.**
Botda avtomatik tiklash yo'q. Administrator bilan bog'laning yoki hisobni o'chirib (`Sozlamalar → Hisobni o'chirish`), qaytadan ro'yxatdan o'ting.

**❓ "Tasodifiy (takrorlanmasdan)" qanday ishlaydi?**
Savollar to'plamdan takrorlanmasdan tanlanadi. To'plam tugagach, tarix tozalanadi va sikl qaytadan boshlanadi.

**❓ Bot guruhdan chiqarib yuborilsa nima bo'ladi?**
Guruh nofaol bo'ladi, barcha jadvallari pauza qilinadi va sizga shaxsiy xabar keladi.

---

## 6. Administrator uchun texnik eslatmalar

**Birinchi adminni yaratish:**
```bash
# Lokal:
python -m app.cli create-admin --username admin

# Docker:
docker compose exec app python -m app.cli create-admin --username admin
```
Chiqadigan **TOTP secret** va **QR kodni** saqlab qo'ying — ular admin panelga kirish uchun kerak.

**Ishga tushirish:**
```bash
python -m app.main            # bot + sayt birga
```

**Muhim `.env` sozlamalari:**

| Sozlama | Izoh |
| :--- | :--- |
| `BOT_TOKEN` | BotFather bergan token |
| `SECRET_KEY`, `JOIN_CODE_PEPPER` | Tasodifiy, 64 belgi (xavfsizlik kalitlari) |
| `PORT` | Sayt tashqi porti (standart 8000) |
| `COOKIE_SECURE` | HTTPS'da `true`, lokal HTTP'da `false` bo'lishi kerak |
| `WEBHOOK_URL` | Bo'sh — polling rejimi; to'ldirilsa — webhook rejimi |
| `SHUFFLE_POLL_OPTIONS` | `true` — variantlar tasodifiy tartibda |

> ⚠️ `COOKIE_SECURE=true` bo'lsa, sayt brauzerda **faqat HTTPS** orqali ishlaydi. Lokal `http://` da kirish uchun `false` qiling, aks holda admin sessiya cookie'si saqlanmaydi.

**Docker bilan ishga tushirish:**
```bash
docker compose up -d --build
```

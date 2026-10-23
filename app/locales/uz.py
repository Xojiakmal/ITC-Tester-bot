"""Uzbek localization dictionary for ITTestBot.

All user-facing bot messages and button labels in Uzbek (Latin script).
"""

STRINGS = {
    # Auth & Start
    "welcome_guest": (
        "Assalomu alaykum! ITTestBot tizimiga xush kelibsiz.\n\n"
        "Ushbu bot orqali Telegram guruhlaringizga test savollarini reja asosida avtomatik yuborishingiz mumkin.\n\n"
        "Davom etish uchun tizimga kiring yoki ro'yxatdan o'ting:"
    ),
    "btn_login": "🔑 Kirish",
    "btn_register": "📝 Ro'yxatdan o'tish",
    "btn_cancel": "❌ Bekor qilish",
    "btn_back": "⬅️ Orqaga",
    "action_cancelled": "Amal bekor qilindi.",

    # Registration
    "reg_enter_username": (
        "Foydalanuvchi nomini (username) kiriting:\n"
        "• 3 tadan 32 tagacha belgi\n"
        "• Faqat lotin harflari, raqamlar va pastki chiziq (_)"
    ),
    "reg_username_invalid": (
        "Foydalanuvchi nomi noto'g'ri formatda. Faqat 3-32 ta lotin harfi, raqam va pastki chiziqdan foydalaning."
    ),
    "reg_username_taken": "Ushbu foydalanuvchi nomi band. Boshqa nom tanlang:",
    "reg_enter_password": (
        "Yangi parolingizni kiriting:\n"
        "• Kamida 10 ta belgi\n"
        "• Oddiy yoki oson parollar qabul qilinmaydi"
    ),
    "reg_password_too_short": "Parol kamida 10 ta belgidan iborat bo'lishi kerak.",
    "reg_password_too_common": "Bu parol juda oddiy va xavfsiz emas. Murakkabroq parol tanlang:",
    "reg_confirm_password": "Parolni tasdiqlash uchun uni qayta kiriting:",
    "reg_passwords_mismatch": "Kiritilgan parollar bir-biriga mos kelmadi. Ro'yxatdan o'tish bekor qilindi.",
    "reg_success": "Tabriklaymiz! Siz muvaffaqiyatli ro'yxatdan o'tdingiz va shaxsiy kabinetingizga kirdingiz.",
    "reg_already_have_account": "Ushbu Telegram hisobi allaqachon ro'yxatdan o'tgan. Iltimos, 'Kirish' tugmasini bosing.",

    # Login
    "login_enter_username": "Foydalanuvchi nomingizni kiriting:",
    "login_enter_password": "Parolingizni kiriting:",
    "login_invalid_credentials": "Login yoki parol noto'g'ri.",
    "login_throttled": "Haddan tashqari ko'p urinish. Iltimos, {seconds} soniyadan keyin qayta urinib ko'ring.",
    "login_account_blocked": "Sizning hisobingiz administrator tomonidan bloklangan.",
    "login_wrong_telegram_account": "Ushbu hisob boshqa Telegram foydalanuvchisiga biriktirilgan.",
    "login_success": "Xush kelibsiz! Shaxsiy kabinetingizga muvaffaqiyatli kirdingiz.",

    # Cabinet Main Menu
    "cabinet_welcome": (
        "🏠 Shaxsiy Kabinet\n\n"
        "Foydalanuvchi: <b>{username}</b>\n"
        "Vaqt mintaqasi: <b>{timezone}</b>\n\n"
        "Kerakli bo'limni tanlang:"
    ),
    "btn_menu_groups": "👥 Guruhlarim",
    "btn_menu_add_group": "➕ Guruh qo'shish",
    "btn_menu_questions": "❓ Savollarim",
    "btn_menu_schedules": "🗓 Jadvallar",
    "btn_menu_settings": "⚙️ Sozlamalar",
    "btn_menu_logout": "🚪 Chiqish",

    # Groups
    "groups_list_title": "👥 <b>Sizning guruhlaringiz:</b>\n\n",
    "groups_empty": "Siz hali hech qanday guruh qo'shmagansiz. '➕ Guruh qo'shish' tugmasi orqali yangi guruh ulang.",
    "group_item": "• <b>{title}</b> ({status})\n",
    "group_status_active": "🟢 Faol",
    "group_status_inactive": "🔴 Nofaol",
    "group_detail": (
        "📌 <b>Guruh:</b> {title}\n"
        "Holati: {status}\n"
        "Guruh ID: <code>{chat_id}</code>\n"
        "So'rovnoma yuborish ruxsati: {polls_permission}\n"
        "Faol jadvallar soni: {schedules_count}"
    ),
    "btn_group_schedules": "🗓 Guruh jadvallari",
    "btn_group_pause_all": "⏸ Barcha jadvallarni to'xtatish",
    "btn_group_resume_all": "▶️ Barcha jadvallarni yoqish",
    "btn_group_unlink": "🗑 Guruhni uzish (ajratish)",
    "group_unlink_confirm": "Rostdan ham ushbu guruhni uzmoqchimisiz? Guruhga tegishli barcha jadvallar o'chiriladi.",
    "btn_confirm": "✅ Tasdiqlash",
    "group_unlinked_success": "Guruh muvaffaqiyatli uzildi.",
    "group_quota_exceeded": "Siz guruhlar limiti ({limit}) ga yetgansiz. Yangi guruh qo'sha olmaysiz.",

    # Add Group & Join Codes
    "add_group_instructions": (
        "➕ <b>Guruhni botga ulash bo'yicha ko'rsatma:</b>\n\n"
        "1. Botni guruhingizga qo'shing va unga <b>Admin</b> huquqini (ayniqsa, <i>So'rovnomalar yuborish</i> ruxsatini) bering.\n"
        "2. Guruhingizga quyidagi buyruqni yuboring:\n\n"
        "<code>{command}</code>\n\n"
        "yoki oddiygina:\n"
        "<code>/join {code}</code>\n\n"
        "⏳ Ushbu kod <b>15 daqiqa</b> davomida amal qiladi va faqat bir marta ishlatiladi."
    ),
    "join_success_group": "✅ Ushbu guruh muvaffaqiyatli ITTestBot tizimiga ulandi!",
    "join_success_private": "🎉 <b>{title}</b> guruhi kabinetingizga muvaffaqiyatli ulandi!",
    "join_code_invalid": "❌ Join-kod yaroqsiz yoki muddati tugagan.",
    "join_not_owner": "❌ Siz ushbu join-kodning egasi emassiz.",
    "join_group_already_linked": "❌ Bu guruh allaqachon boshqa foydalanuvchiga ulangan.",
    "join_must_be_admin": (
        "❌ <b>Bot bu guruhda Administrator emas!</b>\n\n"
        "Guruhni botga ulash uchun avval botni guruhga <b>Admin</b> qilib tayinlang va unga <b>So'rovnomalar yuborish (Send Polls)</b> huquqini bering.\n"
        "Shundan so'ng qaytadan <code>/join &lt;kod&gt;</code> buyrug'ini yuboring."
    ),
    "join_missing_permissions": (
        "❌ Bot bu guruhda so'rovnoma yuborish ruxsatiga ega emas.\n"
        "Iltimos, guruh admin sozlamalarida botga <b>So'rovnomalar yuborish (Send Polls)</b> huquqini bering!"
    ),
    "join_throttled": "❌ Juda ko'p muvaffaqiyatsiz urinishlar. Iltimos, keyinroq qayta urinib ko'ring.",

    # Questions & Sets
    "questions_menu_title": (
        "❓ <b>Savollar va to'plamlar bo'limi</b>\n\n"
        "Jami savollaringiz: <b>{questions_count}</b> ta\n"
        "To'plamlaringiz: <b>{sets_count}</b> ta\n\n"
        "Quyidagi amallardan birini tanlang:"
    ),
    "btn_add_question": "➕ Savol qo'shish",
    "btn_list_questions": "📋 Savollar ro'yxati",
    "btn_test_sets": "📁 Test to'plamlari",
    "btn_import_csv": "📥 CSV dan yuklash",
    "btn_csv_template": "📄 CSV shablonini olish",

    # Add Question Flow
    "add_q_enter_text": (
        "1-qadam: Savol matnini kiriting (maksimal 300 ta belgi):"
    ),
    "add_q_text_too_long": "Savol matni 300 belgidan oshmasligi kerak. Qayta kiriting:",
    "add_q_enter_options": (
        "2-qadam: Variantlarni har birini alohida qatorda kiriting (2 tadan 10 tagacha variant, har biri maksimal 100 belgi):\n\n"
        "Masalan:\n"
        "Python\n"
        "Java\n"
        "C++\n"
        "JavaScript"
    ),
    "add_q_options_invalid": "Variantlar soni 2 dan 10 gacha va har biri 100 belgidan oshmasligi kerak. Qaytadan kiriting:",
    "add_q_select_correct": "3-qadam: To'g'ri javob variantini tanlang:",
    "add_q_enter_explanation": (
        "4-qadam: Savol uchun tushuntirish kiriting (ixtiyoriy, maksimal 200 belgi). "
        "Agar tushuntirish kiritmoqchi bo'lmasangiz, 'O'tkazib yuborish' tugmasini bosing:"
    ),
    "btn_skip": "⏭ O'tkazib yuborish",
    "add_q_explanation_too_long": "Tushuntirish 200 belgidan oshmasligi kerak. Qayta kiriting:",
    "add_q_select_set": "5-qadam: Savol qaysi to'plamga tegishli bo'lsin?",
    "btn_no_set": "📂 To'plamsiz (Umumiy)",
    "add_q_success": "✅ Savol muvaffaqiyatli saqlandi!",
    "question_quota_exceeded": "Siz savollar limiti ({limit}) ga yetgansiz. Yangi savol qo'sha olmaysiz.",

    # Questions List & Pagination & Search
    "questions_list_header": "📋 <b>Savollaringiz (Sahifa {page}/{total_pages}):</b>\n\n",
    "question_item_short": "{index}. {text}\n",
    "btn_prev_page": "⬅️ Oldingi",
    "btn_next_page": "Keyingi ➡️",
    "btn_search_questions": "🔍 Qidirish",
    "search_enter_query": "Qidirilayotgan so'zni kiriting:",
    "question_detail": (
        "❓ <b>Savol:</b> {text}\n\n"
        "<b>Variantlar:</b>\n{options_text}\n"
        "To'g'ri javob: <b>{correct_option}</b>\n"
        "Tushuntirish: <i>{explanation}</i>\n"
        "To'plam: <b>{set_name}</b>"
    ),
    "btn_delete_question": "🗑 Savolni o'chirish",
    "btn_edit_question": "✏️ Tahrirlash",
    "question_deleted": "Savol o'chirildi.",

    # Test Sets
    "sets_list_title": "📁 <b>Test to'plamlari:</b>\n\n",
    "sets_empty": "Sizda hali test to'plamlari yo'q.",
    "btn_create_set": "➕ Yangi to'plam yaratish",
    "set_item": "• <b>{name}</b> ({count} ta savol)\n",
    "create_set_enter_name": "Yangi test to'plami nomini kiriting (maksimal 100 belgi):",
    "create_set_success": "✅ Test to'plami yaratildi!",
    "set_detail": (
        "📁 <b>To'plam:</b> {name}\n"
        "Tavsif: {description}\n"
        "Savollar soni: {count} ta"
    ),
    "btn_delete_set": "🗑 To'plamni o'chirish",
    "set_deleted": "Test to'plami o'chirildi (savollar saqlab qolindi).",

    # CSV Import
    "csv_import_prompt": (
        "📥 <b>CSV fayl orqali savollarni ommaviy yuklash:</b>\n\n"
        "Savollarni o'z ichiga olgan <code>.csv</code> faylni botga yuboring.\n\n"
        "Fayl formati (ustunlar vergul yoki nuqta-vergul bilan ajratilgan bo'lishi kerak):\n"
        "<code>question,option1,option2,option3,option4,correct_option,explanation,set_name</code>\n\n"
        "<i>Eslatma: correct_option 1 dan boshlanuvchi raqam yoki variant matni bo'lishi mumkin.</i>"
    ),
    "csv_template_text": (
        "question,option1,option2,option3,option4,correct_option,explanation,set_name\n"
        "Python qaysi yilda yaratilgan?,1991,2000,1985,1995,1,Gvido van Rossum tomonidan 1991-yilda chiqarilgan,Dasturlash\n"
        "Qaysi biri mantiqiy tur?,bool,int,str,float,1,bool true/false qiymat oladi,Dasturlash"
    ),
    "csv_import_success": "✅ CSV fayl qabul qilindi. <b>{count}</b> ta savol muvaffaqiyatli yuklandi!",
    "csv_import_error": "❌ CSV faylni o'qishda xatolik yuz berdi:\n{error}",

    # Schedules
    "schedules_menu_title": (
        "🗓 <b>Jadvallar bo'limi</b>\n\n"
        "Bu yerda test savollarini guruhlarga avtomatik yuborish vaqtlarini boshqarishingiz mumkin.\n\n"
        "Mavjud jadvallaringiz: <b>{count}</b> ta"
    ),
    "schedules_empty": "Sizda hali rejalashtirilgan jadvallar yo'q.",
    "btn_add_schedule": "➕ Yangi jadval yaratish",
    "schedule_item": "• <b>{name}</b> ({status}) -> {group_title} ({time_info})\n",
    "schedule_detail": (
        "🗓 <b>Jadval:</b> {name}\n"
        "Guruh: <b>{group_title}</b>\n"
        "To'plam: <b>{set_name}</b>\n"
        "Turi: <b>{schedule_type}</b>\n"
        "Vaqt: <b>{time_info}</b>\n"
        "Bir martada yuboriladigan savollar: <b>{count}</b> ta\n"
        "Tartibi: <b>{order_mode}</b>\n"
        "Holati: <b>{status}</b>\n"
        "Keyingi yuborish: <b>{next_run}</b>"
    ),
    "btn_pause_schedule": "⏸ To'xtatish",
    "btn_resume_schedule": "▶️ Davom ettirish",
    "btn_delete_schedule": "🗑 O'chirish",
    "schedule_deleted": "Jadval o'chirildi.",
    "schedule_quota_exceeded": "Siz jadvallar limiti ({limit}) ga yetgansiz. Yangi jadval yarata olmaysiz.",

    # Add Schedule Flow
    "add_sched_enter_name": "1-qadam: Jadval nomini kiriting (masalan, 'Ertalabki test'):",
    "add_sched_select_group": "2-qadam: Jadval qaysi guruhga tegishli bo'lsin?",
    "add_sched_no_groups": "Sizda hali ulangan guruhlar yo'q. Avval 'Guruh qo'shish' orqali guruh ulang.",
    "add_sched_select_set": "3-qadam: Qaysi test to'plamidan savollar yuborilsin?",
    "btn_all_questions": "🌐 Barcha savollarimdan",
    "add_sched_select_type": "4-qadam: Jadval turini tanlang:",
    "btn_type_recurring": "🔄 Har haftalik (takroriy)",
    "btn_type_one_time": "⏰ Bir martalik",
    "add_sched_select_days": "Haftaning qaysi kunlarida yuborilsin? (Kerakli kunlarni belgilang va 'Tayyor' tugmasini bosing):",
    "btn_day_done": "✅ Tayyor",
    "days_names": ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"],
    "add_sched_enter_time": "Yuborilish vaqtini kiriting (HH:MM formatida, sizning vaqtingiz bo'yicha: {timezone}):\nMasalan: 09:30 yoki 18:00",
    "add_sched_enter_date": "Bir martalik test sanasini kiriting (YYYY-MM-DD formatida):\nMasalan: 2026-10-20",
    "add_sched_enter_count": "Har bir yuborishda nechta savol yuborilsin? (1 dan 10 gacha son kiriting):",
    "add_sched_select_order": "Savollar tartibini tanlang:",
    "btn_order_random": "🎲 Tasodifiy (takrorlanmasdan)",
    "btn_order_sequential": "🔢 Ketma-ket",
    "add_sched_success": "✅ Jadval muvaffaqiyatli yaratildi va faollashtirildi!",

    # Settings
    "settings_title": (
        "⚙️ <b>Sozlamalar</b>\n\n"
        "Foydalanuvchi: <b>{username}</b>\n"
        "Vaqt mintaqasi: <b>{timezone}</b>\n\n"
        "Kerakli amalni tanlang:"
    ),
    "btn_change_timezone": "🌍 Vaqt mintaqasini o'zgartirish",
    "btn_change_password": "🔒 Parolni o'zgartirish",
    "btn_logout_everywhere": "🚪 Barcha qurilmalardan chiqish",
    "btn_delete_account": "⚠️ Hisobni o'chirish",
    "tz_enter_name": "Yangi IANA vaqt mintaqasi nomini kiriting (masalan, Asia/Tashkent, Europe/Moscow, UTC):",
    "tz_invalid": "Noto'g'ri vaqt mintaqasi. Iltimos, haqiqiy IANA mintaqasini kiriting (masalan, Asia/Tashkent).",
    "tz_updated": "✅ Vaqt mintaqasi muvaffaqiyatli yangilandi: {timezone}",
    "chpass_enter_old": "Hozirgi parolingizni kiriting:",
    "chpass_old_wrong": "Hozirgi parol noto'g'ri.",
    "chpass_enter_new": "Yangi parolingizni kiriting (kamida 10 belgi):",
    "chpass_confirm_new": "Yangi parolni qayta kiriting:",
    "chpass_success": "✅ Parol muvaffaqiyatli yangilandi!",
    "logout_everywhere_confirm": "Rostdan ham barcha faol sessiyalardan chiqmoqchimisiz?",
    "logout_everywhere_done": "Barcha sessiyalar bekor qilindi. Qayta kirishingiz kerak bo'ladi.",
    "delete_account_confirm": (
        "⚠️ <b>DIQQAT:</b> Hisobingizni o'chirish barcha guruhlaringiz, savollaringiz va jadvallaringizni qaytarib bo'lmas tarzda o'chiradi!\n\n"
        "Haqiqatan ham hisobingizni o'chirmoqchimisiz?"
    ),
    "delete_account_done": "Sizning hisobingiz to'liq o'chirildi. Xayr!",
    "logout_done": "Tizimdan chiqdingiz.",

    # Notifications
    "notify_group_kicked": (
        "⚠️ <b>Guruh xabarnomasi:</b>\n\n"
        "Bot <b>{title}</b> guruhidan chiqarib yuborildi yoki bloklandi. "
        "Ushbu guruhdagi barcha jadvallar vaqtincha to'xtatildi."
    ),
}


def t(key: str, **kwargs) -> str:
    """Translate key with formatted kwargs."""
    template = STRINGS.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template

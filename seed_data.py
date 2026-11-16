import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.accounts.models import Profile
from apps.academic.models import Subject, Topic, Question
from apps.gamification.models import StudentReward, Badge, StudentBadge, ExamDopuskRule
from apps.assessment.models import FormativeGrade, QuizAttempt, StudentTopicMastery
from apps.analytics.services import update_student_topic_mastery, predict_summative_score

print("--- SEED DATA YARATILMOQDA ---")

# 1. Users
def get_or_create_user(username, first_name, last_name, role='STUDENT', grade='9-A'):
    user, created = User.objects.get_or_create(username=username, defaults={
        'first_name': first_name,
        'last_name': last_name,
        'email': f"{username}@maktab.uz"
    })
    user.set_password('parol123')
    user.save()
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.grade_level = grade
    profile.save()
    return user

teacher = get_or_create_user('muallim', 'Rustam', 'Oripov', role='TEACHER')
student1 = get_or_create_user('azizbek', 'Azizbek', 'Karimov', role='STUDENT')
student2 = get_or_create_user('madina', 'Madina', 'Rahimova', role='STUDENT')
student3 = get_or_create_user('jasur', 'Jasur', 'Bekmurodov', role='STUDENT')
student4 = get_or_create_user('shahnoza', 'Shahnoza', 'Aliyeva', role='STUDENT')

# Superadmin
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'first_name': 'Super', 'last_name': 'Admin', 'email': 'admin@maktab.uz'})
admin_user.set_password('admin123')
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.save()
admin_profile, _ = Profile.objects.get_or_create(user=admin_user)
admin_profile.role = 'TEACHER'
admin_profile.save()

print("Foydalanuvchilar tayyor.")

# 2. Subject
subject, _ = Subject.objects.get_or_create(
    code='INF-9',
    defaults={
        'name': 'Informatika va Axborot Texnologiyalari (9-sinf)',
        'description': "Zamonaviy algoritmlash, Python dasturlash va tarmoq xavfsizligi fani"
    }
)

# 3. Topics
topics_data = [
    (1, "Axborot xavfsizligi va kriptografiya", "Axborotni himoyalash usullari, parollar va shifrlash asoslari."),
    (2, "Kompyuter tarmoqlari va topologiyalari", "Lokal va global tarmoqlar, router, switch va IP manzillar."),
    (3, "Algoritmlash va blok-sxemalar", "Chiziqli, tarmoqlanuvchi va takrorlanuvchi algoritmlar."),
    (4, "Python: Ma'lumot turlari va shart operatorlari", "int, float, str turlari, if-elif-else tuzilmalari."),
    (5, "Python: Takrorlanish operatorlari (for, while)", "Sikllar, range funksiyasi va ro'yxatlar (lists)."),
]

topics = []
for order, title, desc in topics_data:
    t, _ = Topic.objects.get_or_create(subject=subject, order=order, defaults={'title': title, 'description': desc})
    topics.append(t)

print("Mavzular tayyor.")

# 4. Questions (Rasch parametrlari va Kognitiv modullar: Bilish, Qo'llash, Mulohaza yuritish)
# Format: (topic, text, A, B, C, D, correct, difficulty, rasch_b, cognitive_level, explanation)
questions_data = [
    # --- MAVZU 1: Axborot xavfsizligi va kriptografiya ---
    # Bilish (Knowledge)
    (topics[0], "Axborotning maxfiyligi deganda nima tushuniladi?", 
     "Axborotdan faqat ruxsat berilgan shaxslarning foydalanishi", "Axborotning buzilmasdan saqlanishi", "Axborotning tez yetib borishi", "Axborotning o'chib ketmasligi", 
     "A", "EASY", -1.2, "KNOWLEDGE", "Maxfiylik (Confidentiality) - faqat vakolatli foydalanuvchilar axborotdan foydalanish huquqiga ega bo'lishidir."),
    (topics[0], "Axborot xavfsizligining 3 ta asosiy tamoyili (CIA triada) qaysilar?", 
     "Maxfiylik, Butunlik, Foydalana olishlik", "Tezkorlik, Arzonlik, Qulaylik", "Antivirus, Firewall, Parol", "Server, Router, Switch", 
     "A", "EASY", -0.9, "KNOWLEDGE", "CIA triad: Confidentiality (Maxfiylik), Integrity (Butunlik), Availability (Foydalana olishlik)."),
    (topics[0], "Parolning ishonchliligini oshirish uchun qanday belgilar kombinatsiyasidan foydalanish lozim?", 
     "Katta-kichik harflar, raqamlar va maxsus belgilar", "Faqat o'z tug'ilgan yili va ismi", "Ketma-ket kelgan 123456 raqamlari", "Faqat bosh harflar", 
     "A", "EASY", -1.0, "KNOWLEDGE", "Kuchli parol kamida 8-12 belgidan iborat bo'lib, har xil registrli harflar, raqamlar va belgilarni o'z ichiga olishi kerak."),

    # Qo'llash (Application)
    (topics[0], "Simmetrik shifrlashda qanday kalit ishlatiladi?", 
     "Faqat bitta umumiy maxfiy kalit", "Ochiq va yopiq juft kalitlar", "Faqat elektron raqamli imzo", "DNS kaliti", 
     "A", "MEDIUM", 0.1, "APPLICATION", "Simmetrik shifrlashda shifrlash va deshifrlash uchun ayni bitta umumiy maxfiy kalit qo'llaniladi."),
    (topics[0], "Sezar shifrida alifbo 3 ta harfga o'ngga surilsa, 'A' harfi qaysi harfga aylanadi?", 
     "D", "B", "C", "E", 
     "A", "MEDIUM", 0.3, "APPLICATION", "Sezar algoritmi bo'yicha har bir harf k qadam suriladi. A(1) + 3 = D(4)."),
    (topics[0], "Foydalanuvchi elektron pochta orqali shubhali havola olganda uning fishing (aldov) ekanligini qanday tekshiradi?", 
     "Havola domen nomining rasmiy saytga to'liq mosligini tekshirish orqali", "Parolni kiritib ko'rish orqali", "Xatni darhol do'stlariga jo'natish orqali", "Kompyuterni o'chirib yoqish orqali", 
     "A", "MEDIUM", 0.4, "APPLICATION", "Fishing havolalari odatda soxta domenga yo'naltiradi (masalan paypa1.com)."),

    # Mulohaza yuritish (Reasoning)
    (topics[0], "Quyidagilardan qaysi biri xeshlash algoritmi hisoblanadi va nima uchun u bir tomonlama hisoblanadi?", 
     "SHA-256, chunki xesh qiymatidan asl matnni matematik tiklab bo'lmaydi", "AES-128, chunki unda kalit yo'qolmaydi", "RSA, chunki u faqat raqamlarni taniydi", "DES, chunki uning tezligi juda yuqori", 
     "A", "HARD", 1.4, "REASONING", "SHA-256 kriptografik bir tomonlama funksiya bo'lib, xeshdan boshlang'ich matnni olish imkonsiz."),
    (topics[0], "Asimmetrik shifrlashda ma'lumot jo'natuvchi xabarni kimning kaliti bilan shifrlashi kerak?", 
     "Qabul qiluvchining ochiq (public) kaliti bilan", "O'zining ochiq kaliti bilan", "Qabul qiluvchining yopiq kaliti bilan", "Tarmoq provayderi kaliti bilan", 
     "A", "HARD", 1.5, "REASONING", "Qabul qiluvchining public kaliti bilan shifrlangan ma'lumotni faqat qabul qiluvchi o'zining private kaliti bilan ocha oladi."),
    (topics[0], "Raqamli imzo qanday qilib xabarning butunligini va jo'natuvchining haqiqiyligini bir vaqtda kafolatlaydi?", 
     "Xesh qiymatini jo'natuvchining shaxsiy kaliti bilan shifrlash orqali", "Parolni ochiq holda xatga ilova qilish orqali", "Faylni arxivlab jo'natish orqali", "Faqat IP manzilni tekshirish orqali", 
     "A", "HARD", 1.6, "REASONING", "Raqamli imzo xesh va asimmetrik kriptografiya birikmasi orqali inkor etib bo'lmaslikni ta'minlaydi."),

    # --- MAVZU 2: Kompyuter tarmoqlari va topologiyalari ---
    # Bilish (Knowledge)
    (topics[1], "Kompyuter tarmoqlarida 'Yulduz' topologiyasining markaziy qurilmasi nima?", 
     "Switch (kommutator) yoki Hub", "Modem", "Server klaviaturasi", "Printer", 
     "A", "EASY", -1.0, "KNOWLEDGE", "Yulduz topologiyasida barcha tugunlar markaziy kommutatorga (switch) ulanadi."),
    (topics[1], "IPv4 manzili necha bitdan iborat?", 
     "32 bit", "64 bit", "128 bit", "16 bit", 
     "A", "EASY", -0.8, "KNOWLEDGE", "IPv4 4 ta oktetdan, ya'ni har biri 8 bitdan jami 32 bitdan iborat."),
    (topics[1], "Tarmoqda ma'lumotlar almashinuvi qoidalarini belgilovchi standart nima deb ataladi?", 
     "Tarmoq protokoli", "Drayver", "Operatsion tizim", "Kompilyator", 
     "A", "EASY", -1.1, "KNOWLEDGE", "Protokol - bu qurilmalar o'rtasidagi aloqa va ma'lumot almashish qoidalari majmui."),

    # Qo'llash (Application)
    (topics[1], "IP manzili 192.168.1.15 bo'lgan kompyuter qaysi sinf (class) tarmog'iga tegishli?", 
     "C sinf", "A sinf", "B sinf", "D sinf", 
     "A", "MEDIUM", 0.0, "APPLICATION", "192.0.0.0 dan 223.255.255.255 gacha bo'lgan manzillar C sinfiga tegishli."),
    (topics[1], "Mahalliy tarmoqdagi ikkita kompyuter orasida aloqa borligini tekshirish uchun qaysi buyruq qo'llaniladi?", 
     "ping", "ipconfig", "mkdir", "tracert", 
     "A", "MEDIUM", 0.2, "APPLICATION", "ping buyrug'i ICMP echo paketlari orqali tarmoq tugunining yetib boruvchanligini tekshiradi."),
    (topics[1], "DNS serverining asosiy amaliy vazifasi nimadan iborat?", 
     "Sayt domen nomlarini IP manzillarga aylantirib berish", "Fayllarni viruslardan tozalash", "Internet tezligini 2 barobarga oshirish", "Kompyuterni elektr bilan ta'minlash", 
     "A", "MEDIUM", 0.3, "APPLICATION", "DNS inson tushunadigan nomlarni (masalan google.com) kompyuter tushunadigan IP ga o'giradi."),

    # Mulohaza yuritish (Reasoning)
    (topics[1], "OSI modelining 7-darajasi (eng yuqori) qaysi?", 
     "Amaliy (Application) sath", "Transport sath", "Kanal sath", "Tarmoq sath", 
     "A", "HARD", 1.3, "REASONING", "Application sathi foydalanuvchi dasturlari bilan bevosita muloqot qiluvchi eng yuqori sathdir."),
    (topics[1], "Yulduz topologiyasi Shina (Bus) topologiyasiga nisbatan qanday muhim afzallikka ega?", 
     "Bitta kabel uzilsa butun tarmoq ishdan chiqmaydi, faqat o'sha kompyuter uziladi", "Umuman kabel talab qilinmaydi", "Barcha kompyuterlar bir xil tezlikda ishlay olmaydi", "Switch ishdan chiqsa ham tarmoq ishlayveradi", 
     "A", "HARD", 1.4, "REASONING", "Yulduz topologiyasida kabel uzilishi lokallashgan bo'ladi, shinada esa butun magistral to'xtaydi."),
    (topics[1], "TCP protokoli UDP ga qaraganda nima sababdan ishonchliroq hisoblanadi?", 
     "Paketlar yetib borishini tasdiqlash va yo'qolganini qayta yuborish mexanizmiga ega", "Uning tezligi UDP dan 10 barobar tez", "U faqat simsiz tarmoqda ishlaydi", "U faqat video striming uchun ishlatiladi", 
     "A", "HARD", 1.5, "REASONING", "TCP uch tomonlama qo'l siqish (3-way handshake) va paket tasdiqlarini ishlatadi, UDP esa tezlikka yo'naltirilgan."),

    # --- MAVZU 3: Algoritmlash va blok-sxemalar ---
    # Bilish (Knowledge)
    (topics[2], "Blok-sxemada shart tekshirish amali qaysi geometrik shakl bilan belgilanadi?", 
     "Romb", "To'g'ri to'rtburchak", "Parallelogramm", "Oval", 
     "A", "EASY", -1.3, "KNOWLEDGE", "Romb shart va mantiqiy tarmoqlanishni ifodalaydi."),
    (topics[2], "Algoritmning 'Diskretlik' xossasi nimani anglatadi?", 
     "Ketma-ket aniq qadamlardan iborat bo'lishini", "Natijaga erishishini", "Barcha uchun tushunarli bo'lishini", "Har xil ma'lumotlar uchun ishlashini", 
     "A", "EASY", -0.9, "KNOWLEDGE", "Diskretlik - jarayonning chekli va aniq qadamlar ketma-ketligiga bo'linuvchanligidir."),
    (topics[2], "Blok-sxemada ma'lumotlarni kiritish va chiqarish qaysi shakl bilan tasvirlanadi?", 
     "Parallelogramm", "Aylana", "Kvadrat", "Uchburchak", 
     "A", "EASY", -1.1, "KNOWLEDGE", "Parallelogramm standart kiritish/chiqarish (I/O) blokidir."),

    # Qo'llash (Application)
    (topics[2], "a = 5, b = 8 bo'lsa, 'a > b bo'lsa c = a - b, aks holda c = a + b' algoritmida c ning qiymati nima bo'ladi?", 
     "13", "3", "-3", "40", 
     "A", "MEDIUM", 0.1, "APPLICATION", "5 > 8 sharti False bo'lgani sababli aks holda shoxchasi ishlaydi: c = 5 + 8 = 13."),
    (topics[2], "1 dan 10 gacha bo'lgan toq sonlarni hisoblovchi sikl necha marta takrorlanadi?", 
     "5 marta", "10 marta", "4 marta", "1 marta", 
     "A", "MEDIUM", 0.2, "APPLICATION", "1, 3, 5, 7, 9 toq sonlari jami 5 ta."),
    (topics[2], "Algoritmda: x = 10; x = x * 2; x = x - 5 bo'lsa, yakuniy x qiymati qanday?", 
     "15", "20", "10", "25", 
     "A", "MEDIUM", -0.2, "APPLICATION", "x = 10 * 2 = 20; 20 - 5 = 15."),

    # Mulohaza yuritish (Reasoning)
    (topics[2], "Rekursiv algoritm nima va unda to'xtash sharti (base case) bo'lmasa nima sodir bo'ladi?", 
     "O'zini o'zi chaqiradi; to'xtash sharti bo'lmasa stek to'lib dastur qulaydi", "Hech qachon ishlamaydi", "Kompyuterni qayta yuklaydi", "Avtomatik to'xtaydi", 
     "A", "HARD", 1.3, "REASONING", "Rekursiya to'xtash shartisiz Stack Overflow (rekursiya chuqurligi oshib ketishi) xatosini keltirib chiqaradi."),
    (topics[2], "Ikkilik qidiruv (Binary search) algoritmining chiziqli qidiruvdan asosiy afzalligi qachon namoyon bo'ladi?", 
     "Ro'yxat tartiblangan bo'lganda, qidiruv vaqti logarifmik O(log n) ga qisqaradi", "Ro'yxat aralash bo'lganda tez ishlaydi", "Faqat matnlarni qidirishda", "Xotirani umuman ishlatmasligida", 
     "A", "HARD", 1.4, "REASONING", "Binary search har qadamda qidiruv sohasini 2 barobar qisqartiradi, ammo massiv saralangan bo'lishi shart."),
    (topics[2], "Algoritm murakkabligi O(n^2) bo'lsa, elementlar soni 10 tadan 100 taga (10 marta) oshganda amallar soni necha marta oshadi?", 
     "100 marta", "10 marta", "20 marta", "1000 marta", 
     "A", "HARD", 1.6, "REASONING", "Kvadratik murakkablikda (10)^2 = 100 marta ko'p amal talab etiladi."),

    # --- MAVZU 4: Python: Ma'lumot turlari va shart operatorlari ---
    # Bilish (Knowledge)
    (topics[3], "Python dasturida 'type(3.14)' qanday natija beradi?", 
     "<class 'float'>", "<class 'int'>", "<class 'str'>", "<class 'bool'>", 
     "A", "EASY", -1.1, "KNOWLEDGE", "3.14 o'nlik kasr (suzuvchi vergulli son), ya'ni float."),
    (topics[3], "Python tilida tenglikni tekshirish uchun qaysi operator ishlatiladi?", 
     "==", "=", "!=", "<>", 
     "A", "EASY", -1.0, "KNOWLEDGE", "Tenglikni tekshirish shart operatorida == belgisi bilan ifodalanadi."),
    (topics[3], "Python'da matnli ma'lumotlar qaysi ma'lumot turida saqlanadi?", 
     "str", "char", "text", "string", 
     "A", "EASY", -1.2, "KNOWLEDGE", "Python'da barcha matnlar str (string) turida saqlanadi."),

    # Qo'llash (Application)
    (topics[3], "Agar x = 10, y = 20 bo'lsa, 'x < 15 and y > 25' ifodasi nima qaytaradi?", 
     "False", "True", "None", "Xatolik", 
     "A", "MEDIUM", 0.0, "APPLICATION", "x < 15 (True), ammo y > 25 (False). True and False natijasi False."),
    (topics[3], "Quyidagi kod natijasi nima bo'ladi: s = 'Python'; print(s[1:4])?", 
     "yth", "Pyt", "ytho", "th", 
     "A", "MEDIUM", 0.3, "APPLICATION", "Kesma [1:4] 1, 2, 3 indekslarni oladi: 'y', 't', 'h'."),
    (topics[3], "a = True; b = False; print(not b or a) kodi natijasi nima?", 
     "True", "False", "None", "SyntaxError", 
     "A", "MEDIUM", 0.2, "APPLICATION", "not False -> True. True or True -> True."),

    # Mulohaza yuritish (Reasoning)
    (topics[3], "Python'da '5' + '5' va 5 + 5 ifodalarining natijalari nima sababdan farq qiladi?", 
     "Birinchisida satrlar ulanadi ('55'), ikkinchisida sonlar qo'shiladi (10)", "Ikkalasi ham 10 natija beradi", "Ikkalasi ham xatolik beradi", "Birinchisi son, ikkinchisi ro'yxat bo'ladi", 
     "A", "HARD", 1.1, "REASONING", "Python kuchli tiplangan til bo'lib, str lar uchun '+' konkatenatsiya, int lar uchun arifmetik qo'shishdir."),
    (topics[3], "bool([]) va bool([0]) ifodalari nima qaytaradi va sababi nima?", 
     "False va True; bo'sh ro'yxat mantiqan False, elementi bor ro'yxat True hisoblanadi", "Ikkalasi ham False", "Ikkalasi ham True", "Xatolik yuz beradi", 
     "A", "HARD", 1.3, "REASONING", "Konteyner turlari (ro'yxat, lug'at) bo'sh bo'lsa False, kamida bitta elementga ega bo'lsa (hatto u 0 bo'lsa ham) True bo'ladi."),
    (topics[3], "x = 0 bo'lganda: (x != 0) and (10 / x > 1) ifodasi nima qaytaradi va nolga bo'lish xatosi nega chiqmaydi?", 
     "False qaytaradi; qisqa zanjirli hisoblash (short-circuit) tufayli ikkinchi qism bajarilmaydi", "ZeroDivisionError xatosi beradi", "True qaytaradi", "None beradi", 
     "A", "HARD", 1.5, "REASONING", "'and' amali birinchi operand False bo'lsa, ikkinchisini hisoblamaydi (short-circuit)."),

    # --- MAVZU 5: Python: Takrorlanish operatorlari (for, while) ---
    # Bilish (Knowledge)
    (topics[4], "Python'da 'range(1, 5)' qaysi sonlarni hosil qiladi?", 
     "1, 2, 3, 4", "1, 2, 3, 4, 5", "0, 1, 2, 3, 4", "2, 3, 4, 5", 
     "A", "EASY", -0.8, "KNOWLEDGE", "range(start, stop) funksiyasida stop qiymatining o'zi kirmaydi."),
    (topics[4], "Siklning keyingi qadamiga o'tish uchun qaysi kalit so'z ishlatiladi?", 
     "continue", "break", "pass", "return", 
     "A", "EASY", -0.7, "KNOWLEDGE", "continue buyrug'i joriy iteratsiyani tugatib darhol keyingisiga o'tadi."),
    (topics[4], "Siklni muddatidan oldin butunlay to'xtatish uchun qaysi buyruq qo'llaniladi?", 
     "break", "stop", "exit", "pause", 
     "A", "EASY", -0.9, "KNOWLEDGE", "break buyrug'i siklni muddatidan oldin darhol to'xtatadi."),

    # Qo'llash (Application)
    (topics[4], "List comprehension orqali [x**2 for x in range(3)] nima hosil qiladi?", 
     "[0, 1, 4]", "[1, 4, 9]", "[0, 1, 2]", "[0, 2, 4]", 
     "A", "MEDIUM", 0.4, "APPLICATION", "range(3) bu 0, 1, 2 sonlari. Ularning kvadratlari [0, 1, 4]."),
    (topics[4], "s = 0; for i in range(1, 4): s += i; print(s) natijasi nima?", 
     "6", "10", "3", "4", 
     "A", "MEDIUM", 0.1, "APPLICATION", "s = 0 + 1 + 2 + 3 = 6."),
    (topics[4], "i = 1; while i < 5: i += 2; print(i) kodi tugagach ekranga nima chiqadi?", 
     "5", "4", "3", "7", 
     "A", "MEDIUM", 0.2, "APPLICATION", "1 -> 3 -> 5. 5 < 5 sharti False bo'lib chiqadi va 5 chop etiladi."),

    # Mulohaza yuritish (Reasoning)
    (topics[4], "'while True' siklida 'break' operatori shartga bog'lanmagan bo'lsa, sikl qanday ishlaydi?", 
     "Sikl faqat bir marta aylanadi va to'xtaydi", "Sikl cheksiz aylanadi", "Dastur qotib qoladi", "Sikl umuman ishlamaydi", 
     "A", "HARD", 1.2, "REASONING", "Agar break to'g'ridan-to'g'ri sikl tanasida tursa, birinchi qadamdayoq sikl to'xtatiladi."),
    (topics[4], "Ro'yxat ustida 'for x in lst:' aylanayotganda, 'lst.remove(x)' qilish nima sababdan xavfli?", 
     "Ro'yxat indekslari surilib, keyingi elementlar tekshirilmasdan qolib ketishi mumkin", "Python birdan o'chib ketadi", "Ro'yxat teskari aylanib qoladi", "Barcha elementlar 0 ga aylanadi", 
     "A", "HARD", 1.4, "REASONING", "Iteratsiya davomida kolleksiya o'lchami o'zgarsa indekslar siljiydi va iteratsiya xatosi yuzaga keladi."),
    (topics[4], "Ichma-ich ikkita 'for' sikli (n x n) nima sababdan katta ma'lumotlarda tavsiya etilmaydi?", 
     "Operatsiyalar soni n kvadratga mutanosib o'sib, hisoblash vaqtini keskin oshiradi", "Xotira yetishmay qoladi", "Python ikkinchi for ga kirmaydi", "Faqat birinchi sikl ishlaydi", 
     "A", "HARD", 1.5, "REASONING", "O(n^2) murakkablik katta n (masalan 100,000) uchun millionlab operatsiyalarni talab qiladi.")
]

for item in questions_data:
    top, txt, oa, ob, oc, od, corr, diff, rasch, cog, exp = item
    q, created = Question.objects.get_or_create(
        topic=top, text=txt,
        defaults={
            'option_a': oa, 'option_b': ob, 'option_c': oc, 'option_d': od,
            'correct_option': corr, 'difficulty': diff, 'rasch_difficulty': rasch,
            'cognitive_level': cog, 'explanation': exp
        }
    )
    if not created:
        q.cognitive_level = cog
        q.difficulty = diff
        q.rasch_difficulty = rasch
        q.explanation = exp
        q.save()

print(f"Jami {Question.objects.count()} ta savol bazada mavjud.")

# 5. Gamification Badges & Rules
badges_data = [
    ("Formativ Qahramoni", "Barcha darslarda yuqori faollik ko'rsatganlik uchun", "fa-star", 50),
    ("Dasturchi Bolakay", "Python mavzularida a'lo natija ko'rsatgan o'quvchiga", "fa-code", 40),
    ("Test Sinovi G'olibi", "Formativ testlarni 100% bajarganlik uchun", "fa-trophy", 60),
    ("BSB Tayyorgarligi", "Summativ imtihonga dopusk olgan o'quvchiga", "fa-shield-halved", 30)
]

for title, desc, icon, rxp in badges_data:
    Badge.objects.get_or_create(title=title, defaults={'description': desc, 'icon': icon, 'reward_xp': rxp})

b1 = Badge.objects.first()
StudentBadge.objects.get_or_create(student=student1, badge=b1)
StudentBadge.objects.get_or_create(student=student4, badge=b1)

# Dopusk Rule
ExamDopuskRule.objects.get_or_create(
    subject=subject,
    defaults={'required_coins': 40, 'required_formative_avg': 60.0, 'bonus_percentage_rate': 5.0}
)

# 6. Student Rewards (Coins & XP)
r1, _ = StudentReward.objects.get_or_create(student=student1)
r1.coins = 95
r1.xp = 340
r1.streak_days = 5
r1.level = "Ilg'or Bilimdon 🚀"
r1.save()

r2, _ = StudentReward.objects.get_or_create(student=student2)
r2.coins = 55
r2.xp = 180
r2.streak_days = 3
r2.level = "Izlanuvchan 💡"
r2.save()

r3, _ = StudentReward.objects.get_or_create(student=student3)
r3.coins = 25  # Dopuskka yetmaydi (< 40)
r3.xp = 80
r3.streak_days = 1
r3.level = "Boshlang'ich 🌱"
r3.save()

r4, _ = StudentReward.objects.get_or_create(student=student4)
r4.coins = 120
r4.xp = 520
r4.streak_days = 7
r4.level = "Bilimdon Master 🏆"
r4.save()

# 7. Formative Assessment Data (Baholar va Testlar)
# Azizbek: Hamma mavzudan yuqori (85-95)
# Madina: Mavzu 3 (Algoritmlar) da past (40-50, zaif)
# Jasur: Mavzu 3 va Mavzu 5 da past (30-45, zaif)

formative_mock = [
    # (student, topic_index, score_quiz, score_hw, score_act)
    (student1, 0, 90, 95, 90),
    (student1, 1, 85, 90, 85),
    (student1, 2, 80, 85, 80),
    (student1, 3, 95, 100, 95),
    (student1, 4, 90, 90, 90),

    (student2, 0, 75, 80, 70),
    (student2, 1, 70, 75, 75),
    (student2, 2, 45, 50, 40),  # Zaif mavzu!
    (student2, 3, 80, 85, 80),
    (student2, 4, 75, 70, 75),

    (student3, 0, 60, 65, 55),
    (student3, 1, 55, 60, 50),
    (student3, 2, 35, 40, 30),  # Zaif mavzu!
    (student3, 3, 65, 70, 60),
    (student3, 4, 40, 45, 35),  # Zaif mavzu!

    (student4, 0, 95, 100, 95),
    (student4, 1, 90, 95, 90),
    (student4, 2, 85, 90, 85),
    (student4, 3, 100, 100, 95),
    (student4, 4, 95, 95, 90),
]

FormativeGrade.objects.all().delete()
QuizAttempt.objects.all().delete()
StudentTopicMastery.objects.all().delete()

for st, t_idx, sq, sh, sa in formative_mock:
    top = topics[t_idx]
    # Homework
    FormativeGrade.objects.create(student=st, topic=top, grade_type='HOMEWORK', score=sh, max_score=100)
    # Activity
    FormativeGrade.objects.create(student=st, topic=top, grade_type='ACTIVITY', score=sa, max_score=100)
    # Quiz attempt
    correct_cnt = int(round((sq / 100) * 5))
    QuizAttempt.objects.create(student=st, topic=top, score=sq, total_questions=5, correct_answers=correct_cnt)
    # Update Mastery
    update_student_topic_mastery(st, top)

print("Formativ baholar va tahlillar hisoblab chiqildi!")
print("--- SEED DATA MUVAFFAQIYATLI YAKUNLANDI ---")

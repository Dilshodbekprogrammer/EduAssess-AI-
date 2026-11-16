import json
import csv
import io
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings

from apps.accounts.models import Profile
from apps.academic.models import Subject, Topic, Question
from apps.assessment.models import (
    FormativeGrade, StudentTopicMastery, QuizAttempt, 
    SummativeExam, SummativeExamQuestion
)
from apps.gamification.models import StudentReward, Badge, StudentBadge, ExamDopuskRule
from apps.analytics.services import (
    update_student_topic_mastery, predict_summative_score,
    check_dopusk, generate_adaptive_exam, evaluate_summative_exam
)

# ----------------- Xavfsizlik & Ruxsat Decoratorlari -----------------

def teacher_required(view_func):
    """
    Faqat o'qituvchilar va administratorlar uchun ruxsat tekshiruvi.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        profile = getattr(request.user, 'profile', None)
        if not (request.user.is_staff or request.user.is_superuser or (profile and profile.is_teacher)):
            messages.error(request, "Xavfsizlik: Ushbu sahifaga faqat o'qituvchilar va ma'murlar kira oladi!")
            return redirect('student_portal')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ----------------- Autentifikatsiya (Login / Logout) -----------------

def login_view(request):
    """
    Xavfsiz tizimga kirish sahifasi
    """
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if request.user.is_staff or (profile and profile.is_teacher):
            return redirect('teacher_dashboard')
        return redirect('student_portal')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            profile = getattr(user, 'profile', None)
            if user.is_staff or (profile and profile.is_teacher):
                return redirect('teacher_dashboard')
            return redirect('student_portal')
        else:
            messages.error(request, "Login yoki parol noto'g'ri kiritildi! Iltimos, qayta urinib ko'ring.")

    return render(request, 'login.html')

def logout_view(request):
    """
    Tizimdan xavfsiz chiqish
    """
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('login')

# ----------------- Asosiy Sahifa -----------------

def home_view(request):
    """
    Bosh sahifa: Loyiha maqsadi va konsepsiyasi
    """
    subject = Subject.objects.first()
    students = User.objects.filter(profile__role='STUDENT').select_related('profile', 'reward')
    teacher = User.objects.filter(profile__role='TEACHER').first()
    
    total_students = students.count()
    total_topics = Topic.objects.count()
    total_questions = Question.objects.count()

    context = {
        'subject': subject,
        'students': students,
        'teacher': teacher,
        'total_students': total_students,
        'total_topics': total_topics,
        'total_questions': total_questions,
    }
    return render(request, 'index.html', context)

# ----------------- O'qituvchi Boshqaruv Paneli -----------------

@teacher_required
def teacher_dashboard(request):
    """
    O'qituvchining aqlli jurnali va tahliliy dashboardi.
    Faqat vakolatli o'qituvchi va ma'murlar kira oladi.
    """
    subject = Subject.objects.first()
    topics = subject.topics.all() if subject else []
    students = User.objects.filter(profile__role='STUDENT').select_related('profile', 'reward')

    student_analysis = []
    chart_names = []
    chart_predicted = []
    chart_actual_latest = []
    chart_coins = []

    for st in students:
        pred = predict_summative_score(st, subject)
        weak_topics = StudentTopicMastery.objects.filter(student=st, is_weak=True).select_related('topic')
        can_enter, dopusk_msg, bonus = check_dopusk(st, subject)
        reward = getattr(st, 'reward', None)
        coins = reward.coins if reward else 0

        # Oxirgi summativ imtihon
        latest_exam = SummativeExam.objects.filter(student=st, status='COMPLETED').order_by('-completed_at').first()
        actual_score = latest_exam.final_score if latest_exam else None

        student_analysis.append({
            'student': st,
            'predicted': pred,
            'weak_topics': weak_topics,
            'can_enter': can_enter,
            'dopusk_msg': dopusk_msg,
            'bonus': bonus,
            'coins': coins,
            'actual_score': actual_score
        })

        chart_names.append(st.get_full_name() or st.username)
        chart_predicted.append(pred)
        # TUZATISH: actual_score mavjud bo'lmasa, uni sun'iy prognoz bilan almashtirmaymiz (None -> null)
        chart_actual_latest.append(actual_score)
        chart_coins.append(coins)

    # Mavzular bo'yicha zaiflik darajasi (Topic Gap Analysis)
    topic_gaps = []
    for top in topics:
        weak_count = StudentTopicMastery.objects.filter(topic=top, is_weak=True).count()
        total_m = StudentTopicMastery.objects.filter(topic=top).count()
        percentage = round((weak_count / total_m * 100), 1) if total_m > 0 else 0
        topic_gaps.append({
            'topic': top,
            'weak_count': weak_count,
            'percentage': percentage
        })

    # Oxirgi formativ baholar
    recent_grades = FormativeGrade.objects.select_related('student', 'topic').order_by('-id')[:10]

    context = {
        'subject': subject,
        'topics': topics,
        'students': students,
        'student_analysis': student_analysis,
        'topic_gaps': topic_gaps,
        'recent_grades': recent_grades,
        'chart_names_json': json.dumps(chart_names),
        'chart_predicted_json': json.dumps(chart_predicted),
        'chart_actual_json': json.dumps(chart_actual_latest),
        'chart_coins_json': json.dumps(chart_coins),
        'topic_gaps_labels_json': json.dumps([t['topic'].title[:20] for t in topic_gaps]),
        'topic_gaps_values_json': json.dumps([t['percentage'] for t in topic_gaps]),
    }
    return render(request, 'dashboard_teacher.html', context)

@teacher_required
def add_student_view(request):
    """
    O'qituvchi tomonidan yangi o'quvchi(lar)ni tizimga qo'shish:
    1. Yagona o'quvchi qo'shish formasi
    2. Ommaviy sinf ro'yxati (Bulk list) orqali bir necha o'quvchini bir vaqtda kiritish
    """
    if request.method == 'POST':
        action = request.POST.get('action', 'single')

        if action == 'single':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            grade_level = request.POST.get('grade_level', '9-A').strip()
            username = request.POST.get('username', '').strip().lower()
            password = request.POST.get('password', '').strip() or 'parol123'
            phone = request.POST.get('phone', '').strip()

            if not first_name or not last_name:
                messages.error(request, "Iltimos, o'quvchining ismi va familiyasini to'ldiring!")
                return redirect('teacher_dashboard')

            # Agar login kiritilmagan bo'lsa, avtomatik yaratish
            if not username:
                import re
                base_user = re.sub(r'[^a-zA-Z0-9]', '', f"{first_name.lower()}_{last_name.lower()}")
                username = base_user
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_user}{suffix}"
                    suffix += 1

            if User.objects.filter(username=username).exists():
                messages.error(request, f"'{username}' logini allaqachon mavjud! Iltimos, boshqa login tanlang.")
                return redirect('teacher_dashboard')

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{username}@maktab.uz"
                )
                user.profile.role = 'STUDENT'
                user.profile.grade_level = grade_level
                user.profile.phone = phone
                user.profile.save()

                StudentReward.objects.get_or_create(student=user, defaults={'coins': 0, 'xp': 0})

                # Barcha mavzular bo'yicha boshlang'ich o'zlashtirish kartalarini yaratish
                subject = Subject.objects.first()
                if subject:
                    for top in subject.topics.all():
                        StudentTopicMastery.objects.get_or_create(
                            student=user, topic=top,
                            defaults={'mastery_percentage': 0.0, 'is_weak': True}
                        )

            messages.success(
                request, 
                f"🎉 Yangi o'quvchi muvaffaqiyatli qo'shildi! "
                f"F.I.SH: {first_name} {last_name} | Login: <strong>{username}</strong> | Parol: <strong>{password}</strong>"
            )

        elif action == 'bulk':
            raw_text = request.POST.get('student_list', '').strip()
            default_grade = request.POST.get('default_grade', '9-A').strip()
            default_pass = request.POST.get('default_password', 'parol123').strip() or 'parol123'

            if not raw_text:
                messages.error(request, "Ro'yxat matni bo'sh! Iltimos, o'quvchilar ismlarini kiriting.")
                return redirect('teacher_dashboard')

            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            created_students = []

            with transaction.atomic():
                import re
                for line in lines:
                    # Qatordan tartib raqamlarini tozalash: "1. Aliyev Vali, 9-A"
                    clean_line = re.sub(r'^\d+[\.\)\-\s]+', '', line).strip()
                    parts = [p.strip() for p in clean_line.split(',') if p.strip()]
                    name_part = parts[0]
                    grade = parts[1] if len(parts) > 1 else default_grade

                    name_tokens = name_part.split()
                    if len(name_tokens) >= 2:
                        surname_suffixes = ('ov', 'ova', 'ev', 'eva', 'yev', 'yeva', 'zoda', 'iy', 'iya')
                        # Agar ikkinchi yoki oxirgi so'z familiyaga o'xshasa (masalan: "Sardor Valiyev")
                        if any(name_tokens[-1].lower().endswith(s) for s in surname_suffixes) and not any(name_tokens[0].lower().endswith(s) for s in surname_suffixes):
                            first_name = " ".join(name_tokens[:-1])
                            last_name = name_tokens[-1]
                        else:
                            last_name = name_tokens[0]
                            first_name = " ".join(name_tokens[1:])
                    else:
                        first_name = name_tokens[0]
                        last_name = "O'quvchi"

                    # Avtomatik login
                    base_login = re.sub(r'[^a-zA-Z0-9]', '', f"{first_name.lower()}_{last_name.lower()}")
                    if not base_login:
                        base_login = "student"
                    username = base_login
                    suffix = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_login}{suffix}"
                        suffix += 1

                    user = User.objects.create_user(
                        username=username,
                        password=default_pass,
                        first_name=first_name,
                        last_name=last_name,
                        email=f"{username}@maktab.uz"
                    )
                    user.profile.role = 'STUDENT'
                    user.profile.grade_level = grade
                    user.profile.save()

                    StudentReward.objects.get_or_create(student=user, defaults={'coins': 0, 'xp': 0})

                    subject = Subject.objects.first()
                    if subject:
                        for top in subject.topics.all():
                            StudentTopicMastery.objects.get_or_create(
                                student=user, topic=top,
                                defaults={'mastery_percentage': 0.0, 'is_weak': True}
                            )

                    created_students.append(f"{first_name} {last_name} (Login: {username})")

            messages.success(
                request, 
                f"✅ Sinf ro'yxatidan {len(created_students)} nafar o'quvchi muvaffaqiyatli ro'yxatga olindi! Barchasining boshlang'ich paroli: <strong>{default_pass}</strong>"
            )

    return redirect('teacher_dashboard')

@teacher_required
def add_formative_grade(request):
    """
    O'qituvchi tomonidan formativ baho qo'shish
    Server qiymatlari to'liq tekshiriladi:
    - 0 <= score <= max_score
    - max_score > 0
    - student va topic to'g'ri bog'langan
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        topic_id = request.POST.get('topic_id')
        grade_type = request.POST.get('grade_type')
        comment = request.POST.get('comment', '').strip()

        try:
            score = float(request.POST.get('score', 0))
            max_score = float(request.POST.get('max_score', 100.0))
        except (ValueError, TypeError):
            messages.error(request, "Baho va maksimal ball faqat raqam bo'lishi kerak!")
            return redirect('teacher_dashboard')

        if max_score <= 0:
            messages.error(request, "Maksimal ball 0 dan katta bo'lishi shart!")
            return redirect('teacher_dashboard')

        if score < 0 or score > max_score:
            messages.error(request, f"Baho 0 va maksimal ball ({max_score}) oralig'ida bo'lishi kerak! Siz kiritgan qiymat: {score}")
            return redirect('teacher_dashboard')

        student = get_object_or_404(User, id=student_id)
        topic = get_object_or_404(Topic, id=topic_id)

        with transaction.atomic():
            FormativeGrade.objects.create(
                student=student,
                topic=topic,
                grade_type=grade_type,
                score=score,
                max_score=max_score,
                comment=comment
            )

            # Mavzu o'zlashtirish foizini yangilash
            mastery = update_student_topic_mastery(student, topic)

            # Gamifikatsiya: Darsdagi faollik uchun o'quvchiga coin
            reward, _ = StudentReward.objects.get_or_create(student=student)
            coins_to_add = int((score / max_score * 100) // 10)
            reward.add_coins(coins_to_add)

        messages.success(
            request, 
            f"✅ {student.get_full_name()}ga '{topic.title}' bo'yicha {score}/{max_score} baho qo'yildi (+{coins_to_add} coin)! "
            f"Mavzu o'zlashtirish: {mastery.mastery_percentage}%."
        )

    return redirect('teacher_dashboard')

# ----------------- O'quvchi Kabineti -----------------

@login_required
def student_portal(request, student_id=None):
    """
    O'quvchi kabineti:
    - Xavfsizlik: O'quvchi faqat o'zining shaxsiy natijalarini ko'ra oladi.
    - O'qituvchilar va ma'murlar monitoring uchun istalgan o'quvchini ko'rishlari mumkin.
    """
    current_profile = getattr(request.user, 'profile', None)
    is_teacher = request.user.is_staff or (current_profile and current_profile.is_teacher)

    if student_id:
        target_student = get_object_or_404(User, id=student_id)
        if not is_teacher and target_student.id != request.user.id:
            messages.error(request, "Xavfsizlik: Siz faqat o'zingizning natijalaringizni ko'ra olasiz!")
            return redirect('student_portal')
        student = target_student
    else:
        if is_teacher:
            student = User.objects.filter(profile__role='STUDENT').first() or request.user
        else:
            student = request.user

    subject = Subject.objects.first()
    reward, _ = StudentReward.objects.get_or_create(student=student)
    badges = StudentBadge.objects.filter(student=student).select_related('badge')
    all_badges = Badge.objects.all()

    # O'zlashtirish xaritasi
    topics = subject.topics.all() if subject else []
    masteries = []
    for top in topics:
        m, _ = StudentTopicMastery.objects.get_or_create(
            student=student, topic=top,
            defaults={'mastery_percentage': 0.0, 'is_weak': True}
        )
        masteries.append(m)

    weak_count = sum(1 for m in masteries if m.is_weak)

    # Prognoz va Dopusk
    predicted_score = predict_summative_score(student, subject)
    can_enter, dopusk_msg, bonus = check_dopusk(student, subject)

    # Imtihonlar tarixi
    exams = SummativeExam.objects.filter(student=student).order_by('-created_at')

    # Reyting (Leaderboard)
    leaderboard = StudentReward.objects.select_related('student', 'student__profile').order_by('-xp')[:10]

    context = {
        'student': student,
        'subject': subject,
        'reward': reward,
        'badges': badges,
        'all_badges': all_badges,
        'masteries': masteries,
        'weak_count': weak_count,
        'predicted_score': predicted_score,
        'can_enter': can_enter,
        'dopusk_msg': dopusk_msg,
        'bonus': bonus,
        'exams': exams,
        'leaderboard': leaderboard,
        'is_teacher_viewing': is_teacher,
    }
    return render(request, 'student_portal.html', context)

@login_required
def take_formative_quiz(request, topic_id, student_id=None):
    """
    Mavzu bo'yicha qisqa formativ test.
    O'quvchi faqat o'zi uchun test topshira oladi.
    """
    topic = get_object_or_404(Topic, id=topic_id)
    current_profile = getattr(request.user, 'profile', None)
    is_teacher = request.user.is_staff or (current_profile and current_profile.is_teacher)

    if student_id:
        if not is_teacher and student_id != request.user.id:
            messages.error(request, "Siz faqat o'zingiz uchun test topshira olasiz!")
            return redirect('student_portal')
        student = get_object_or_404(User, id=student_id)
    else:
        student = request.user

    questions = list(topic.questions.all())

    if request.method == 'POST':
        correct_count = 0
        total = len(questions)
        for q in questions:
            user_ans = request.POST.get(f'question_{q.id}', '').upper().strip()
            if user_ans == q.correct_option:
                correct_count += 1

        percentage = round((correct_count / total * 100), 1) if total > 0 else 0
        
        with transaction.atomic():
            # Test natijasini faqat QuizAttempt ga saqlash (takroriy hisoblashni oldini olish)
            QuizAttempt.objects.create(
                student=student,
                topic=topic,
                score=percentage,
                total_questions=total,
                correct_answers=correct_count
            )

            # O'zlashtirishni yangilash
            update_student_topic_mastery(student, topic)

            # Gamifikatsiya
            earned_coins = correct_count * 5
            reward, _ = StudentReward.objects.get_or_create(student=student)
            reward.add_coins(earned_coins)

        messages.success(request, f"Formativ test yakunlandi! Natija: {percentage}%. Siz {earned_coins} coin qo'lga kiritdingiz!")
        return redirect('student_portal_id', student_id=student.id)

    context = {
        'student': student,
        'topic': topic,
        'questions': questions,
    }
    return render(request, 'formative_quiz.html', context)

# ----------------- Adaptiv Summativ Imtihon -----------------

@login_required
def start_adaptive_exam(request, student_id=None):
    """
    Dinamik Summativ Imtihon (BSB/CHSB) ni generatsiya qilish (15 ta savol)
    - 5 ta Bilish
    - 5 ta Qo'llash
    - 5 ta Mulohaza yuritish
    - 60% savollar o'quvchining aynan zaif mavzulariga adaptiv yo'naltiriladi
    """
    current_profile = getattr(request.user, 'profile', None)
    is_teacher = request.user.is_staff or (current_profile and current_profile.is_teacher)

    if student_id:
        if not is_teacher and student_id != request.user.id:
            messages.error(request, "Siz faqat o'zingiz uchun imtihon boshlay olasiz!")
            return redirect('student_portal')
        student = get_object_or_404(User, id=student_id)
    else:
        student = request.user

    subject = Subject.objects.first()
    if not subject:
        messages.error(request, "Tizimda fan mavjud emas!")
        return redirect('student_portal')

    exam = generate_adaptive_exam(student, subject, exam_type='BSB', total_questions=15)

    if not exam.dopusk_granted:
        messages.error(request, f"Imtihon boshlanmadi: {exam.dopusk_message}")
        return redirect('student_portal_id', student_id=student.id)

    return redirect('take_adaptive_exam', exam_id=exam.id)

@login_required
def take_adaptive_exam(request, exam_id):
    """
    Dinamik imtihon topshirish sahifasi.
    Xavfsizlik:
    - Faqat imtihon egasi topshira oladi.
    - Agar imtihon allaqachon yakunlangan bo'lsa, qayta yuborish bloklanadi va natijaga yo'naltiriladi.
    """
    exam = get_object_or_404(SummativeExam, id=exam_id)

    # Imtihon egasini tekshirish
    if exam.student != request.user and not request.user.is_staff:
        messages.error(request, "Siz faqat o'zingizga tegishli imtihonni topshirishingiz mumkin!")
        return redirect('student_portal')

    # Bir martalik topshirish kafolati
    if exam.status == 'COMPLETED':
        messages.info(request, "Ushbu imtihon allaqachon yakunlangan.")
        return redirect('exam_result', exam_id=exam.id)

    exam_questions = exam.questions.select_related('question', 'question__topic').all()

    if request.method == 'POST':
        # Qayta yuborilganda yana hisoblash va mukofot berishni qat'iy bloklash
        if exam.status == 'COMPLETED':
            return redirect('exam_result', exam_id=exam.id)

        answers_dict = {}
        for eq in exam_questions:
            q_id = str(eq.question.id)
            answers_dict[q_id] = request.POST.get(f'q_{q_id}', '')

        evaluate_summative_exam(exam, answers_dict)
        messages.success(request, "Imtihon topshirildi va natijalar hisoblandi!")
        return redirect('exam_result', exam_id=exam.id)

    context = {
        'exam': exam,
        'exam_questions': exam_questions,
        'student': exam.student,
    }
    return render(request, 'adaptive_exam.html', context)

@login_required
def exam_result(request, exam_id):
    """
    Imtihon natijalari, Rasch modeli va kognitiv tahlil.
    XAVFSIZLIK:
    - Faqat imtihon egasi yoki o'qituvchi/ma'mur ko'ra oladi.
    - Tugallanmagan imtihonning natija sahifasida javoblar QAT'IYAN KO'RSATILMAYDI!
    """
    exam = get_object_or_404(SummativeExam, id=exam_id)
    current_profile = getattr(request.user, 'profile', None)
    is_teacher = request.user.is_staff or (current_profile and current_profile.is_teacher)

    if not is_teacher and exam.student != request.user:
        messages.error(request, "Ushbu natijani ko'rishga ruxsatingiz yo'q!")
        return redirect('student_portal')

    # Xavfsizlik: Tugallanmagan imtihon javoblarini oldindan ko'rishni bloklash
    if exam.status != 'COMPLETED':
        if exam.student == request.user:
            messages.warning(request, "Imtihon hali yakunlanmagan! Avval barcha savollarga javob bering.")
            return redirect('take_adaptive_exam', exam_id=exam.id)
        else:
            messages.error(request, "Ushbu imtihon hali o'quvchi tomonidan yakunlanmagan.")
            return redirect('teacher_dashboard')

    exam_questions = exam.questions.select_related('question', 'question__topic').all()

    weak_questions = [eq for eq in exam_questions if eq.is_targeted_weak]
    weak_correct = sum(1 for eq in weak_questions if eq.is_correct)
    diff = round(exam.final_score - exam.predicted_score, 1)

    context = {
        'exam': exam,
        'exam_questions': exam_questions,
        'weak_questions_count': len(weak_questions),
        'weak_correct_count': weak_correct,
        'diff': diff,
    }
    return render(request, 'exam_result.html', context)

# ----------------- Savollar Banki va Test Yuklash -----------------

@teacher_required
def upload_questions_view(request):
    """
    O'qituvchilar uchun savol yuklash oynasi.
    Tranzaksiya yaxlitligi: Xato qator bo'lsa, qisman yuklash bekor qilinadi.
    """
    subject = Subject.objects.first()
    topics = subject.topics.all() if subject else Topic.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action', 'single')

        if action == 'single':
            topic_id = request.POST.get('topic_id')
            text = request.POST.get('text', '').strip()
            oa = request.POST.get('option_a', '').strip()
            ob = request.POST.get('option_b', '').strip()
            oc = request.POST.get('option_c', '').strip()
            od = request.POST.get('option_d', '').strip()
            corr = request.POST.get('correct_option', 'A').strip().upper()
            cog = request.POST.get('cognitive_level', 'KNOWLEDGE')
            diff = request.POST.get('difficulty', 'MEDIUM')
            exp = request.POST.get('explanation', '').strip()

            try:
                rasch = float(request.POST.get('rasch_difficulty', 0.0))
            except (ValueError, TypeError):
                rasch = 0.0

            topic = get_object_or_404(Topic, id=topic_id)
            if not text or not oa or not ob or not oc or not od:
                messages.error(request, "Iltimos, savol matni va barcha 4 ta variantni to'liq kiriting!")
                return redirect('upload_questions')

            if corr not in ['A', 'B', 'C', 'D']:
                messages.error(request, "To'g'ri javob faqat A, B, C yoki D bo'lishi kerak!")
                return redirect('upload_questions')

            Question.objects.create(
                topic=topic,
                text=text,
                option_a=oa,
                option_b=ob,
                option_c=oc,
                option_d=od,
                correct_option=corr,
                cognitive_level=cog,
                difficulty=diff,
                rasch_difficulty=rasch,
                explanation=exp
            )
            messages.success(request, f"Yangi savol '{topic.title}' mavzusiga muvaffaqiyatli qo'shildi!")

        elif action == 'csv':
            csv_file = request.FILES.get('csv_file')
            topic_id = request.POST.get('topic_id')
            topic = get_object_or_404(Topic, id=topic_id)

            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Iltimos, to'g'ri CSV fayl yuklang!")
                return redirect('upload_questions')

            try:
                decoded_file = csv_file.read().decode('utf-8-sig')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)

                rows_to_create = []
                errors = []
                line_no = 1

                for row in reader:
                    line_no += 1
                    q_text = (row.get('text') or row.get('savol') or '').strip()
                    oa = (row.get('option_a') or row.get('a') or '').strip()
                    ob = (row.get('option_b') or row.get('b') or '').strip()
                    oc = (row.get('option_c') or row.get('c') or '').strip()
                    od = (row.get('option_d') or row.get('d') or '').strip()
                    corr = (row.get('correct_option') or row.get('javob') or '').strip().upper()
                    cog = (row.get('cognitive_level') or row.get('modul') or 'KNOWLEDGE').strip().upper()
                    diff = (row.get('difficulty') or row.get('qiyinchilik') or 'MEDIUM').strip().upper()
                    exp = (row.get('explanation') or row.get('izoh') or '').strip()

                    # Validatsiyalar
                    if not q_text:
                        errors.append(f"{line_no}-qatorda savol matni kiritilmagan.")
                        continue
                    if not oa or not ob or not oc or not od:
                        errors.append(f"{line_no}-qator: Barcha 4 ta variant (A, B, C, D) to'ldirilishi shart.")
                        continue
                    if corr not in ['A', 'B', 'C', 'D']:
                        errors.append(f"{line_no}-qator: To'g'ri javob '{corr}' noto'g'ri (A, B, C, D bo'lishi shart).")
                        continue

                    if 'QO' in cog or 'APP' in cog:
                        cog = 'APPLICATION'
                    elif 'MULO' in cog or 'REAS' in cog:
                        cog = 'REASONING'
                    else:
                        cog = 'KNOWLEDGE'

                    if diff not in ['EASY', 'MEDIUM', 'HARD']:
                        diff = 'MEDIUM'

                    try:
                        rasch = float(row.get('rasch_difficulty') or (0.0 if diff == 'MEDIUM' else (-1.0 if diff == 'EASY' else 1.2)))
                    except (ValueError, TypeError):
                        rasch = 0.0

                    rows_to_create.append(Question(
                        topic=topic,
                        text=q_text,
                        option_a=oa,
                        option_b=ob,
                        option_c=oc,
                        option_d=od,
                        correct_option=corr,
                        cognitive_level=cog,
                        difficulty=diff,
                        rasch_difficulty=rasch,
                        explanation=exp
                    ))

                # Xatolik bo'lsa, qisman yuklash bo'lmasligi uchun butunlay bekor qilish
                if errors:
                    err_msg = f"CSV faylda {len(errors)} ta xatolik aniqlandi. Tranzaksiya bekor qilindi:<br>" + "<br>".join(errors[:4])
                    if len(errors) > 4:
                        err_msg += f"<br>...va yana {len(errors)-4} ta xato."
                    messages.error(request, err_msg)
                    return redirect('upload_questions')

                # Xato bo'lmasa, atomik tranzaksiyada barchasini saqlash
                with transaction.atomic():
                    Question.objects.bulk_create(rows_to_create)

                messages.success(request, f"CSV fayldan barcha {len(rows_to_create)} ta savol muvaffaqiyatli tekshirilib bazaga yuklandi!")

            except Exception as e:
                messages.error(request, f"CSV faylni o'qishda xatolik yuz berdi: {str(e)}")

        elif action == 'paste':
            topic_id = request.POST.get('topic_id')
            raw_text = request.POST.get('raw_text', '').strip()
            topic = get_object_or_404(Topic, id=topic_id)

            if not raw_text:
                messages.error(request, "Matn bo'sh! Iltimos, namunadagidek savollarni kiriting.")
                return redirect('upload_questions')

            blocks = [b.strip() for b in raw_text.split('---') if b.strip()]
            if len(blocks) == 1 and '\n\n' in raw_text:
                blocks = [b.strip() for b in raw_text.split('\n\n') if b.strip()]

            rows_to_create = []
            errors = []

            for idx, block in enumerate(blocks, start=1):
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                q_text = ""
                oa, ob, oc, od = "", "", "", ""
                corr = "A"
                cog = "KNOWLEDGE"
                diff = "MEDIUM"
                exp = ""
                rasch = 0.0

                for line in lines:
                    line_lower = line.lower()
                    if line_lower.startswith(('savol:', 'q:', 'savol ')):
                        q_text = line.split(':', 1)[-1].strip() if ':' in line else line
                    elif line_lower.startswith(('a)', 'a.', 'a -')):
                        oa = line[2:].strip().lstrip('.)- ')
                    elif line_lower.startswith(('b)', 'b.', 'b -')):
                        ob = line[2:].strip().lstrip('.)- ')
                    elif line_lower.startswith(('c)', 'c.', 'c -')):
                        oc = line[2:].strip().lstrip('.)- ')
                    elif line_lower.startswith(('d)', 'd.', 'd -')):
                        od = line[2:].strip().lstrip('.)- ')
                    elif line_lower.startswith(('javob:', 'to`g`ri:', "to'g'ri:", 'ans:')):
                        val = line.split(':', 1)[-1].strip().upper()
                        if val in ['A', 'B', 'C', 'D']:
                            corr = val
                    elif line_lower.startswith(('modul:', 'daraja:', 'kognitiv:')):
                        val = line.split(':', 1)[-1].strip().lower()
                        if 'bil' in val:
                            cog = 'KNOWLEDGE'
                        elif 'qo`l' in val or "qo'l" in val or 'qoll' in val or 'app' in val:
                            cog = 'APPLICATION'
                        elif 'mulo' in val or 'fikr' in val or 'reas' in val:
                            cog = 'REASONING'
                    elif line_lower.startswith(('qiyinchilik:', 'diff:')):
                        val = line.split(':', 1)[-1].strip().lower()
                        if 'oson' in val or 'easy' in val:
                            diff, rasch = 'EASY', -1.0
                        elif 'qiyin' in val or 'hard' in val:
                            diff, rasch = 'HARD', 1.3
                        else:
                            diff, rasch = 'MEDIUM', 0.2
                    elif line_lower.startswith(('izoh:', 'tushuntirish:', 'exp:')):
                        exp = line.split(':', 1)[-1].strip()
                    elif not q_text and not line.startswith(('A', 'B', 'C', 'D')):
                        q_text = line

                if not q_text:
                    errors.append(f"{idx}-savol blokida savol matni topilmadi.")
                elif not (oa and ob and oc and od):
                    errors.append(f"{idx}-savol: Barcha 4 ta variant (A, B, C, D) kiritilmagan.")
                else:
                    rows_to_create.append(Question(
                        topic=topic,
                        text=q_text,
                        option_a=oa,
                        option_b=ob,
                        option_c=oc,
                        option_d=od,
                        correct_option=corr,
                        cognitive_level=cog,
                        difficulty=diff,
                        rasch_difficulty=rasch,
                        explanation=exp
                    ))

            if errors:
                err_msg = f"Matnni tahlil qilishda {len(errors)} ta xatolik aniqlandi:<br>" + "<br>".join(errors[:4])
                messages.error(request, err_msg)
                return redirect('upload_questions')

            with transaction.atomic():
                Question.objects.bulk_create(rows_to_create)

            messages.success(request, f"Matndan {len(rows_to_create)} ta savol muvaffaqiyatli tekshirilib '{topic.title}' mavzusiga qo'shildi!")

        return redirect('upload_questions')

    total_q = Question.objects.count()
    k_count = Question.objects.filter(cognitive_level='KNOWLEDGE').count()
    a_count = Question.objects.filter(cognitive_level='APPLICATION').count()
    r_count = Question.objects.filter(cognitive_level='REASONING').count()
    recent_questions = Question.objects.select_related('topic').order_by('-id')[:8]

    context = {
        'subject': subject,
        'topics': topics,
        'total_q': total_q,
        'k_count': k_count,
        'a_count': a_count,
        'r_count': r_count,
        'recent_questions': recent_questions,
    }
    return render(request, 'upload_questions.html', context)

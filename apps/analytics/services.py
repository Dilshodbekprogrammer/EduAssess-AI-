import random
from django.utils import timezone
from django.db import transaction
from apps.academic.models import Subject, Topic, Question
from apps.assessment.models import (
    FormativeGrade, StudentTopicMastery, QuizAttempt, 
    SummativeExam, SummativeExamQuestion
)
from apps.gamification.models import StudentReward, ExamDopuskRule

def update_student_topic_mastery(student, topic):
    """
    O'quvchining ma'lum bir mavzu bo'yicha barcha formativ baholarini (test, faollik, uy vazifasi)
    tahlil qilib, o'zlashtirish foizini va zaiflik (<60%) holatini yangilaydi.
    
    Tuzatish: FormativeGrade dan 'QUIZ' turi chiqarib tashlanadi, chunki u QuizAttempt
    jadvali orqali hisoblanadi. Bu bitta testning 2 marta qo'shilib ketishining oldini oladi.
    """
    grades = FormativeGrade.objects.filter(student=student, topic=topic).exclude(grade_type='QUIZ')
    quizzes = QuizAttempt.objects.filter(student=student, topic=topic)

    scores = []
    for g in grades:
        scores.append(g.percentage)
    for q in quizzes:
        scores.append(q.percentage)

    if not scores:
        avg_score = 0.0
        is_weak = True
    else:
        avg_score = round(sum(scores) / len(scores), 1)
        is_weak = avg_score < 60.0

    mastery, _ = StudentTopicMastery.objects.get_or_create(
        student=student,
        topic=topic,
        defaults={'mastery_percentage': avg_score, 'is_weak': is_weak}
    )
    mastery.mastery_percentage = avg_score
    mastery.is_weak = is_weak
    mastery.attempts_count = len(scores)
    mastery.save()
    return mastery

def predict_summative_score(student, subject):
    """
    Formativ baholar asosida BSB/CHSB bo'yicha kutilayotgan prognoz ballini hisoblaydi.
    Formula: 0.40 * Quiz_avg + 0.35 * Homework_avg + 0.25 * Activity_avg

    Tuzatishlar:
    1. 0.0 ball va "ma'lumot yo'q" (None) holati qat'iy ajratildi (0.0 or 65.0 xatosi bartaraf etildi).
    2. Barcha baholar max_score ga nisbatan foizga normallashtirildi (10/10 = 100%).
    3. Barcha baholari 0 bo'lgan o'quvchiga sun'iy 20% qo'yilmaydi, aniq 0.0% chiqariladi.
    """
    topics = subject.topics.all()
    if not topics.exists():
        return 0.0

    # 1. Quizzes (QuizAttempt percentage)
    quizzes = QuizAttempt.objects.filter(student=student, topic__in=topics)
    if quizzes.exists():
        quiz_pcts = [q.percentage for q in quizzes]
        quiz_avg = sum(quiz_pcts) / len(quiz_pcts)
    else:
        quiz_avg = None

    # 2. Homework (FormativeGrade percentage = score / max_score * 100)
    hw_grades = FormativeGrade.objects.filter(student=student, topic__in=topics, grade_type='HOMEWORK')
    if hw_grades.exists():
        hw_pcts = [g.percentage for g in hw_grades if g.max_score > 0]
        hw_avg = sum(hw_pcts) / len(hw_pcts) if hw_pcts else None
    else:
        hw_avg = None

    # 3. Activity (FormativeGrade percentage = score / max_score * 100)
    act_grades = FormativeGrade.objects.filter(student=student, topic__in=topics, grade_type='ACTIVITY')
    if act_grades.exists():
        act_pcts = [g.percentage for g in act_grades if g.max_score > 0]
        act_avg = sum(act_pcts) / len(act_pcts) if act_pcts else None
    else:
        act_avg = None

    # Agar birorta ham baho mavjud bo'lmasa:
    if quiz_avg is None and hw_avg is None and act_avg is None:
        return 0.0

    # Mavjud komponentlar bo'yicha og'irlikli proporsional hisoblash
    components = [
        (quiz_avg, 0.40),
        (hw_avg, 0.35),
        (act_avg, 0.25),
    ]

    total_weight = sum(w for val, w in components if val is not None)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(val * w for val, w in components if val is not None)
    prediction = weighted_sum / total_weight

    return round(min(100.0, max(0.0, prediction)), 1)

def check_dopusk(student, subject):
    """
    Gamifikatsiya va formativ o'rtacha ball asosida imtihonga 'Dopusk' tekshiruvi.
    """
    rule = ExamDopuskRule.objects.filter(subject=subject).first()
    reward, _ = StudentReward.objects.get_or_create(student=student)
    
    if not rule:
        return True, "Dopusk berildi (Standart)", 0.0

    predicted = predict_summative_score(student, subject)

    # Shartlar
    has_enough_coins = reward.coins >= rule.required_coins
    has_enough_score = predicted >= rule.required_formative_avg

    # Bonus hisoblash (Har 50 coin uchun 5% bonus, maksimal 10%)
    bonus = min(10.0, round((reward.coins // 50) * rule.bonus_percentage_rate, 1))

    if has_enough_coins and has_enough_score:
        return True, f"Imtihonga ruxsat berildi! (+{bonus}% bonus ball qo'shiladi)", bonus
    elif not has_enough_coins:
        return False, f"Coinlar yetarli emas! Sizda {reward.coins} coin bor, kerak: {rule.required_coins} coin.", 0.0
    else:
        return False, f"Formativ o'rtacha ball past! Hozirgi ko'rsatkich: {predicted}%, talab etiladi: {rule.required_formative_avg}%.", 0.0

def generate_adaptive_exam(student, subject, exam_type='BSB', total_questions=15):
    """
    Dinamik va Adaptiv Summativ Imtihon generatsiyasi (15 ta savol):
    1. Kognitiv modullar:
       - 5 ta Bilish (Knowledge)
       - 5 ta Qo'llash (Application)
       - 5 ta Mulohaza yuritish (Reasoning)
    2. O'quvchining zaif mavzularini (is_weak=True) diagnostika qilib,
       har bir modulda 60% savollarni aynan o'quvchi oqsayotgan mavzulardan tanlaydi.
    3. Savollar banki yetarli bo'lmaganda (kamida 15 ta savol) imtihon boshlanmaydi!
    """
    topics = list(subject.topics.all())
    available_questions_count = Question.objects.filter(topic__in=topics).count()

    # Xavfsizlik: Savollar bankida yetarli savol mavjudligini tekshirish
    if available_questions_count < total_questions:
        exam = SummativeExam.objects.create(
            student=student,
            subject=subject,
            exam_type=exam_type,
            status='PENDING',
            predicted_score=predict_summative_score(student, subject),
            bonus_applied=0.0,
            dopusk_granted=False,
            dopusk_message=f"Savollar bankida yetarli savol mavjud emas! Kamida {total_questions} ta savol talab etiladi (mavjud: {available_questions_count} ta)."
        )
        return exam

    can_enter, message, bonus = check_dopusk(student, subject)
    predicted = predict_summative_score(student, subject)

    exam = SummativeExam.objects.create(
        student=student,
        subject=subject,
        exam_type=exam_type,
        status='IN_PROGRESS' if can_enter else 'PENDING',
        predicted_score=predicted,
        bonus_applied=bonus,
        dopusk_granted=can_enter,
        dopusk_message=message
    )

    if not can_enter:
        return exam

    # O'quvchining zaif mavzulari
    weak_topic_ids = set(StudentTopicMastery.objects.filter(
        student=student, topic__in=topics, is_weak=True
    ).values_list('topic_id', flat=True))

    # Kognitiv modullar bo'yicha kvotalar (jami 15 ta)
    modules_quota = [
        ('KNOWLEDGE', 5),
        ('APPLICATION', 5),
        ('REASONING', 5),
    ]

    selected_questions = []
    already_used_ids = set()

    for cog_level, count in modules_quota:
        module_weak_count = int(round(count * 0.6)) if weak_topic_ids else 0
        module_normal_count = count - module_weak_count

        module_selected = []

        # 1. Zaif mavzulardan savollar tanlash
        if module_weak_count > 0 and weak_topic_ids:
            weak_qs = list(Question.objects.filter(
                topic_id__in=weak_topic_ids,
                cognitive_level=cog_level
            ).exclude(id__in=already_used_ids))
            random.shuffle(weak_qs)
            for q in weak_qs[:module_weak_count]:
                module_selected.append((q, True))
                already_used_ids.add(q.id)

        # 2. Kuchli / boshqa mavzulardan to'ldirish
        still_needed = count - len(module_selected)
        normal_qs = list(Question.objects.filter(
            topic__in=topics,
            cognitive_level=cog_level
        ).exclude(id__in=already_used_ids))
        random.shuffle(normal_qs)
        for q in normal_qs[:still_needed]:
            is_targeted = q.topic_id in weak_topic_ids
            module_selected.append((q, is_targeted))
            already_used_ids.add(q.id)

        # 3. Agar ushbu kognitiv darajada savol yetishmasa, mavjud ixtiyoriy savollardan to'ldirish
        if len(module_selected) < count:
            extra_needed = count - len(module_selected)
            extra_qs = list(Question.objects.filter(
                topic__in=topics
            ).exclude(id__in=already_used_ids))
            random.shuffle(extra_qs)
            for q in extra_qs[:extra_needed]:
                is_targeted = q.topic_id in weak_topic_ids
                module_selected.append((q, is_targeted))
                already_used_ids.add(q.id)

        selected_questions.extend(module_selected)

    # Exam questions bazaga saqlash
    for q, is_targeted in selected_questions:
        SummativeExamQuestion.objects.create(
            exam=exam,
            question=q,
            is_targeted_weak=is_targeted,
            weight=q.weight
        )

    return exam

def evaluate_summative_exam(exam, answers_dict):
    """
    Rasch psixometrik modeli va 3 ta Kognitiv modul (Bilish, Qo'llash, Mulohaza) bo'yicha imtihonni baholash.
    XAVFSIZLIK:
    - Agar imtihon allaqachon COMPLETED bo'lsa, qayta hisoblanmaydi va mukofot qayta berilmaydi!
    """
    if exam.status == 'COMPLETED':
        return exam

    with transaction.atomic():
        exam_questions = exam.questions.select_related('question', 'question__topic').all()
        total_weights = 0.0
        earned_weights = 0.0
        correct_count = 0

        # Modullar bo'yicha statistikalar
        mod_stats = {
            'KNOWLEDGE': {'total': 0, 'correct': 0},
            'APPLICATION': {'total': 0, 'correct': 0},
            'REASONING': {'total': 0, 'correct': 0},
        }

        weak_targeted_total = 0
        weak_targeted_correct = 0

        for eq in exam_questions:
            q_id = str(eq.question.id)
            chosen = answers_dict.get(q_id, '').upper().strip()
            eq.student_answer = chosen
            total_weights += eq.weight

            cog = eq.question.cognitive_level
            if cog in mod_stats:
                mod_stats[cog]['total'] += 1

            if eq.is_targeted_weak:
                weak_targeted_total += 1

            if chosen and chosen == eq.question.correct_option:
                eq.is_correct = True
                earned_weights += eq.weight
                correct_count += 1
                if cog in mod_stats:
                    mod_stats[cog]['correct'] += 1
                if eq.is_targeted_weak:
                    weak_targeted_correct += 1
            else:
                eq.is_correct = False
            eq.save()

        # Rasch score percentage
        if total_weights > 0:
            raw_percentage = round((earned_weights / total_weights) * 100, 1)
        else:
            raw_percentage = 0.0

        # Kognitiv modullar ballari
        k_tot = mod_stats['KNOWLEDGE']['total']
        a_tot = mod_stats['APPLICATION']['total']
        r_tot = mod_stats['REASONING']['total']

        exam.knowledge_score = round((mod_stats['KNOWLEDGE']['correct'] / k_tot * 100), 1) if k_tot > 0 else 0.0
        exam.application_score = round((mod_stats['APPLICATION']['correct'] / a_tot * 100), 1) if a_tot > 0 else 0.0
        exam.reasoning_score = round((mod_stats['REASONING']['correct'] / r_tot * 100), 1) if r_tot > 0 else 0.0

        exam.actual_score = raw_percentage
        exam.final_score = min(100.0, round(raw_percentage + exam.bonus_applied, 1))
        exam.status = 'COMPLETED'
        exam.completed_at = timezone.now()
        exam.save()

        # Agar zaif mavzulardagi savollarni muvaffaqiyatli topshirgan bo'lsa, o'zlashtirishni yangilash
        if weak_targeted_total > 0 and (weak_targeted_correct / weak_targeted_total) >= 0.6:
            for eq in exam_questions:
                if eq.is_targeted_weak and eq.is_correct:
                    update_student_topic_mastery(exam.student, eq.question.topic)

        # Gamifikatsiya mukofoti: Har bir to'g'ri javob uchun 5 coin va 15 XP (FAQAT BIR MARTA!)
        reward, _ = StudentReward.objects.get_or_create(student=exam.student)
        reward.add_coins(correct_count * 5, correct_count * 15)

    return exam

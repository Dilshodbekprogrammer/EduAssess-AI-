from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import Profile
from apps.academic.models import Subject, Topic, Question
from apps.assessment.models import (
    FormativeGrade, StudentTopicMastery, QuizAttempt, 
    SummativeExam, SummativeExamQuestion
)
from apps.gamification.models import StudentReward, ExamDopuskRule
from apps.analytics.services import (
    update_student_topic_mastery, predict_summative_score,
    check_dopusk, generate_adaptive_exam, evaluate_summative_exam
)

class AuditFixesTestCase(TestCase):
    def setUp(self):
        # O'qituvchi
        self.teacher = User.objects.create_user(username='muallim_test', password='password123', first_name='Rustam', last_name='Oripov')
        self.teacher.profile.role = 'TEACHER'
        self.teacher.profile.save()

        # O'quvchi 1
        self.student1 = User.objects.create_user(username='azizbek_test', password='password123', first_name='Azizbek', last_name='Karimov')
        self.student1.profile.role = 'STUDENT'
        self.student1.profile.save()
        reward1, _ = StudentReward.objects.get_or_create(student=self.student1)
        reward1.coins = 50
        reward1.xp = 100
        reward1.save()

        # O'quvchi 2
        self.student2 = User.objects.create_user(username='madina_test', password='password123', first_name='Madina', last_name='Rahimova')
        self.student2.profile.role = 'STUDENT'
        self.student2.profile.save()
        reward2, _ = StudentReward.objects.get_or_create(student=self.student2)
        reward2.coins = 30
        reward2.xp = 50
        reward2.save()

        # Fan va mavzular
        self.subject = Subject.objects.create(name='Informatika', code='INF-TEST')
        self.topic1 = Topic.objects.create(subject=self.subject, order=1, title='Tarmoqlar')
        self.topic2 = Topic.objects.create(subject=self.subject, order=2, title='Algoritmlar')

        # Dopusk qoidasi
        self.dopusk_rule = ExamDopuskRule.objects.create(
            subject=self.subject,
            required_coins=40,
            required_formative_avg=60.0,
            bonus_percentage_rate=5.0
        )

        # Savollar (kamida 15 ta)
        self.questions = []
        for i in range(18):
            cog = 'KNOWLEDGE' if i < 6 else ('APPLICATION' if i < 12 else 'REASONING')
            q = Question.objects.create(
                topic=self.topic1 if i % 2 == 0 else self.topic2,
                text=f"Savol {i+1} matni?",
                option_a="Variant A",
                option_b="Variant B",
                option_c="Variant C",
                option_d="Variant D",
                correct_option="A",
                cognitive_level=cog,
                difficulty="MEDIUM",
                rasch_difficulty=0.0
            )
            self.questions.append(q)

        self.client = Client()

    # 1. Xavfsizlik: Parolsiz switch yo'q, ruxsatlar tekshiriladi
    def test_security_and_authorization(self):
        # 1a. Anonim foydalanuvchi o'qituvchi jurnaliga kira olmaydi
        res = self.client.get('/teacher/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res.url)

        # 1b. O'quvchi o'qituvchi jurnaliga kira olmaydi
        self.client.login(username='azizbek_test', password='password123')
        res = self.client.get('/teacher/')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/student/')

        # 1c. O'quvchi boshqa o'quvchining shaxsiy kabinetiga kira olmaydi
        res = self.client.get(f'/student/{self.student2.id}/')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/student/')

        # 1d. O'qituvchi o'z login/paroli bilan o'qituvchi jurnaliga kira oladi
        self.client.logout()
        self.client.login(username='muallim_test', password='password123')
        res = self.client.get('/teacher/')
        self.assertEqual(res.status_code, 200)

    # 2. Tugallanmagan imtihonning natija sahifasida javoblar ochilmaydi
    def test_unfinished_exam_results_protected(self):
        self.client.login(username='azizbek_test', password='password123')
        # Dopusk olish uchun baholar qo'shamiz
        FormativeGrade.objects.create(student=self.student1, topic=self.topic1, grade_type='HOMEWORK', score=85, max_score=100)
        FormativeGrade.objects.create(student=self.student1, topic=self.topic1, grade_type='ACTIVITY', score=85, max_score=100)
        QuizAttempt.objects.create(student=self.student1, topic=self.topic1, score=85, total_questions=5, correct_answers=4)

        exam = generate_adaptive_exam(self.student1, self.subject, exam_type='BSB', total_questions=15)
        self.assertEqual(exam.status, 'IN_PROGRESS')

        # Natija sahifasiga kirishga uringanda, tugallanmagani uchun imtihon topshirish sahifasiga yo'naltiriladi
        res = self.client.get(f'/exam/{exam.id}/result/')
        self.assertEqual(res.status_code, 302)
        self.assertIn(f'/exam/{exam.id}/', res.url)

    # 3. Yakunlangan imtihon qayta yuborilganda mukofot takrorlanmaydi
    def test_no_duplicate_rewards_on_resubmit(self):
        self.client.login(username='azizbek_test', password='password123')
        # Dopusk olish uchun baholar qo'shamiz
        FormativeGrade.objects.create(student=self.student1, topic=self.topic1, grade_type='HOMEWORK', score=85, max_score=100)
        FormativeGrade.objects.create(student=self.student1, topic=self.topic1, grade_type='ACTIVITY', score=85, max_score=100)
        QuizAttempt.objects.create(student=self.student1, topic=self.topic1, score=85, total_questions=5, correct_answers=4)

        exam = generate_adaptive_exam(self.student1, self.subject, exam_type='BSB', total_questions=15)
        self.assertEqual(exam.status, 'IN_PROGRESS')
        
        # Barcha savollarga to'g'ri javob yuborish
        post_data = {f'q_{eq.question.id}': eq.question.correct_option for eq in exam.questions.all()}
        res1 = self.client.post(f'/exam/{exam.id}/', post_data)
        self.assertEqual(res1.status_code, 302)

        exam.refresh_from_db()
        self.assertEqual(exam.status, 'COMPLETED')
        
        reward = StudentReward.objects.get(student=self.student1)
        initial_coins = reward.coins

        # Ikkinchi marta POST yuborish
        res2 = self.client.post(f'/exam/{exam.id}/', post_data)
        self.assertEqual(res2.status_code, 302)

        reward.refresh_from_db()
        # Coinlar qayta qo'shilmasligi kerak!
        self.assertEqual(reward.coins, initial_coins)

    # 4. Nol baholar "ma'lumot yo'q" bilan adashtirilmasligi (0 baholarga 0.0% prognoz)
    def test_zero_grades_lead_to_zero_prediction(self):
        zero_student = User.objects.create_user(username='zero_student', password='password123')
        zero_student.profile.role = 'STUDENT'
        zero_student.profile.save()
        reward, _ = StudentReward.objects.get_or_create(student=zero_student)
        reward.coins = 100
        reward.save()

        # 0 ballik uy vazifasi va darsdagi faollik
        FormativeGrade.objects.create(student=zero_student, topic=self.topic1, grade_type='HOMEWORK', score=0, max_score=100)
        FormativeGrade.objects.create(student=zero_student, topic=self.topic1, grade_type='ACTIVITY', score=0, max_score=100)
        QuizAttempt.objects.create(student=zero_student, topic=self.topic1, score=0.0, total_questions=5, correct_answers=0)

        pred = predict_summative_score(zero_student, self.subject)
        # Natija 69.2% emas, aynan 0.0% bo'lishi shart!
        self.assertEqual(pred, 0.0)

        # Dopusk tekshiruvi: 0.0% ball bilan dopusk berilmasligi kerak
        can_enter, msg, bonus = check_dopusk(zero_student, self.subject)
        self.assertFalse(can_enter)
        self.assertIn("past", msg.lower())

    # 5. Prognoz baholarni maksimal ballga (max_score) nisbatan foizda hisoblashi
    def test_prediction_normalizes_by_max_score(self):
        norm_student = User.objects.create_user(username='norm_student', password='password123')
        norm_student.profile.role = 'STUDENT'
        norm_student.profile.save()
        reward, _ = StudentReward.objects.get_or_create(student=norm_student)
        reward.coins = 50
        reward.save()

        # Test 100%, Uy vazifasi 10/10 (100%), Faollik 10/10 (100%)
        QuizAttempt.objects.create(student=norm_student, topic=self.topic1, score=100.0, total_questions=5, correct_answers=5)
        FormativeGrade.objects.create(student=norm_student, topic=self.topic1, grade_type='HOMEWORK', score=10.0, max_score=10.0)
        FormativeGrade.objects.create(student=norm_student, topic=self.topic1, grade_type='ACTIVITY', score=10.0, max_score=10.0)

        pred = predict_summative_score(norm_student, self.subject)
        # 10/10 va 100% holatida 46% emas, 100.0% chiqishi shart!
        self.assertEqual(pred, 100.0)

    # 6. Bitta formativ testning o'zlashtirishda 2 marta qatnashmasligi
    def test_no_double_counting_quiz_in_mastery(self):
        test_student = User.objects.create_user(username='quiz_test_st', password='password123')
        test_student.profile.role = 'STUDENT'
        test_student.profile.save()

        # 1 ta faollik: 0 ball (0%)
        FormativeGrade.objects.create(student=test_student, topic=self.topic1, grade_type='ACTIVITY', score=0, max_score=100)
        # 1 ta test: 100 ball (100%)
        QuizAttempt.objects.create(student=test_student, topic=self.topic1, score=100.0, total_questions=5, correct_answers=5)
        # Formativ jurnalga ham yozilgan taqdirda
        FormativeGrade.objects.create(student=test_student, topic=self.topic1, grade_type='QUIZ', score=100.0, max_score=100.0)

        mastery = update_student_topic_mastery(test_student, self.topic1)
        # 0 va 100 uchun o'rtacha 66.7% emas, aynan 50.0% bo'lishi kerak!
        self.assertEqual(mastery.mastery_percentage, 50.0)

    # 7. Server kiritilgan qiymatlarni tekshirishi va tranzaksiya yaxlitligi
    def test_server_input_validation_and_transactions(self):
        self.client.login(username='muallim_test', password='password123')

        # 7a. 101/100 baho qabul qilinmasligi kerak
        initial_grade_count = FormativeGrade.objects.count()
        res = self.client.post('/teacher/grade/add/', {
            'student_id': self.student1.id,
            'topic_id': self.topic1.id,
            'grade_type': 'ACTIVITY',
            'score': 101,
            'max_score': 100
        })
        self.assertEqual(FormativeGrade.objects.count(), initial_grade_count)

        # 7b. Noto'g'ri CSV qatori butun tranzaksiyani bekor qilishi (qisman yozilmaslik)
        csv_content = (
            "text,option_a,option_b,option_c,option_d,correct_option,cognitive_level,difficulty\n"
            "To'g'ri savol 1,A,B,C,D,A,KNOWLEDGE,MEDIUM\n"
            ",A,B,C,D,A,KNOWLEDGE,MEDIUM\n"  # 2-qator xato: savol matni bo'sh!
        )
        csv_file = SimpleUploadedFile("test_bad.csv", csv_content.encode('utf-8'), content_type="text/csv")
        initial_q_count = Question.objects.count()

        res_csv = self.client.post('/teacher/questions/upload/', {
            'action': 'csv',
            'topic_id': self.topic1.id,
            'csv_file': csv_file
        })
        # 1-savol ham bazaga yozilmasligi kerak!
        self.assertEqual(Question.objects.count(), initial_q_count)

    # 8. Savollar yetishmaganda imtihon boshlanmasligi
    def test_insufficient_questions_blocks_exam(self):
        small_subject = Subject.objects.create(name='Kichik Fan', code='SMALL-SUB')
        small_topic = Topic.objects.create(subject=small_subject, order=1, title='Mavzu')
        # Faqat 4 ta savol qo'shamiz
        for i in range(4):
            Question.objects.create(
                topic=small_topic,
                text=f"Kichik savol {i}",
                option_a="A", option_b="B", option_c="C", option_d="D", correct_option="A"
            )

        exam = generate_adaptive_exam(self.student1, small_subject, total_questions=15)
        # Imtihon IN_PROGRESS bo'lmaydi, dopusk rad etiladi
        self.assertFalse(exam.dopusk_granted)
        self.assertEqual(exam.status, 'PENDING')
        self.assertIn("yetarli savol mavjud emas", exam.dopusk_message)

    # 9. Yangi o'quvchi qo'shish (Single va Bulk) va tizimga kirish tekshiruvi
    def test_add_student_workflow(self):
        self.client.login(username='muallim_test', password='password123')

        # 9a. Yagona o'quvchi qo'shish
        res_single = self.client.post('/teacher/students/add/', {
            'action': 'single',
            'first_name': 'Jasurbek',
            'last_name': 'Aliyev',
            'grade_level': '9-B',
            'username': 'jasur_9b',
            'password': 'maxsusparol123'
        })
        self.assertEqual(res_single.status_code, 302)
        new_student = User.objects.get(username='jasur_9b')
        self.assertEqual(new_student.first_name, 'Jasurbek')
        self.assertEqual(new_student.profile.grade_level, '9-B')
        self.assertEqual(new_student.profile.role, 'STUDENT')
        self.assertTrue(StudentReward.objects.filter(student=new_student).exists())

        # 9b. O'quvchi o'z logini va paroli bilan tizimga muvaffaqiyatli kira olishi
        self.client.logout()
        login_success = self.client.login(username='jasur_9b', password='maxsusparol123')
        self.assertTrue(login_success)

        # 9c. Ommaviy (Bulk) ro'yxatdan qo'shish
        self.client.login(username='muallim_test', password='password123')
        bulk_text = "1. Sardor Valiyev\n2. Nodira Karimova, 9-C"
        res_bulk = self.client.post('/teacher/students/add/', {
            'action': 'bulk',
            'student_list': bulk_text,
            'default_grade': '9-A',
            'default_password': 'parol123'
        })
        self.assertEqual(res_bulk.status_code, 302)
        self.assertTrue(User.objects.filter(last_name='Valiyev').exists())
        self.assertTrue(User.objects.filter(last_name='Karimova').exists())
        nodira = User.objects.get(last_name='Karimova')
        self.assertEqual(nodira.profile.grade_level, '9-C')

    # 10. Oddiy o'quvchi o'quvchi qo'sha olmasligi kerak (Ruxsat himoyasi)
    def test_student_cannot_add_student(self):
        self.client.login(username='azizbek_test', password='password123')
        res = self.client.post('/teacher/students/add/', {
            'action': 'single',
            'first_name': 'Xaker',
            'last_name': 'Xakerov'
        })
        # Student o'qituvchi sahifasiga kirolmaydi va redirect bo'ladi
        self.assertEqual(res.status_code, 302)
        self.assertFalse(User.objects.filter(first_name='Xaker').exists())


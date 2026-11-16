from django.db import models
from django.contrib.auth.models import User
from apps.academic.models import Subject, Topic, Question

class FormativeGrade(models.Model):
    GRADE_TYPES = (
        ('ACTIVITY', "Darsdagi faollik"),
        ('HOMEWORK', "Uy vazifasi"),
        ('QUIZ', "Qisqa formativ test"),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='formative_grades', verbose_name="O'quvchi")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='formative_grades', verbose_name="Mavzu")
    grade_type = models.CharField(max_length=15, choices=GRADE_TYPES, default='ACTIVITY', verbose_name="Turi")
    score = models.FloatField(verbose_name="To'plangan ball")
    max_score = models.FloatField(default=100.0, verbose_name="Maksimal ball")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Izoh")
    date = models.DateField(auto_now_add=True, verbose_name="Sana")

    def __str__(self):
        return f"{self.student.username} - {self.topic.title} ({self.get_grade_type_display()}): {self.score}/{self.max_score}"

    @property
    def percentage(self):
        if self.max_score > 0:
            return round((self.score / self.max_score) * 100, 1)
        return 0.0

class StudentTopicMastery(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_masteries')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='student_masteries')
    mastery_percentage = models.FloatField(default=0.0, verbose_name="O'zlashtirish foizi (%)")
    is_weak = models.BooleanField(default=False, verbose_name="Zaif nuqta (< 60%)")
    attempts_count = models.PositiveIntegerField(default=0)
    last_evaluated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'topic')

    def __str__(self):
        status = "🔴 Zaif" if self.is_weak else "🟢 O'zlashtirilgan"
        return f"{self.student.username} | {self.topic.title}: {self.mastery_percentage}% ({status})"

class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.FloatField(default=0.0, verbose_name="To'plangan ball")
    total_questions = models.PositiveIntegerField(default=5)
    correct_answers = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.topic.title} ({self.correct_answers}/{self.total_questions})"

    @property
    def percentage(self):
        if self.total_questions > 0:
            return round((self.correct_answers / self.total_questions) * 100, 1)
        return 0.0

class SummativeExam(models.Model):
    EXAM_TYPES = (
        ('BSB', "Birlik Summativ Baholash (BSB)"),
        ('CHSB', "Choraklik Summativ Baholash (CHSB)"),
    )
    STATUS_CHOICES = (
        ('PENDING', "Kutilmoqda"),
        ('IN_PROGRESS', "Jarayonda"),
        ('COMPLETED', "Yakunlangan"),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='summative_exams', verbose_name="O'quvchi")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='summative_exams', verbose_name="Fan")
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPES, default='BSB', verbose_name="Imtihon turi")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING', verbose_name="Holat")
    
    predicted_score = models.FloatField(default=0.0, verbose_name="Prognoz qilingan baho (%)")
    actual_score = models.FloatField(default=0.0, verbose_name="Haqiqiy test balli (Rasch)")
    bonus_applied = models.FloatField(default=0.0, verbose_name="Gamifikatsiya bonusi (%)")
    final_score = models.FloatField(default=0.0, verbose_name="Yakuniy summativ baho (%)")
    
    # Kognitiv modullar bo'yicha ko'rsatkichlar (15 ta savol tahlili)
    knowledge_score = models.FloatField(default=0.0, verbose_name="Bilish moduli bali (%)")
    application_score = models.FloatField(default=0.0, verbose_name="Qo'llash moduli bali (%)")
    reasoning_score = models.FloatField(default=0.0, verbose_name="Mulohaza yuritish moduli bali (%)")
    
    dopusk_granted = models.BooleanField(default=True, verbose_name="Dopusk berilganmi")
    dopusk_message = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.get_exam_type_display()} ({self.final_score}%)"

class SummativeExamQuestion(models.Model):
    exam = models.ForeignKey(SummativeExam, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    is_targeted_weak = models.BooleanField(default=False, verbose_name="Zaif mavzudan tanlanganmi")
    student_answer = models.CharField(max_length=1, blank=True, verbose_name="O'quvchi javobi")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'rimi")
    weight = models.FloatField(default=1.0, verbose_name="Rasch vazni")

    def __str__(self):
        return f"Exam #{self.exam.id} - Q: {self.question.id} ({'To`g`ri' if self.is_correct else 'Noto`g`ri'})"

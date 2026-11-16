from django.db import models

class Subject(models.Model):
    name = models.CharField(max_length=150, verbose_name="Fan nomi")
    code = models.CharField(max_length=30, unique=True, verbose_name="Fan kodi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics', verbose_name="Fan")
    title = models.CharField(max_length=200, verbose_name="Mavzu nomi")
    order = models.PositiveIntegerField(default=1, verbose_name="Tartib raqami")
    description = models.TextField(blank=True, verbose_name="Mavzu mazmuni")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title}"

class Question(models.Model):
    DIFFICULTY_CHOICES = (
        ('EASY', "Oson"),
        ('MEDIUM', "O'rta"),
        ('HARD', "Qiyin"),
    )
    COGNITIVE_CHOICES = (
        ('KNOWLEDGE', "Bilish"),
        ('APPLICATION', "Qo'llash"),
        ('REASONING', "Mulohaza yuritish"),
    )
    CORRECT_CHOICES = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    )

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions', verbose_name="Mavzu")
    text = models.TextField(verbose_name="Savol matni")
    option_a = models.CharField(max_length=255, verbose_name="Variant A")
    option_b = models.CharField(max_length=255, verbose_name="Variant B")
    option_c = models.CharField(max_length=255, verbose_name="Variant C")
    option_d = models.CharField(max_length=255, verbose_name="Variant D")
    correct_option = models.CharField(max_length=1, choices=CORRECT_CHOICES, verbose_name="To'g'ri javob")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='MEDIUM', verbose_name="Qiyinchilik")
    cognitive_level = models.CharField(max_length=20, choices=COGNITIVE_CHOICES, default='KNOWLEDGE', verbose_name="Kognitiv modul (Daraja)")
    rasch_difficulty = models.FloatField(default=0.0, verbose_name="Rasch b-parametri (-3 dan +3)")
    explanation = models.TextField(blank=True, verbose_name="Tushuntirish/Izoh")

    def __str__(self):
        return f"[{self.get_cognitive_level_display()} | {self.get_difficulty_display()}] {self.text[:50]}..."

    @property
    def weight(self):
        # Rasch model weight calculation
        # b in [-2, +2] -> weight in [0.8, 1.6]
        return round(1.0 + (self.rasch_difficulty * 0.3), 2)

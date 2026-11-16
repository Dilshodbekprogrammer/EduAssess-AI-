from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class StudentReward(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reward')
    coins = models.PositiveIntegerField(default=50, verbose_name="EduCoinlar")
    xp = models.PositiveIntegerField(default=120, verbose_name="Tajriba ballari (XP)")
    streak_days = models.PositiveIntegerField(default=3, verbose_name="Uzluksizlik (kun)")
    level = models.CharField(max_length=50, default="Izlanuvchan", verbose_name="Daraja")

    def __str__(self):
        return f"{self.student.username} - {self.coins} Coins, {self.xp} XP"

    def add_coins(self, amount, xp_amount=None):
        self.coins += amount
        if xp_amount is None:
            self.xp += amount * 2
        else:
            self.xp += xp_amount
        
        # Daraja hisoblash
        if self.xp > 500:
            self.level = "Bilimdon Master 🏆"
        elif self.xp > 250:
            self.level = "Ilg'or Bilimdon 🚀"
        elif self.xp > 100:
            self.level = "Izlanuvchan 💡"
        else:
            self.level = "Boshlang'ich 🌱"
        self.save()

class Badge(models.Model):
    title = models.CharField(max_length=100, verbose_name="Nishon nomi")
    description = models.TextField(verbose_name="Tavsif")
    icon = models.CharField(max_length=50, default="fa-medal", verbose_name="Ikonka (FA)")
    reward_xp = models.PositiveIntegerField(default=30, verbose_name="Mukofot XP")

    def __str__(self):
        return self.title

class StudentBadge(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'badge')

    def __str__(self):
        return f"{self.student.username} -> {self.badge.title}"

class ExamDopuskRule(models.Model):
    subject = models.ForeignKey('academic.Subject', on_delete=models.CASCADE, related_name='dopusk_rules')
    required_coins = models.PositiveIntegerField(default=40, verbose_name="Dopusk uchun minimal coin")
    required_formative_avg = models.FloatField(default=60.0, verbose_name="Minimal formativ o'rtacha ball (%)")
    bonus_percentage_rate = models.FloatField(default=5.0, verbose_name="Har 50 coin uchun bonus % (maks 10%)")

    def __str__(self):
        return f"{self.subject.name} - Dopusk: {self.required_coins} coin, {self.required_formative_avg}%"

@receiver(post_save, sender=User)
def create_student_reward(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'reward'):
        StudentReward.objects.create(student=instance)

from django.contrib import admin
from django.utils.html import format_html
from .models import StudentReward, Badge, StudentBadge, ExamDopuskRule

@admin.register(StudentReward)
class StudentRewardAdmin(admin.ModelAdmin):
    list_display = ('student', 'coins_display', 'xp_display', 'streak_days_display', 'level')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    list_editable = ('level',)
    actions = ['give_50_coins', 'reset_streak']

    def coins_display(self, obj):
        return format_html('<span style="color:#d97706; font-weight:bold;">🪙 {} coin</span>', obj.coins)
    coins_display.short_description = "EduCoinlar"

    def xp_display(self, obj):
        return format_html('<span style="color:#4f46e5; font-weight:bold;">⚡ {} XP</span>', obj.xp)
    xp_display.short_description = "Tajriba"

    def streak_days_display(self, obj):
        return format_html('<span style="color:#059669; font-weight:bold;">🔥 {} kun</span>', obj.streak_days)
    streak_days_display.short_description = "Ketma-ketlik (Streak)"

    @admin.action(description="Tanlangan o'quvchilarga +50 EduCoin berish")
    def give_50_coins(self, request, queryset):
        for r in queryset:
            r.add_coins(50, 100)
        self.message_user(request, f"{queryset.count()} nafar o'quvchiga +50 coin va +100 XP qo'shildi.")

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_preview', 'reward_xp', 'description')

    def icon_preview(self, obj):
        return format_html('<i class="fa-solid {}" style="font-size:16px; color:#4f46e5;"></i> ({})', obj.icon, obj.icon)
    icon_preview.short_description = "Ikonka"

@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ('student', 'badge', 'earned_at')
    list_filter = ('badge', 'earned_at')
    search_fields = ('student__username', 'badge__title')

@admin.register(ExamDopuskRule)
class ExamDopuskRuleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'required_coins_badge', 'required_score_badge', 'bonus_rate_badge')

    def required_coins_badge(self, obj):
        return format_html('<span style="font-weight:bold; color:#d97706;">Kamida {} coin</span>', obj.required_coins)
    required_coins_badge.short_description = "Talab etiladigan coin"

    def required_score_badge(self, obj):
        return format_html('<span style="font-weight:bold; color:#0284c7;">Kamida {}%</span>', obj.required_formative_avg)
    required_score_badge.short_description = "Minimal formativ o'rtacha"

    def bonus_rate_badge(self, obj):
        return format_html('<span style="font-weight:bold; color:#059669;">Har 50 coin uchun +{}%</span>', obj.bonus_percentage_rate)
    bonus_rate_badge.short_description = "Bonus ko'rsatkichi"

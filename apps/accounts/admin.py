from django.contrib import admin
from django.utils.html import format_html
from .models import Profile

admin.site.site_header = "EduAssess AI — Baholash Tizimi Boshqaruvi"
admin.site.site_title = "EduAssess AI Admin"
admin.site.index_title = "Tizim ma'lumotlari, savollar banki va psixometrik modellar boshqaruvi"

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'role_badge', 'grade_level', 'phone', 'coins_count')
    list_filter = ('role', 'grade_level')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "F.I.SH"

    def role_badge(self, obj):
        if obj.is_teacher:
            return format_html('<span style="background:#dbeafe; color:#1e40af; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">O\'qituvchi</span>')
        return format_html('<span style="background:#d1fae5; color:#065f46; font-weight:bold; padding:2px 8px; border-radius:10px; font-size:11px;">O\'quvchi</span>')
    role_badge.short_description = "Roli"

    def coins_count(self, obj):
        reward = getattr(obj.user, 'reward', None)
        if reward:
            return format_html('<b style="color:#d97706;">🪙 {} coin</b>', reward.coins)
        return "-"
    coins_count.short_description = "EduCoin"
